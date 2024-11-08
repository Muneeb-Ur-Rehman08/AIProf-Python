import os
from typing import List, Dict, Optional, Tuple
import dspy
import uuid
import logging

from app.utils.supabase_manager import SupabaseManager
from app.modals.assistants import TeachingAssistant, AssistantConfig
from app.modals.assitant_module import AssistantModule, AssistantInput
from app.utils.vector_store import vector_store


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantManager:
    def __init__(self):
        self.assistants: Dict[str, TeachingAssistant] = {}
        self.supabase_manager = SupabaseManager()
        self.assistant_module = AssistantModule()
        
        # Initialize DSPy with preferred language model
        self.lm = dspy.GROQ(model="gemma2-9b-it", api_key=os.getenv("GROQ_API_KEY"))
        dspy.settings.configure(lm=self.lm)

    # Create and save new assistant here
    async def create_assistant(self, config) -> TeachingAssistant:
        """Create and save a new teaching assistant"""
        try:
            assistant = TeachingAssistant(config)
            
            # Save assistant configuration to Supabase
            assistant_data = await assistant.save_to_supabase()
            logger.info(f"\nSuccessfully saved assistant with: {assistant_data}\n")
            
            # Initialize knowledge base if provided
            if config.knowledge_base:
                await assistant.initialize_knowledge_base(config.knowledge_base)
            
            # Cache the assistant
            self.assistants[assistant.config.assistant_name] = assistant
            
            return assistant
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise
    
    # Get existing assistant here
    async def get_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> Optional[TeachingAssistant]:
        """Retrieve an assistant by ID with caching"""
        try:
            # Check local cache first
            cache_key = f"{ass_id}_{user_id}"
            if cache_key in self.assistants:
                logger.info(f"Retrieved assistant from cache: {cache_key}")
                return self.assistants[cache_key]

            # If not found locally, check Supabase
            assistant_data = await self.supabase_manager.get_assistant(ass_id, user_id)
            # logger.info(f"Successfully get Assistant data: {assistant_data} \n")
            if assistant_data:
                config = AssistantConfig(**assistant_data)
                assistant = TeachingAssistant(config)
                
                # Cache the assistant
                self.assistants[cache_key] = assistant
                logger.info(f"Retrieved assistant from Supabase: {cache_key}")
                return assistant
            
            logger.warning(f"Assistant not found: {ass_id}, {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving assistant: {e}")
            return None
    
    async def process_query(self, ass_id, user_id, query: str) -> Tuple[str, List[str]]:
        """Process a query using the appropriate assistant"""
        try:
            assistant = await self.get_assistant(ass_id, user_id)
            logger.info(f"get assistant in process query: {assistant.config.ass_id}\n")
            if not assistant:
                return "Assistant not found.", []
            
            context = await assistant.get_relevant_context_in_chunks(query, user_id, ass_id)
            logger.info(f"Retreived context:\n {context}\n")
            
            # Use DSPy module to process query
            input_data = AssistantInput(
                subject=assistant.config.subject,
                context=context,
                query=query,
                teaching_instructions=assistant.config.teacher_instructions
            )
            result = await self.assistant_module.process_query(input_data)
            # logger.info(f"Input data send to process query: {input_data}\n")
            # Process query using assistant module
            return result
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Unable to process query at this time.", []
        
    
    async def update_assistant(self, ass_id, user_id, 
                             updates: Dict) -> Optional[TeachingAssistant]:
        """Update an existing assistant's configuration"""
        try:
            assistant = await self.get_assistant(ass_id, user_id)
            if not assistant:
                return None
            logger.info(f"the data need to be updated: {updates}")
            # Update configuration
            for key, value in updates.items():
                if hasattr(assistant.config, key):
                    setattr(assistant.config, key, value)
            data = {
                "user_id": str(assistant.config.user_id),
                "ass_id": str(assistant.config.ass_id),
                "assistant_name": assistant.config.assistant_name,
                "subject": assistant.config.subject,
                "teacher_instructions": assistant.config.teacher_instructions,
            }
            if assistant.config.knowledge_base:
                assistant.initialize_knowledge_base(assistant.config.knowledge_base)
            logger.info(f"data need to be updated: {assistant}\n")
            # Save updates to Supabase
            await self.supabase_manager.update_assistant(data)
            
            # Update cache
            cache_key = f"{ass_id}_{user_id}"
            self.assistants[cache_key] = assistant
            
            
            return assistant
        except Exception as e:
            logger.error(f"Error updating assistant: {e}")
            return None
    
    async def delete_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete an assistant and its associated data"""
        try:
            # Remove from Supabase
            success = await self.supabase_manager.delete_assistant(ass_id, user_id)
            
            # Remove from cache
            cache_key = f"{ass_id}_{user_id}"
            if cache_key in self.assistants:
                del self.assistants[cache_key]
            
            return success
        except Exception as e:
            logger.error(f"Error deleting assistant: {e}")
            return False
        



async def main():

    assistant_manager = AssistantManager()
    
    update_data = {
        # "user_id":"0fe175e6-8a82-4fcf-8e45-baeaf289459f",
        # "ass_id": "deddc9c6-be68-42e6-a6f7-de1d26fffe07",
        "assistant_name": 'Pythonic',
        "subject": 'Python Basics and Advance Level',
        "teacher_instructions": 'Provide detailed explanations according not to go outside from the knowledge_base documents provided',
        # "knowledge_base": "['D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf']"
    }

    # Test for get assistant
    get_assistant = await assistant_manager.get_assistant("1e4c86be-e8bb-4351-8849-1e0a59f4fa63", "0fe175e6-8a82-4fcf-8e45-baeaf289459f")
    print("Get assitant", get_assistant.config.ass_id)
    
    # Test for update assistant
    assistant_without_id = await assistant_manager.update_assistant(updates=update_data, ass_id=str(get_assistant.config.ass_id), user_id=str(get_assistant.config.user_id))
    # The assistant's config will now have the generated ass_id if it was not provided
    print(f"Successfully Assistant update with id: {assistant_without_id}")  # This will show the generated ass_id
    
    # assistant_delete = await assistant_manager.delete_assistant("dc6693b2-7796-4ffc-b9fa-e1498bab85bf", "0fe175e6-8a82-4fcf-8e45-baeaf289459f")

    # # Process a query
    explanation, examples = await assistant_manager.process_query(
        "1e4c86be-e8bb-4351-8849-1e0a59f4fa63",
        "0fe175e6-8a82-4fcf-8e45-baeaf289459f",
        "Explain the setup python on windows?"
    )
    
    print("Explanation:", explanation)
    print("Examples:", examples)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())