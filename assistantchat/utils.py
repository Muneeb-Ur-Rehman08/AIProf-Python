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
        """Create a prompt for assessing user's knowledge level."""
        subject = assistant_config.get('subject', 'General Learning')
        topic = assistant_config.get('topic', 'Comprehensive Understanding')
        teacher_instructions = assistant_config.get('teacher_instructions', 'Systematic, incremental knowledge probing')
        prompt_instructions = assistant_config.get("prompt_instructions")
        prompt = assistant_config.get('prompt')

        system_message = f"""
        You are an expert educational diagnostics specialist focusing on {subject} assessment.

        Your goal is to precisely evaluate the user's current knowledge level through a strategic questioning approach:
        - Develop 3-5 progressively challenging questions
        - Questions should systematically probe:
        1. Basic comprehension
        2. Intermediate understanding
        3. Advanced application or conceptual depth

        Assessment Guidelines:
        - Subject Focus: {subject}
        - Topic: {topic}
        - Pedagogical Approach: {teacher_instructions}

        Output Format (CRITICAL):
        A JSON array of assessment questions, where each question includes:
        {{
            "question": "Specific diagnostic question",
            "difficulty": "basic/intermediate/advanced",
            "expected_knowledge_indicators": ["key conceptual markers"]
        }}
        """

        human_message = """
        Conduct a knowledge assessment for a user's understanding of {subject} in {topic}.
        Generate diagnostic questions that reveal their current understanding level.
        Follow the specified pedagogical approach: {teacher_instructions}
        """

        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_message)
        ])

    def _create_contextual_rag_prompt(self, assistant_config) -> ChatPromptTemplate:
        """
        Create an advanced contextual RAG prompt with multi-dimensional awareness.
        """
        subject = assistant_config.get('subject', 'General Knowledge')
        topic = assistant_config.get('topic', 'Comprehensive Understanding')
        pedagogical_approach = assistant_config.get('teacher_instructions', 'Adaptive Learning')
        prompt_instructions = assistant_config.get('prompt_instructions', '')
        prompt = assistant_config.get('prompt')
        
        system_message = f"""You are an AI assistant professional that helps the user with their questions.
        # Contextual Response Generator
        ## Operational Parameters
        - **Domain**: {subject}
        - **Specific Topic**: {topic}
        - **Pedagogical Strategy**: {pedagogical_approach}
        
        ## Contextual Inputs
        1. Previous Interactions: {{chat_history}}
        2. Relevant Document Context: {{context}}
        3. Current User Query: {prompt}
        4. Prompt Instructions: {prompt_instructions}
        
        ## CRITICAL RESPONSE GENERATION CONSTRAINTS
        ### Context Utilization Mandate
        - STRICTLY generate responses ONLY using:
        * Provided chat history
        * Available document context
        - DO NOT introduce external knowledge
        - If context is insufficient, clearly state limitations
        
        ### Diagram Usage Protocol
        - Create Mermaid diagrams ONLY when:
        * Context explicitly supports visual representation
        * Diagram meaningfully clarifies complex concepts
        * Direct textual explanation is insufficient
        - Avoid diagram generation as a default
        - Diagrams should provide ESSENTIAL visual insights
        
        ### Response Integrity Guidelines
        - Prioritize context relevance
        - Maintain fidelity to available information
        - If context lacks detailed information, provide:
        * Partial, context-based response
        * Clear indication of information gaps
        
        ## Response Generation Principles
        1. Contextual Coherence
        2. Knowledge Level Adaptation
        3. Precise, Focused Answers
        4. Incremental Information Delivery
        
        ## Advanced Response Guidelines
        - Analyze chat history for:
        * Previous knowledge demonstrations
        * Learning progression
        * Identified knowledge gaps
        - Context Utilization Strategy:
        * Extract most relevant information
        * Avoid redundant explanations
        * Highlight connections to previous interactions
        
        ## Mermaid Diagram Integration
        - Use diagrams sparingly and purposefully
        - Ensure diagram adds significant value
        - Align with {subject} and {topic} domain specifics
        - One diagram per significant concept, only if absolutely necessary or asked by user
        
        ## Response Constraints
        - Direct answer to the specific query
        - Maintain academic rigor
        - Ensure clarity and comprehensibility
        - If you are not sure about the answer, ask the user to clarify their question
        
        ## LANGUAGE AND RESPONSE STYLE RESTRICTIONS
        - AVOID phrases such as:
        * "I will not provide any further information."
        * "Based on the provided context."
        * "Based on our previous conversation."
        * "The answer to your query is straightforward and simple."
        * "Please let me know if this revised response meets your requirements."
        - Instead, focus on:
        * Providing thorough explanations
        * Offering additional insights or directions for further learning
        * Encouraging deeper engagement without closing the conversation prematurely
        """
        
        human_message = f"""## Precise Query Resolution
        ### Conversational Context
        {{chat_history}}
        
        ### Available Knowledge Context
        {{context}}
        
        ### Current Specific Query
        {prompt}
        
        ### Response Requirements
        - Build upon previous explanations
        - Provide connected, incremental insights
        - Maintain appropriate explanation depth
        - Use ONLY provided context
        - Consider {pedagogical_approach}
        """
        
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_message)
        ])


    def assess_user_knowledge(self, assistant_config: dict, user_assistant_key: str) -> Dict[str, Any]:
        """Conduct initial knowledge assessment."""
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
                "subject": assistant_config.get('subject'),
                "topic": assistant_config.get('topic'),
                "teacher_instructions": assistant_config.get('teacher_instructions')
            })
            
            # Parse JSON response
            try:
                diagnostic_questions = json.loads(assessment_result)
            except json.JSONDecodeError:
                logger.error("Failed to parse assessment questions")
                diagnostic_questions = []

            # Store assessment with assistant-specific information
            self.user_knowledge_levels[user_assistant_key] = {
                'diagnostic_questions': diagnostic_questions,
                'knowledge_level': 'unassessed',
                'assistant_id': assistant_config.get('id')  # Store assistant ID
            }

            return {
                'diagnostic_questions': diagnostic_questions,
                'instructions': 'Please answer these diagnostic questions to help us understand your current knowledge level.'
            }

        except Exception as e:
            logger.error(f"Knowledge assessment error: {e}")
            return {'error': 'Assessment failed', 'details': str(e)}


    def get_relevant_context(self, query: str, assistant_id: str, k: int = 5, api_key: Optional[str] = None) -> str:
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
                        ) -> List[Dict]:
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
                conversations = query.order_by('-created_at')

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
                
                # If assessment generated questions, return them
                if 'diagnostic_questions' in assessment_result:
                    return json.dumps(assessment_result)

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
                    "diagnostic_questions": json.dumps(user_knowledge.get('diagnostic_questions', []))
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
        

def main():
    """Test function to demonstrate ChatModule functionality."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize ChatModule
        chat_module = ChatModule()
        
        # Create test user ID and assistant ID
        test_assistant_id = "78b0cdb8-2ee0-41b2-bbfa-0ee4276e8630"
        test_user_id = "33039e91-cee1-4896-9cd3-ab6bba98369a"
        
        # Sample assistant configuration
        assistant_config = {
            "subject": "Python Programming",
            "teacher_instructions": "Provide clear, beginner-friendly explanations with code examples when appropriate."
        }
        
        # Create a test conversation
        conversation_id = uuid.uuid4()
        
        # Test messages
        test_messages = [
            "What is a Python decorator?",
            "Can you show me an example of using decorators?",
            "How do I create a class decorator?"
        ]
        
        print("\n=== Starting ChatModule Test ===\n")
        
        # Process multiple messages in conversation
        for message in test_messages:
            print(f"\nUser: {message}\n")
            
            response = chat_module.process_message(
                message=message,
                assistant_id=test_assistant_id,
                user_id=test_user_id,
                assistant_config=assistant_config,
                conversation_id=conversation_id
            )
            
            print(f"Assistant: {response}\n")
            print("-" * 50)
        
        # Test retrieving chat history
        print("\n=== Retrieving Chat History ===\n")
        chat_history = chat_module.get_chat_history(
            assistant_id=test_assistant_id,
            user_id=test_user_id,
            conversation_id=conversation_id
        )
        
        for interaction in chat_history:
            print(f"Time: {interaction['timestamp']}")
            print(f"Question: {interaction['question']}")
            print(f"Answer: {interaction['answer']}")
            print("-" * 50)
        
        # Test clearing chat history
        print("\n=== Clearing Chat History ===\n")
        success = chat_module.clear_chat_history(
            assistant_id=test_assistant_id,
            user_id=test_user_id,
            conversation_id=conversation_id
        )
        print(f"Chat history cleared: {success}")
        
        # Verify chat history is cleared
        empty_history = chat_module.get_chat_history(
            assistant_id=test_assistant_id,
            user_id=test_user_id,
            conversation_id=conversation_id
        )
        print(f"Chat history after clearing: {empty_history}")
        
    except Exception as e:
        logger.error(f"Error in main test function: {e}")
        raise

if __name__ == "__main__":
    main()