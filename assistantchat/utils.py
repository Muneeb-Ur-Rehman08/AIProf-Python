from typing import List, Dict, Optional, Any, Generator
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate, 
    HumanMessagePromptTemplate, 
    SystemMessagePromptTemplate, 
    AIMessagePromptTemplate,
    PromptTemplate,
    MessagesPlaceholder
)
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.store.memory import InMemoryStore

import logging
import uuid
from django.db.models import Q
import json

from django.contrib.auth.models import User

from app.modals.chat import get_llm
from .models import Conversation
from users.models import Assistant, DocumentChunk

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatModule:
    def __init__(self):
        """Initialize the chat module with necessary components."""
        self.llm = get_llm()
        self.user_knowledge_levels = {}  # Store user knowledge assessment
        self.memory_store = InMemoryStore()
        self.namespace = ("chat",)
    

    def _create_knowledge_assessment_prompt(self, assistant_config) -> ChatPromptTemplate:
        """Create an interactive and welcoming prompt for assessing user's knowledge level."""
        subject = assistant_config.get('subject', 'General Learning')
        topic = assistant_config.get('topic', 'Comprehensive Understanding')
        teacher_instructions = assistant_config.get('teacher_instructions', 'Interactive, adaptive knowledge assessment')
        
        system_message = f"""You are a friendly and supportive AI educator specializing in {subject} education.

        Interaction Guidelines:
        - Create a warm, encouraging learning environment
        - Ask diagnostic questions that reveal knowledge depth
        - Use conversational, approachable language
        - Adapt questioning based on initial responses
        - Provide constructive, motivational feedback

        Assessment Goals:
        - Understand the learner's current knowledge level
        - Identify strengths and areas for growth
        - Personalize the learning experience
        - Build learner confidence

        Focus Areas:
        - Subject: {subject}
        - Topic: {topic}
        - Pedagogical Approach: {teacher_instructions}

        Output Instructions:
        Respond with a JSON object containing:
        {{{{
            "welcome_message": "Personalized greeting that makes the user feel comfortable",
            "diagnostic_questions": [
                {{{{
                    "question": "Conversational, engaging question",
                    "difficulty": "basic/intermediate/advanced",
                    "learning_goal": "What this question helps assess"
                }}}}
            ]
        }}}}
        """
        
        human_message = f"""Let's explore your current understanding of {topic} in {subject}.

        I'll ask you a few friendly questions to understand your knowledge level. 
        There are no right or wrong answers - this is just to help me understand 
        how I can best support your learning journey.

        Please answer the following questions as openly and honestly as you can."""
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_message)
        ])

    def _create_contextual_rag_prompt(self, assistant_config, has_chat_history, prompt) -> ChatPromptTemplate:
        """Create a context-aware, adaptive prompt that incorporates teacher instructions, Mermaid diagrams, previous interactions, provided context, and supports image or file-based questions and solutions."""

        subject = assistant_config.get('subject', '')
        topic = assistant_config.get('topic', '')
        # prompt = assistant_config.get('prompt', '')
        teacher_instructions = assistant_config.get('teacher_instructions', '')
        prompt_instructions = assistant_config.get('prompt_instructions', '')
        user_name = assistant_config.get('user_name', '')
        if 'def ' in prompt or 'class ' in prompt or '{' in prompt:  # Simplified check for code presence
            # Wrap in triple backticks and escape any curly braces
            prompt = f"{prompt.replace('{', '{{').replace('}','}}')}"
        
        

        # System message to explain the query first, provide tailored exercises, and adapt based on history
        system_message = f"""
        You are an adaptive AI educator specializing in {topic} in {subject}. Your role is to:
        1. **Analyze the user's query first** and tailor your response accordingly, considering context, user history, and {{knowledge level}}.
        2. Explain the user's query clearly and thoroughly using the provided **context**.
        3. Adapt explanations and exercises based on user feedback and knowledge level (beginner, intermediate, advanced).
        4. Apply the following **teacher instructions**: {teacher_instructions}.
        5. Generate exercises based on the following criteria:
        
        - If the user confirms understanding (e.g., "yes", "I understand", "that's clear"), automatically proceed to provide relevant exercises
        - If the user asks for clarification, provide additional explanation before moving to exercises
        - If the user modifies the query, adjust the explanation and exercises accordingly
        6. Allow the user to submit questions or exercise solutions via text, image, or file upload.
        7. **Do not use notes in the responses**.

        ## Teaching Strategy (Guided by Teacher Instructions):
        - Use pedagogical approaches as defined by the teacher instructions provided.
        - Tailor explanations and exercises to suit the user's understanding and goals.
        - Focus on engaging and effective teaching methods as per the teacher's approach.

        ## Exercise Generation Protocol:
        1. After confirmation of understanding:
        - For beginners: Provide 1-2 foundational exercises focusing on basic concepts
        - For intermediate users: Offer 2-3 scenario-based exercises with increasing complexity
        - For advanced users: Present 1-2 complex real-world problems or case studies
        2. Structure each exercise with:
        - Clear problem statement
        - Expected learning outcome
        - Hints (optional, based on difficulty level)
        - Solution submission instructions
        3. Always include a clear transition phrase like "Now that you understand, let's practice with these exercises:"

        ## Diagram Usage (Mermaid):
        - If applicable, use **Mermaid diagrams** for visualizing non-textual concepts like processes or structures.
        - Only include diagrams when a visual representation adds clarity.
        - Do not explicitly mention "Mermaid" or the tool unless necessary.

        ## Interaction Flow:
        1. **Analyze and Explain**:
            - Process the user's query (including image/file content if provided)
            - Provide thorough explanation using context (without directly including it)
            - Explicitly check for understanding(donot ask understanding of the user in every response)
        2. **Exercise Delivery**:
            - After user confirms understanding or change the topic or query, automatically transition to exercises
            - Include clear submission instructions
            - Accept solutions via text, image, or file
        3. **Solution Review**:
            - Evaluate submitted solutions
            - Analyze submitted solutions
            - Provide detailed feedback
            - Offer follow-up exercises if needed

        ## Contextual Inputs:
        - **Provided Context**: {{context}} (strictly use this context to generate responses. If the query is unrelated to the context, please respond with a polite message stating that you lack knowledge about the query and **do not use context in the final response**).
        - **Chat Summary**: {{chat_summary}} (to assess learning progress and knowledge level, but do **not** include or reference the chat history in final response).
        - **Prompt Instructions**: {prompt_instructions} (use these to guide the response generation, but do **not** include them in the final answer).

        Focus on maintaining a clear flow: explanation → understanding check → exercise generation → solution evaluate and review. Always proceed to exercises after confirmed understanding.
        """


        # Human message with the user's query or mention of image upload
        human_message = f"""
        My Current Query: {prompt}
        """

        # Convert chat history into individual LangChain messages
        history_messages = []
        if has_chat_history:
            for entry in has_chat_history:
                if "User" in entry:
                    history_messages.append(HumanMessage(content=entry["User"]))
                if "AI" in entry:
                    history_messages.append(AIMessage(content=entry["AI"]))

        # logger.info(f"history_messages: {history_messages}")

        return ChatPromptTemplate.from_messages([
        SystemMessage(content=system_message),
        *history_messages,
        HumanMessage(content=human_message)
            
        ])

    def analyze_chat_history(self, messages: list, current_summary: str) -> Dict[str, Any]:
        """Analyze chat history to generate learning insights."""
        try:
            
            logger.info(f"\n\n Start creating summary\n\n")
            if not messages:
                return {
                    "error": "No chat history found for analysis"
                }

            # Format chat history
            chat_history_str = "\n".join([
                f"Human: {chat['User']}\nAssistant: {chat['AI']}"
                for chat in messages
            ])
            logger.info(f"\n\nThe messages string for analyze chats")
           # System message (instructions to the assistant)
            system_message = """
            You are an intelligent assistant tasked with summarizing chat histories.
            Your summary should cover the following points:
            1. The topics discussed between the Human and Assistant.
            2. The current knowledge level of the Human based on their questions and conversations.
            3. Any exercises or hands-on activities the Human has completed or discussed.
            4. How much progress the Human has made in terms of understanding or learning the topics.
            5. Use current summary if available and generate new summary using current summary and chat_history.
            Be sure to clearly address each of these points in your summary.
            Summary should be in plain text.

            Current Summart:
                {current_summary}
            """

            # Human message (actual chat history)
            human_message = """

                New Conversations:
                {chat_history_str}"""

            # Create ChatPromptTemplate with system and human messages
            chat_prompt_template = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(system_message),
                HumanMessagePromptTemplate.from_template(human_message)
            ])

            chain = chat_prompt_template | self.llm 


            # Generate the prompt
            summary_prompt = chain.invoke({"current_summary": current_summary, "chat_history_str": chat_history_str})

            logger.info(f"\n\nSummary we got: {summary_prompt.content}\n\n")

            return summary_prompt.content

        except Exception as e:
            logger.error(f"Error analyzing chat history: {e}")
            return {
                "error": f"Analysis failed: {str(e)}"
            }

    def assess_user_knowledge(self, messages: Optional[list]=None) -> str:
        """Assess user's knowledge level with improved error handling."""
        try:

            # Join messages to provide full context
            combined_messages = "\n".join([entry["User"] for entry in messages if "User" in entry])

            assessment_prompt = ChatPromptTemplate.from_messages([
                SystemMessagePromptTemplate.from_template(
                    "Based on the user's messages, assess their knowledge level as either 'beginner', 'intermediate', or 'advanced'. Consider technical vocabulary, complexity of questions, and depth of understanding shown."
                ),
                HumanMessagePromptTemplate.from_template("{input}")
            ])
            
            chain = assessment_prompt | self.llm | StrOutputParser()
            knowledge_level = chain.invoke(combined_messages).strip().lower()
            
            # Validate knowledge level
            valid_levels = {'beginner', 'intermediate', 'advanced'}
            knowledge_level = knowledge_level if knowledge_level in valid_levels else 'beginner'
            
            
        
            return knowledge_level
            
        except Exception as e:
            logger.error(f"Error in knowledge assessment: {str(e)}", exc_info=True)
            return 'beginner'
    
    def get_relevant_context(self, query: str, assistant_id: str, k: int = 3) -> str:
        """Retrieve relevant context from the DocumentChunk model based on similarity search."""
        try:
            # Step 1: Call the similarity_search class method from DocumentChunk
            # doc_id = PDFDocument.objects.filter(assistant_id=assistant_id)
            # chunks = DocumentChunk.objects.filter(document=doc_id.doc_id)
            # logger.info(f"Length of chunks: {len(chunks)}")
            results = DocumentChunk.similarity_search(query=query, k=k, assistant_id=assistant_id)

            # logger.info(f"Relevent result: {[x for x in results.document]}")
            
            # Step 2: Filter results by assistant ID (assistant_id)
            # relevant_chunks = [
            #     chunk for chunk, _ in results
            #     if chunk.document == doc_id
            # ]
            relevant_chunks = [
                    {
                        'chunk_id': chunk.id,
                        'page_number': chunk.page_number,
                        'document': chunk.document,
                        'chunk_content': chunk.content,
                        'similarity_score': similarity_score
                    }
                    for chunk, similarity_score in results
                ]
            
            # Step 3: Extract and combine the content of the top-k relevant chunks
            context = "\n".join([chunk['chunk_content'] for chunk in relevant_chunks])
            
            return context if context else "No relevant context found."
        
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return "Error retrieving context."

    def save_chat_history(self, user_id: str, assistant_id: str, 
                         messages: list) -> None:
        """Save chat interaction to Django model."""
        try:
            
            # Get the related models instances
            user = User.objects.get(id=user_id)
            assistant = Assistant.objects.get(id=assistant_id)


            logger.info(f"\n\nMessages we got for save: {messages}\n\n")

            existing_conversation = Conversation.objects.filter(
                Q(assistant_id=assistant) & Q(user_id=user)
            ).first()

            if existing_conversation:
                # Use existing conversation
                conversation_id = existing_conversation.conversation_id
                
            
            # If no conversation_id provided, create a new one
            else:
                conversation_id = uuid.uuid4()
            
            # Save messages to the database
            for message in messages:
                Conversation.objects.create(
                    user_id=user,
                    assistant_id=assistant,
                    prompt=message["User"],
                    content=message["AI"],
                    conversation_id=conversation_id
                )
                logger.info(f"\n\nSaved chat history for conversation {message['User']}\n\n")

            
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            raise

    def get_chat_history(self, assistant_id: str, user_id: str, 
                        limit: int=1) -> List[Dict]:
        """Retrieve chat history from Django model."""
        try:
            # Base query
            existing_conversation = Conversation.objects.filter(
                Q(assistant_id=assistant_id) & Q(user_id=user_id)
            ).first()
            
            if existing_conversation:
                # If conversation_id is provided, filter based on it
                query = Conversation.objects.filter(conversation_id=existing_conversation.conversation_id)
                
                # Order by creation date and limit results
                conversations = query.order_by('-created_at')[:limit]

                # Convert query result to list of dicts for consistent output
                return [
                    {
                        'question': conv.prompt,
                        'answer': conv.content,
                        'timestamp': conv.created_at,
                        'conversation_id': conv.conversation_id
                    }
                    for conv in conversations
                ]
            else:
                # Return an empty list if no conversation is found
                return []
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []

    def process_message(self, prompt: str, assistant_id: str, user_id: str, assistant_config: dict, chat_history):
        """Process message with LangGraph memory integration."""
        try:
            logger.info(f"chat_history in process_message: {chat_history}")
            
            # Create a unique key for user-assistant knowledge tracking
            user_assistant_key = f"{user_id}_{assistant_id}"
                    
            # Retrieve context
            context = self.get_relevant_context(prompt, assistant_id)
            
            # Create contextual RAG prompt
            rag_prompt = self._create_contextual_rag_prompt(
                assistant_config=assistant_config, 
                has_chat_history=chat_history,
                prompt=prompt
                )

            # Check if user's knowledge level is already assessed for this specific assistant
            # user_knowledge = self.user_knowledge_levels.get(user_assistant_key, {})


            knowledge_level = self.assess_user_knowledge(messages=chat_history)

            chat_summary = next(
                (entry["summary"] for entry in chat_history if "summary" in entry),
                "No summary available. Use chat history only to generate chat summary."
            )

            logger.info(f"chat_summary in process_message: {chat_summary}")


            # # If no prior assessment or knowledge level is unassessed
            # if (not user_knowledge or 
            #     user_knowledge.get('knowledge_level') == 'unassessed' or 
            #     user_knowledge.get('assistant_id') != assistant_id):
                
            #     # Conduct knowledge assessment for this specific assistant
            #     assessment_result = self.assess_user_knowledge(assistant_config, user_assistant_key)
            #     logger.info(f"The result of assessment: {assessment_result}")
                
            #     # If assessment generated questions, return them
            #     if 'diagnostic_questions' in assessment_result:
            #         return json.dumps({
            #             'type': 'knowledge_assessment',
            #             'data': assessment_result
            #         })
            # Prepare input for RAG chain
            def prepare_rag_input(input_prompt):
                return {
                    "context": context,
                    "question": prompt,
                    "chat_summary": chat_summary,
                    "subject": assistant_config.get("subject", ""),
                    "instructions": assistant_config.get("teacher_instructions", ""),
                    "knowledge_level": knowledge_level,
                    # "diagnostic_questions": json.dumps(user_knowledge.get('diagnostic_questions', [])),
                    # "assessment_context": json.dumps(user_knowledge.get('assessment_context', {}))
                }
            # Generate the response
            rag_chain = (
                prepare_rag_input
                | rag_prompt
                | self.llm
                | StrOutputParser()
            )
            response = rag_chain.stream(prompt)

            # full_response = ""
            # for chunk in response:
            #     full_response += chunk
            #     yield chunk

            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I encountered an error processing your message. Please try again."
        
    def clear_chat_history(self, assistant_id: str, user_id: str, 
                          conversation_id: Optional[uuid.UUID] = None) -> bool:
        """Clear chat history for a specific assistant and user."""
        try:
            query = Conversation.objects.filter(
                assistant_id=assistant_id,
                user_id=user_id
            )
            
            if conversation_id:
                query = query.filter(conversation_id=conversation_id)
                
            query.delete()
            return True
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return False
            
    def get_conversation_list(self, user_id: str) -> List[Dict]:
        """Get list of unique conversations for a user."""
        try:
            conversations = Conversation.objects.filter(
                user_id=user_id
            ).values(
                'conversation_id',
                'created_at'
            ).distinct().order_by('-created_at')
            
            return [
                {
                    'conversation_id': str(conv['conversation_id']),
                    'created_at': conv['created_at']
                }
                for conv in conversations
            ]
        except Exception as e:
            logger.error(f"Error retrieving conversation list: {e}")
            return []
        

