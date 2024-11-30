from typing import List, Dict, Optional, Any, Generator
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from datetime import datetime
import logging
import uuid

from django.contrib.auth.models import User
from app.utils.vector_store import vector_store
from app.modals.chat import get_llm
from .models import Conversation
from users.models import Assistant, SupabaseUser, DocumentChunk
from app.utils.assistant_manager import AssistantManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatModule:
    def __init__(self):
        """Initialize the chat module with necessary components."""
        self.llm = get_llm()
        

    def _create_prompt(self, assistant_config) -> ChatPromptTemplate:
        """Create a chat prompt template based on assistant configuration."""
        template = f"""You are a teaching assistant specialized in {assistant_config.get("subject", "")}.
        
        Instructions: {assistant_config.get("teacher_instructions", "")}
        
        Context from knowledge base:
        {{context}}
        
        Chat History:
        {{chat_history}}
        
        Human Question: {{question}}
        
        Provide a clear, detailed response based on the context and your expertise. If the question cannot be fully answered using the provided context, state that clearly but provide the best possible answer from what is available."""
        
        prompt = ChatPromptTemplate.from_template(template)
        return prompt

    def get_relevant_context(self, query: str, assistant_id: str, k: int = 3, api_key: Optional[str] = None) -> str:
        """Retrieve relevant context from the DocumentChunk model based on similarity search."""
        try:
            # Step 1: Call the similarity_search class method from DocumentChunk
            results = DocumentChunk.similarity_search(query=query, k=k, api_key=api_key)
            
            # Step 2: Filter results by assistant ID (assistant_id)
            relevant_chunks = [
                chunk for chunk, _ in results
                if chunk.document.assistant_id == assistant_id
            ]
            
            # Step 3: Extract and combine the content of the top-k relevant chunks
            context = "\n".join([chunk.content for chunk in relevant_chunks])
            
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
            
            # If no conversation_id provided, create a new one
            if not conversation_id:
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
                        limit: int = 10) -> List[Dict]:
        """Retrieve chat history from Django model."""
        try:
            # Base query
            query = Conversation.objects.filter(
                assistant_id=assistant_id,
                user_id=user_id
            )
            
            # Add conversation_id filter if provided
            if conversation_id:
                query = query.filter(conversation_id=conversation_id)
            
            # Get latest conversations
            conversations = query.order_by('-created_at')[:limit]
            
            # Convert to list of dicts for consistency with existing code
            return [
                {
                    'question': conv.prompt,
                    'answer': conv.content,
                    'timestamp': conv.created_at,
                    'conversation_id': conv.conversation_id
                }
                for conv in conversations
            ]
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []

    def process_message(self, prompt: str, assistant_id: str, 
                       user_id: str, assistant_config: dict,
                       conversation_id: Optional[uuid.UUID] = None) -> Generator[Any, Any, Any]:
        """Process a chat message and generate a response."""
        try:
            # Get relevant context
            context = self.get_relevant_context(prompt, assistant_id)
            
            # Create prompt
            prompt_template = self._create_prompt(assistant_config)
            
            # Get chat history
            chat_history = self.get_chat_history(
                assistant_id, 
                user_id, 
                conversation_id=conversation_id
            )
            chat_history_str = "\n".join([
                f"Human: {chat['question']}\nAssistant: {chat['answer']}"
                for chat in chat_history
            ])

            def prepare_input(input_prompt):
                return {
                    "context": context,
                    "question": input_prompt,
                    "chat_history": chat_history_str,
                    "subject": assistant_config.get("subject", ""),
                    "instructions": assistant_config.get("teacher_instructions", "")
                }
            # Create chain
            chain = (
                prepare_input
                | prompt_template
                | self.llm
                | StrOutputParser()
            )
            
            # Generate response
            response = chain.stream(prompt)
            
            # Save interaction
            self.save_chat_history(
                user_id=user_id,
                assistant_id=assistant_id,
                prompt=prompt,
                content=response,
                conversation_id=conversation_id
            )
            
            for chunk in response:
                if chunk:
                    yield chunk
            
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