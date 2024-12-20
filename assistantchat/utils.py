from typing import List, Dict, Optional, Any, Generator
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from datetime import datetime
import logging
import uuid
from django.db.models import Q
import json

from django.contrib.auth.models import User
from app.utils.vector_store import vector_store
from app.modals.chat import get_llm
from .models import Conversation
from users.models import Assistant, SupabaseUser, DocumentChunk, PDFDocument
from app.utils.assistant_manager import AssistantManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatModule:
    def __init__(self):
        """Initialize the chat module with necessary components."""
        self.llm = get_llm()
        self.user_knowledge_levels = {}  # Store user knowledge assessment
    

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
        {{
            "welcome_message": "Personalized greeting that makes the user feel comfortable",
            "diagnostic_questions": [
                {{
                    "question": "Conversational, engaging question",
                    "difficulty": "basic/intermediate/advanced",
                    "learning_goal": "What this question helps assess"
                }}
            ]
        }}
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


    def _create_contextual_rag_prompt(self, assistant_config) -> ChatPromptTemplate:
        """Create a context-aware, adaptive prompt that incorporates teacher instructions, Mermaid diagrams, previous interactions, and provided context."""

        subject = assistant_config.get('subject', '')
        topic = assistant_config.get('topic', '')
        prompt = assistant_config.get('prompt', '')
        teacher_instructions = assistant_config.get('teacher_instructions', '')
        prompt_instructions = assistant_config.get('prompt_instructions', '')
        

        # System message to explain the query first, provide tailored exercises, and adapt based on history
        system_message = f"""
        You are an adaptive AI educator specializing in {topic} in {subject}. Your role is to:
        1. Explain the user's query clearly and thoroughly using the provided **context**: {{context}}.
        2. Adapt explanations and exercises based on user feedback and knowledge level (beginner, intermediate, advanced).
        3. Apply the following **teacher instructions**: {teacher_instructions}.
        4. Generate exercises only after the user confirms understanding or modifies the query.

        ## Teaching Strategy (Guided by Teacher Instructions):
        - Use pedagogical approaches as defined by the teacher instructions provided.
        - Tailor explanations and exercises to suit the user’s understanding and goals.
        - Focus on engaging and effective teaching methods as per the teacher’s approach.

        ## Diagram Usage (Mermaid):
        - If applicable, use **Mermaid diagrams** for visualizing non-textual concepts like processes or structures.
        - Only include diagrams when a visual representation adds clarity.
        - Do not explicitly mention "Mermaid" or the tool unless necessary.

        ## Interaction Flow:
        1. **Explain the query** using the provided **context**: {{context}}.
            - Explain the query thoroughly and ensure clarity first.
            - Adapt your explanation based on the user’s knowledge level (beginner, intermediate, advanced).
        2. **Provide tailored exercises**:
            - After confirming the user’s understanding or when the user changes the query, provide exercises suited to their level:
                - Beginners: Focus on simple concept reinforcement.
                - Intermediate users: Offer scenario-based exercises.
                - Advanced users: Present real-world problems or case studies.
        3. **Adapt to user history**:
            - Use previous interactions (if available) to assess the user’s knowledge level and learning preferences.
            - If no history is available, ask a brief question to assess the user’s understanding before starting the explanation.

        ## Current User Query:
        - {prompt}

        ## Contextual Inputs:
        - **Provided Context**: {{context}} (strictly use this context to generate responses, but do **not** include or reference the inner context in the final response).
        - **Previous Interactions**: {{chat_history}} (to assess learning progress and knowledge level).
        - **Prompt Instructions**: {prompt_instructions} (use these to guide the response generation, but do not include them in the final answer).

        Focus on generating a pedagogically sound, adaptive response tailored to the user's current query, learning history, and provided context.
        """

        # Human message with the user's query
        human_message = f"""I want that you teaching me as teacher.

        ### My Question: {prompt}"""

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_message)
        ])

    def assess_user_knowledge(self, assistant_config: dict, user_assistant_key: str) -> Dict[str, Any]:
        try:
            # Create knowledge assessment prompt
            assessment_prompt = self._create_knowledge_assessment_prompt(assistant_config)
            
            # Create assessment chain
            assessment_chain = (
                assessment_prompt
                | self.llm
                | StrOutputParser()
            )

            # Generate assessment questions
            assessment_result = assessment_chain.invoke({
                "subject": assistant_config.get('subject', 'General Learning'),
                "topic": assistant_config.get('topic', 'Comprehensive Understanding'),
                "teacher_instructions": assistant_config.get('teacher_instructions', 'Interactive assessment')
            })
            
            # Enhanced JSON parsing with error handling
            try:
                parsed_result = json.loads(assessment_result)
                diagnostic_questions = parsed_result.get('questions', [])
                assessment_context = parsed_result.get('assessment_context', {})
            except json.JSONDecodeError:
                logger.error(f"Failed to parse assessment result: {assessment_result}")
                diagnostic_questions = []
                assessment_context = {}

            # Store assessment with more comprehensive information
            self.user_knowledge_levels[user_assistant_key] = {
                'diagnostic_questions': diagnostic_questions,
                'knowledge_level': 'unassessed',
                'assistant_id': assistant_config.get('id'),
                'assessment_context': assessment_context
            }

            return {
                'diagnostic_questions': diagnostic_questions,
                'assessment_context': assessment_context,
                'instructions': 'Please answer these diagnostic questions to help us understand your current knowledge level.'
            }

        except Exception as e:
            logger.error(f"Knowledge assessment error: {e}")
            return {'error': 'Assessment failed', 'details': str(e)}


    def get_relevant_context(self, query: str, assistant_id: str, k: int = 3, api_key: Optional[str] = None) -> str:
        """Retrieve relevant context from the DocumentChunk model based on similarity search."""
        try:
            # Step 1: Call the similarity_search class method from DocumentChunk
            # doc_id = PDFDocument.objects.filter(assistant_id=assistant_id)
            # chunks = DocumentChunk.objects.filter(document=doc_id.doc_id)
            # logger.info(f"Length of chunks: {len(chunks)}")
            results = DocumentChunk.similarity_search(query=query, k=k, api_key=api_key, assistant_id=assistant_id)

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

            logger.info(f"Relevant chunks: {[chunk['chunk_content'] for chunk in relevant_chunks]}")
            
            # Step 3: Extract and combine the content of the top-k relevant chunks
            context = "\n".join([chunk['chunk_content'] for chunk in relevant_chunks])
            
            return context if context else "No relevant context found."
        
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return "Error retrieving context."

    def save_chat_history(self, user_id: str, assistant_id: str, 
                         prompt: str, content: str, 
                         conversation_id: Optional[uuid.UUID] = None) -> None:
        """Save chat interaction to Django model."""
        try:
            
            # Get the related models instances
            user = User.objects.get(id=user_id)
            assistant = Assistant.objects.get(id=assistant_id)

            existing_conversation = Conversation.objects.filter(
                Q(assistant_id=assistant) & Q(user_id=user)
            ).first()

            if existing_conversation:
                # Use existing conversation
                conversation_id = existing_conversation.conversation_id
                
            
            # If no conversation_id provided, create a new one
            else:
                conversation_id = uuid.uuid4()
            
            # Create new conversation entry
            Conversation.objects.create(
                user_id=user,
                assistant_id=assistant,
                prompt=prompt,
                content=content,
                conversation_id=conversation_id
            )
            
            logger.info(f"Saved chat history for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            raise

    def get_chat_history(self, assistant_id: str, user_id: str, 
                        conversation_id: Optional[uuid.UUID] = None,
                        limit: int = 5) -> List[Dict]:
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

    def process_message(self, prompt: str, assistant_id: str, 
                       user_id: str, assistant_config: dict,
                       conversation_id: Optional[uuid.UUID] = None) -> Generator[Any, Any, Any]:
        """Enhanced message processing with two-chain approach."""
        try:
            # Create a unique key for user-assistant knowledge tracking
            user_assistant_key = f"{user_id}_{assistant_id}"

            # Check if user's knowledge level is already assessed for this specific assistant
            user_knowledge = self.user_knowledge_levels.get(user_assistant_key, {})


            # Get chat history
            chat_history = self.get_chat_history(
                assistant_id, 
                user_id, 
                
            )
            chat_history_str = "\n".join([
                f"Human: {chat['question']}\nAssistant: {chat['answer']}"
                for chat in chat_history
            ])
            
            # If no prior assessment or knowledge level is unassessed
            if (not user_knowledge or 
                user_knowledge.get('knowledge_level') == 'unassessed' or 
                user_knowledge.get('assistant_id') != assistant_id):
                
                # Conduct knowledge assessment for this specific assistant
                assessment_result = self.assess_user_knowledge(assistant_config, user_assistant_key)
                logger.info(f"The result of assessment: {assessment_result}")
                
                # If assessment generated questions, return them
                if 'diagnostic_questions' in assessment_result:
                    return json.dumps({
                        'type': 'knowledge_assessment',
                        'data': assessment_result
                    })

            # Retrieve context
            context = self.get_relevant_context(prompt, assistant_id)
            
            # Create contextual RAG prompt
            rag_prompt = self._create_contextual_rag_prompt(assistant_config)
            
            # Prepare input for RAG chain
            def prepare_rag_input(input_prompt):
                return {
                    "context": context,
                    "question": input_prompt,
                    "chat_history": chat_history_str,
                    "subject": assistant_config.get("subject", ""),
                    "instructions": assistant_config.get("teacher_instructions", ""),
                    "knowledge_level": user_knowledge.get('knowledge_level', 'basic'),
                    "diagnostic_questions": json.dumps(user_knowledge.get('diagnostic_questions', [])),
                    "assessment_context": json.dumps(user_knowledge.get('assessment_context', {}))
                }

            # Create RAG chain
            rag_chain = (
                prepare_rag_input
                | rag_prompt
                | self.llm
                | StrOutputParser()
            )

            # Generate response
            response = rag_chain.stream(prompt)

            full_response = ""
            for chunk in response:
                # logger.info(f"chunks from response: {chunk}")
                full_response += chunk
                yield chunk


            # Save interaction
            self.save_chat_history(
                user_id=user_id,
                assistant_id=assistant_id,
                prompt=prompt,
                content=full_response,
                conversation_id=conversation_id
            )

            # return full_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield "I apologize, but I encountered an error processing your message. Please try again."
        

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
        

