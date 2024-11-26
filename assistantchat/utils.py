from typing import List, Dict, Optional, Any, Generator
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
import logging
import uuid

from app.utils.vector_store import vector_store
from app.modals.chat import get_llm
from .models import Conversation
from users.models import SupabaseUser
from app.utils.assistant_manager import AssistantManager, AssistantConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatModule:
    def __init__(self):
        """
        Initialize the chat module with optional LLM injection for testing.
        
        :param llm: Optional language model, defaults to get_llm()
        """
        self.llm = get_llm()
        
    def _create_prompt(self, assistant_config: Dict[str, str]) -> ChatPromptTemplate:
        """
        Create a sophisticated chat prompt template based on assistant configuration.
        
        :param assistant_config: Configuration dictionary for the assistant
        :return: ChatPromptTemplate
        """
        template = f"""You are a specialized teaching assistant focusing on {assistant_config.get("subject", "")}.

        Teaching Methodology:
        {assistant_config.get("teacher_instructions", "General teaching principles:")}
        - Provide explanations that are clear, structured, and tailored to the learner's level
        - Break down complex concepts into digestible parts
        - Encourage critical thinking and deeper understanding
        - Use analogies, examples, or visual explanations when appropriate

        Subject-Specific Knowledge Domain:
        {assistant_config.get("subject", "General Academic Subject")} requires a nuanced approach that emphasizes:
        - Fundamental principles and core concepts
        - Practical applications and real-world relevance
        - Interconnections with related fields of study

        Contextual Knowledge Base:
        {{context}}

        Conversation History:
        {{chat_history}}

        Human Query: {assistant_config.get("prompt", "")}

        Response Guidelines:
        1. Directly address the specific question or learning objective
        2. Leverage the provided context to construct a comprehensive answer
        3. Maintain an engaging, supportive, and educational tone
        4. Adapt the complexity of the explanation to the learner's level

        Provide a detailed, structured, and insightful response."""
        
        return ChatPromptTemplate.from_template(template)

    def get_relevant_context(self, query: str, ass_id: str, k: int = 3) -> str:
        """
        Retrieve relevant context from vector store.
        
        :param query: Search query
        :param ass_id: Assistant ID
        :param k: Number of context results to retrieve
        :return: Concatenated context string
        """
        try:
            results = vector_store.similarity_search(
                query,
                k=k,
                filter={"ass_id": ass_id}
            )
            return "\n".join([doc.page_content for doc in results])
        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
            return ""

    def save_chat_history(
        self, 
        user_id: str, 
        ass_id: str, 
        prompt: str, 
        content: str, 
        conversation_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Save chat interaction to Django model with robust error handling.
        
        :param user_id: User's unique identifier
        :param ass_id: Assistant's identifier
        :param prompt: User's input prompt
        :param content: Assistant's response
        :param conversation_id: Optional conversation tracking ID
        """
        try:
            user = SupabaseUser.objects.get(id=user_id)
            conversation_id = conversation_id or uuid.uuid4()
            
            Conversation.objects.create(
                users_id=user,
                assistant_id=str(ass_id),
                prompt=prompt,
                content=content,
                conversation_id=conversation_id
            )
            
            logger.info(f"Chat history saved: {conversation_id}")
        except Exception as e:
            logger.error(f"Chat history save error: {e}")

    def process_message(
        self, 
        prompt: str, 
        ass_id: Any, 
        user_id: str, 
        assistant_config: dict,
        conversation_id: Optional[uuid.UUID] = None
    ) -> Generator[str, None, None]:
        """
        Process a chat message and generate a streaming response.
        
        :param prompt: User's input message
        :param ass_id: Assistant identifier
        :param user_id: User's identifier
        :param assistant_config: Assistant configuration
        :param conversation_id: Optional conversation tracking ID
        :return: Generator yielding response chunks
        """
        try:
            context = self.get_relevant_context(
                prompt, 
                str(ass_id.config.ass_id if hasattr(ass_id, 'config') else ass_id)
            )
            
            prompt_template = self._create_prompt(assistant_config)
            
            # Retrieve and format chat history
            chat_history = self.get_chat_history(
                ass_id=str(ass_id.config.ass_id if hasattr(ass_id, 'config') else ass_id), 
                user_id=user_id, 
                
            )
            chat_history_str = "\n".join([
                f"Human: {chat['question']}\nAssistant: {chat['answer']}"
                for chat in chat_history
            ])

            print(f"chat history: {chat_history_str}")

            def prepare_input(input_prompt):
                return {
                    "context": context,
                    "question": input_prompt,
                    "chat_history": chat_history_str,
                    "subject": assistant_config.get("subject", ""),
                }

            chain = (
                prepare_input
                | prompt_template
                | self.llm
                | StrOutputParser()
            )
            
            # Efficient response accumulation
            full_response_parts = []
            for chunk in chain.stream(prompt):
                full_response_parts.append(chunk)
                yield chunk

            # Save complete response
            full_response = ''.join(full_response_parts)
            self.save_chat_history(
                user_id=user_id,
                ass_id=str(ass_id.config.ass_id if hasattr(ass_id, 'config') else ass_id),
                prompt=prompt,
                content=full_response,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            yield "An error occurred while processing your message."

    def get_chat_history(
        self, 
        ass_id: str, 
        user_id: str, 
        conversation_id: Optional[uuid.UUID] = None
    ) -> List[Dict]:
        """
        Retrieve chat history with comprehensive filtering.
        
        :param ass_id: Assistant identifier
        :param user_id: User identifier
        :param conversation_id: Optional specific conversation ID
        :return: List of conversation dictionaries
        """
        try:
            query = Conversation.objects.filter(
                assistant_id=ass_id,
                users_id=user_id
            )
            
            if conversation_id:
                query = query.filter(conversation_id=conversation_id)
            
            conversations = query.order_by('-created_at')[:10]  # Limit to prevent excessive memory usage
            
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
            logger.error(f"Chat history retrieval error: {e}")
            return []

    def clear_chat_history(
        self, 
        ass_id: str, 
        user_id: str, 
        conversation_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Clear chat history with optional conversation-specific deletion.
        
        :param ass_id: Assistant identifier
        :param user_id: User identifier
        :param conversation_id: Optional specific conversation ID
        :return: Deletion success status
        """
        try:
            query = Conversation.objects.filter(
                assistant_id=ass_id,
                users_id_=user_id
            )
            
            if conversation_id:
                query = query.filter(conversation_id=conversation_id)
                
            deletion_count, _ = query.delete()
            logger.info(f"Deleted {deletion_count} conversation records")
            
            return deletion_count > 0
        except Exception as e:
            logger.error(f"Chat history clearing error: {e}")
            return False

    def get_conversation_list(self, user_id: str) -> List[Dict]:
        """
        Get paginated list of unique conversations for a user.
        
        :param user_id: User identifier
        :return: List of conversation metadata
        """
        try:
            conversations = Conversation.objects.filter(
                users_id=user_id
            ).values(
                'conversation_id',
                'created_at'
            ).distinct().order_by('-created_at')[:20]  # Limit to 20 recent conversations
            
            return [
                {
                    'conversation_id': str(conv['conversation_id']),
                    'created_at': conv['created_at']
                }
                for conv in conversations
            ]
        except Exception as e:
            logger.error(f"Conversation list retrieval error: {e}")
            return []