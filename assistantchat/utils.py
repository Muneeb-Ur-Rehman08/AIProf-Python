from typing import List, Dict, Optional, Any, Generator, Annotated, TypedDict
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate, 
    HumanMessagePromptTemplate, 
    SystemMessagePromptTemplate
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt.tool_executor import ToolExecutor
from langchain_core.tools import tool, StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
from typing import Union

import logging
import uuid
import re
from django.db.models import Q
import json
from typing import TypeVar, Sequence
from datetime import datetime, timezone
from functools import partial
from pydantic import BaseModel, Field

from django.contrib.auth.models import User
from app.modals.chat import get_llm
from .models import Conversation
from users.models import Assistant, DocumentChunk

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Message(BaseMessage):
    role: str
    content: str

    @property
    def type(self) -> str:
        return self.role

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}

class ChatState(BaseModel):
    """Pydantic model for tracking conversation state."""
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    assistant_id: str
    knowledge_level: Optional[str] = None
    context: Optional[str] = None
    next_step: str = "get_context"
    conversation_id: str
    memory_id: Optional[str] = None
    assistant_config: Dict[str, Any]
    chat_history: Optional[List[Dict[str, Any]]] = None
    chat_summary: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

class ChatModule:
    def __init__(self):
        self.llm = get_llm()
        self.user_knowledge_levels = {}
        self.memory_saver = MemorySaver()
        self.workflow = self._create_workflow()

    def _create_contextual_rag_prompt(self, assistant_config: Dict[str, Any]) -> ChatPromptTemplate:
        """Create a context-aware, adaptive prompt that incorporates teacher instructions, Mermaid diagrams, previous interactions, provided context, and supports image or file-based questions and solutions."""
   
        subject = assistant_config.get('subject', '')
        topic = assistant_config.get('topic', '')
        prompt = assistant_config.get('prompt', '')
        if 'def ' in prompt or 'class ' in prompt or '{' in prompt:  # Simplified check for code presence
            # Wrap in triple backticks and escape any curly braces
            prompt = f"```{prompt.replace('{', '{{').replace('}', '}}')}```"
        teacher_instructions = assistant_config.get('teacher_instructions', '')
        prompt_instructions = assistant_config.get('prompt_instructions', '')
        user_name = assistant_config.get('user_name', '')
        

        # System message to explain the query first, provide tailored exercises, and adapt based on history
        system_message = f"""
        You are an adaptive AI educator specializing in {topic} in {subject}. Your role is to:
        1. **Analyze the user's query first** and tailor your response accordingly, considering context, user history, and knowledge level.
        2. Explain the user's query clearly and thoroughly using the provided **context**: {{context}}.
        3. Adapt explanations and exercises based on user feedback and knowledge level (beginner, intermediate, advanced).
        4. Apply the following **teacher instructions**: {teacher_instructions}.
        5. Generate exercises only after the user confirms understanding or modifies the query.
        6. Allow the user to submit questions or exercise solutions via text, image, or file upload.
        7. **Check the query and response from chat history** (human query and assistant response accordingly), and if required by the query, generate a new response without including chat history in the final response.
        8. **Do not use notes in the responses**.

        ## Teaching Strategy (Guided by Teacher Instructions):
        - Use pedagogical approaches as defined by the teacher instructions provided.
        - Tailor explanations and exercises to suit the user's understanding and goals.
        - Focus on engaging and effective teaching methods as per the teacher's approach.

        ## Diagram Usage (Mermaid):
        - If applicable, use **Mermaid diagrams** for visualizing non-textual concepts like processes or structures.
        - Only include diagrams when a visual representation adds clarity.
        - Do not explicitly mention "Mermaid" or the tool unless necessary.

        ## Interaction Flow:
        1. **Analyze the user's query** and then explain using the provided **context**(but do not include the inner context in final response): {{context}}.
            - Explain the query thoroughly and ensure clarity first.
            - If the user submits a question via an image or file, process the image content and provide a relevant explanation based on it.
            - Adapt your explanation based on the user's knowledge level (beginner, intermediate, advanced).
            - **Do not use provided context directly in the final response**, but use provided context to tailor future responses.
        2. **Provide tailored exercises**:
            - After confirming the user's understanding or when the user changes the query, provide exercises suited to their level:
                - Beginners: Focus on simple concept reinforcement.
                - Intermediate users: Offer scenario-based exercises.
                - Advanced users: Present real-world problems or case studies.
            - Instruct the user that they can complete the exercise by submitting text, an image, or a file (only when exercise is given to the user, do **not** on every response), **do not use these instructs in final response**.
        3. **Accept user solutions or questions**:
            - **Accept solution in english, programming language, math, code etc.**
            - Allow the user to upload an image or file as part of their question or solution.
            - If the user submits a question in an image format, analyze the image and provide an explanation based on the image content.
            - After submitting, analyze the uploaded content (text, image, or file) and provide feedback or explanation.
        4. **Adapt to user history**:
            - Use previous interactions (if available) to assess the user's knowledge level and learning preferences (Human query and Assistant responses accordingly).
            - **Do not use chat history directly in the final response**, but use the chat history to tailor future responses.
            - If no history is available, ask a brief question to assess the user's understanding before starting the explanation.

        

        ## Contextual Inputs:
        - **Provided Context**: {{context}} (strictly use this context to generate responses. If the query is unrelated to the context, please respond with a polite message stating that you lack knowledge about the query and **do not use context in the final response**).
        - **Previous Interactions**: {{chat_history}} (Use the chat history to remember the interactions, but **do not** use it directly in the final response. Use it to generate response if user's query is related to chat history e.g if user ask about any query that related to previous question, then use chat history to generate response).
        - **Previous Chat Summary**: {{chat_summary}} (**Learning Progress**: Assess the user's learning progress and knowledge level based on previous interactions. **Main Points**: Tailor the response to the user's understanding and goals.).
        - **Prompt Instructions**: {prompt_instructions} (use these to guide the response generation, but do **not** include them in the final answer).
        
        Focus on generating a pedagogically sound, adaptive response tailored to the user's current query, learning history, and provided context without including the inner context in the final response. Allow the user to submit their question or solution as text, image, or file.
        """


        # Human message with the user's query or mention of image upload
        human_message = f"""
        ### My Question: {prompt}"""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_message)
        ])

    def get_relevant_context(self, state: ChatState) -> ChatState:
        """Retrieve relevant context from DocumentChunk model with improved error handling."""
        try:
            if not state.messages:
                state.context = "No message history available."
                return state

            results = DocumentChunk.similarity_search(
                query=state.messages[-1].content, 
                k=3, 
                assistant_id=state.assistant_id
            )
            
            # Ensure results is a list of dictionaries with the expected structure
            relevant_chunks_str = "\n".join([
                f"Content: {chunk.content}"
                for chunk, similarity_score in results
            ])
                
            state.context = relevant_chunks_str if relevant_chunks_str else "No relevant context found."
            
            
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {str(e)}", exc_info=True)
            state.context = f"Error retrieving context: {str(e)}"
            
        return state

    def get_chat_history(self, state: ChatState, limit: int = 10) -> Dict[str, Any]:
        """Retrieve chat history from Django model."""
        try:
            user_id = state.user_id
            assistant_id = state.assistant_id

            # Base query
            existing_conversation = Conversation.objects.filter(
                Q(assistant_id=assistant_id) & Q(user_id=user_id)
            ).first()
            
            if existing_conversation:
                # If conversation_id is provided, filter based on it
                query = Conversation.objects.filter(conversation_id=existing_conversation.conversation_id)
                
                # Order by creation date and limit results
                conversations = query.order_by('-created_at')[:limit]

                # Convert query result to a dictionary with 'chat_history' key
                return {
                    'chat_history': [
                    {
                        'question': conv.prompt,
                        'answer': conv.content,
                        'timestamp': conv.created_at,
                        'conversation_id': conv.conversation_id
                    }
                    for conv in conversations
                ]
                }
            else:
                # Return an empty dictionary if no conversation is found
                return {'chat_history': []}
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return {'chat_history': []}

    def analyze_chat_history(self, state: ChatState) -> ChatState:
        """Analyze chat history to generate learning insights."""
        try:
            # Get chat history
            chat_history = self.get_chat_history(state, limit=10)
            
            if not chat_history or 'chat_history' not in chat_history:
                state.chat_history = "No chat history found for analysis"
                return state

            # Extract the actual chat history entries
            chat_history_entries = chat_history['chat_history']

            # Format chat history
            chat_history_str = "\n".join([
                f"Human: {chat['question']}\nAssistant: {chat['answer']}"
                for chat in chat_history_entries
            ])

            # System message (instructions to the assistant)
            system_message = """
            You are an intelligent assistant tasked with summarizing chat histories.
            Your summary should cover the following points:
            1. The topics discussed between the Human and Assistant.
            2. The current knowledge level of the Human based on their questions and conversations.
            3. Any exercises or hands-on activities the Human has completed or discussed.
            4. How much progress the Human has made in terms of understanding or learning the topics.
            Be sure to clearly address each of these points in your summary.
            Summary should be in plain text.
            """

            # Human message (actual chat history)
            human_message = """{chat_history}"""

            # Create ChatPromptTemplate with system and human messages
            chat_prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message)
            ])

            chain = self.llm | chat_prompt_template
            response = chain.invoke(chat_history_str)

            # Generate the prompt
            state.chat_summary = response.messages[-1].content
            return state

        except Exception as e:
            logger.error(f"Error analyzing chat history: {e}")
            state.chat_history = f"Analysis failed: {str(e)}"
            return state

    def assess_knowledge(self, state: ChatState) -> ChatState:
        """Assess user's knowledge level with improved error handling."""
        try:
            user_assistant_key = f"{state.user_id}_{state.assistant_id}"
            
            if user_assistant_key not in self.user_knowledge_levels:
                if not state.messages:
                    state.knowledge_level = 'beginner'
                    return state

                assessment_prompt = ChatPromptTemplate.from_messages([
                    SystemMessagePromptTemplate.from_template(
                        "Based on the user's message, assess their knowledge level as either 'beginner', 'intermediate', or 'advanced'. Consider technical vocabulary, complexity of questions, and depth of understanding shown."
                    ),
                    HumanMessagePromptTemplate.from_template("{input}")
                ])
                
                user_message = state.messages[-1].content
                chain = assessment_prompt | self.llm | StrOutputParser()
                knowledge_level = chain.invoke({"input": user_message}).strip().lower()
                
                # Validate knowledge level
                valid_levels = {'beginner', 'intermediate', 'advanced'}
                if knowledge_level not in valid_levels:
                    knowledge_level = 'beginner'
                
                self.user_knowledge_levels[user_assistant_key] = knowledge_level
            
            state.knowledge_level = self.user_knowledge_levels[user_assistant_key]
            
        except Exception as e:
            logger.error(f"Error in knowledge assessment: {str(e)}", exc_info=True)
            state.knowledge_level = 'beginner'
            
        return state

    def generate_response(self, state: ChatState) -> ChatState:
        """Generate response with improved error handling and retry logic."""
        max_retries = 3
        retry_count = 0
        
        prompt_input = {
            "subject": state.assistant_config['subject'],
            "topic": state.assistant_config['topic'],
            "prompt": f"```{state.messages[-1]}```" if state.messages else "No message available",
            "teacher_instructions": state.assistant_config['teacher_instructions'],
            "prompt_instructions": state.assistant_config['prompt_instructions'],
            "user_name": state.assistant_config['user_name'],
            "context": state.context or "No context available",
            "chat_history": state.chat_history or "No chat history available",
            "chat_summary": state.chat_summary or "No chat summary available",
            "knowledge_level": state.knowledge_level or "No knowledge level available"
        }
        
        try:
            # Create RAG chain
            rag_prompt = self._create_contextual_rag_prompt(state.assistant_config)
            
            rag_chain = rag_prompt | self.llm | StrOutputParser()

            # Generate response
            response = rag_chain.invoke(prompt_input)
            logger.info(f"\n\nresponse from generate_response is :{response}\n\n")
            
            
            if response and isinstance(response, str):
                state.messages.append(AIMessage(content=response))
                logger.debug(f"Appended AIMessage: {state.messages[-1]}")
            else:
                logger.error("Invalid response format received")
                state.messages.append(AIMessage(content="I apologize, but I couldn't generate a proper response."))
                
        except Exception as e:
            logger.debug(f"State after generate_response: {state.messages}")
            logger.error(f"Error generating response (attempt {retry_count + 1}): {str(e)}", exc_info=True)
            
        return state

    def save_history(self, state: ChatState) -> ChatState:
        """Save chat history with improved error handling and validation."""
        try:
            user = User.objects.get(id=state.user_id)
            assistant = Assistant.objects.get(id=state.assistant_id)
            
            if len(state.messages) >= 2:
                user_message = state.messages[-2].content
                assistant_message = state.messages[-1].content
            else:
                user_message = "No user message available"
                assistant_message = "No assistant message available"
            
            # Validate conversation_id
            if not state.conversation_id:
                state.conversation_id = uuid.uuid4()
            
            Conversation.objects.create(
                user_id=user,
                assistant_id=assistant,
                prompt=user_message,
                content=assistant_message,
                conversation_id=state.conversation_id,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error saving chat history: {str(e)}", exc_info=True)
            
        return state

    def _create_workflow(self) -> StateGraph:
        """Create the conversation workflow graph."""
        graph_builder = StateGraph(ChatState)
        
        # Add nodes
        graph_builder.add_node("get_context", self.get_relevant_context)
        graph_builder.add_node("assess_knowledge", self.assess_knowledge)
        graph_builder.add_node("get_chat_history", self.get_chat_history)
        graph_builder.add_node("analyze_chat_history", self.analyze_chat_history)
        graph_builder.add_node("generate_response", self.generate_response)
        graph_builder.add_node("save_history", self.save_history)
        
        # Define edges
        graph_builder.add_edge("get_context", "assess_knowledge")
        graph_builder.add_edge("assess_knowledge", "get_chat_history")
        graph_builder.add_edge("get_chat_history", "analyze_chat_history")
        graph_builder.add_edge("analyze_chat_history", "generate_response")
        graph_builder.add_edge("generate_response", "save_history")
        graph_builder.add_edge("save_history", END)
        
        graph_builder.set_entry_point("get_context")
        
        return graph_builder.compile(checkpointer=self.memory_saver)

    def process_message(self, prompt: str, assistant_id: str, 
                       user_id: str, assistant_config: Dict[str, Any] 
                       ) -> Generator[Any, Any, Any]:
        """Process a message through the workflow with improved error handling."""
        try:
            thread_id = f"{user_id}_{assistant_id}"
            config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": "default"}}

            existing_conversation = Conversation.objects.filter(
                Q(assistant_id=assistant_id) & Q(user_id=user_id)
            ).first()

            conversation_id = str(existing_conversation.conversation_id if existing_conversation 
                               else uuid.uuid4())
            
            # Check if there is already a saved state for this conversation
            saved_state = self.memory_saver.get_tuple(config)
            
            if saved_state:
                # Convert `saved_state` into `ChatState` if needed
                saved_state = ChatState(**saved_state.checkpoint)
                saved_state.messages.append(HumanMessage(content=prompt))
            else:
                # Create a new state if no saved state is found
                saved_state = ChatState(
                    messages=[HumanMessage(content=prompt)],
                    user_id=user_id,
                    assistant_id=assistant_id,
                    assistant_config=assistant_config,
                    conversation_id=conversation_id
                )

            # Run the workflow and process the events
            events_generator = self.workflow.stream(
                saved_state,
                config=config,
                stream_mode="values"
            )

            # Keep track of seen messages and final state
            seen_messages = set()
            final_state = None

            # Process events
            for event in events_generator:
                final_state = event
                
                if 'messages' in event:
                    for message in event['messages']:
                        if isinstance(message, AIMessage):
                            message_content = message.content
                            if message_content not in seen_messages:
                                seen_messages.add(message_content)
                                yield message_content

            # Save the updated state after processing
            if final_state:
                metadata = {"timestamp": datetime.now(timezone.utc).isoformat()}
                new_versions = {}
                
                # Convert final_state to a regular dictionary
                final_state_dict = dict(final_state)
                
                # Ensure the final_state_dict has an 'id' key
                if 'id' not in final_state_dict:
                    final_state_dict['id'] = conversation_id
                
                self.memory_saver.put(config, final_state_dict, metadata, new_versions)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            yield "I apologize, but I encountered an error processing your message. Please try again."