import os
from typing import List, Dict, Optional, Tuple
import dspy
import uuid
import logging

from app.utils.supabase_manager import SupabaseManager
from app.modals.assistants import TeachingAssistant, AssistantConfig
from app.modals.assitant_module import AssistantModule, AssistantInput


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
            logger.info(f"\nInitial create Assistant data from assistant manager: {config}\n")
            if not config.ass_id:  # Generate ass_id if not provided
                config.ass_id = uuid.uuid4()
            assistant = TeachingAssistant(config)
            
            logger.info(f"\nAfter create Assistant data: {config}\n")
            # Save assistant configuration to Supabase
            await assistant.save_to_supabase()
            
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
        logger.info(f"Before get Assistant data: {ass_id} {user_id}\n")
        try:
            # Check local cache first
            cache_key = f"{ass_id}_{user_id}"
            if cache_key in self.assistants:
                logger.info(f"Retrieved assistant from cache: {cache_key}")
                return self.assistants[cache_key]

            # If not found locally, check Supabase
            assistant_data = await self.supabase_manager.get_assistant(ass_id, user_id)
            logger.info(f"After get Assistant data: {assistant_data} \n")
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
    
    async def process_query(self, ass_id:uuid.UUID, user_id: uuid.UUID, query: str) -> Tuple[str, List[str]]:
        """Process a query using the appropriate assistant"""
        try:
            assistant = await self.get_assistant(ass_id, user_id)
            logger.info(f"get assistant in process query: {assistant}\n")
            if not assistant:
                return "Assistant not found.", []
            
            # Get relevant context
            context = await assistant.get_relevant_context(query)
            logger.info(f"Retreived context:\n {context}\n")
            
            # Use DSPy module to process query
            input_data = AssistantInput(
                subject=assistant.config.subject,
                context=context,
                query=query,
                teaching_instructions=assistant.config.teacher_instructions
            )

            # logger.info(f"Input data send to process query: {input_data}\n")
            # Process query using assistant module
            return await self.assistant_module.process_query(input_data)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Unable to process query at this time.", []
        
    
    async def update_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID, 
                             updates: Dict) -> Optional[TeachingAssistant]:
        """Update an existing assistant's configuration"""
        try:
            assistant = await self.get_assistant(ass_id, user_id)
            if not assistant:
                return None
            
            # Update configuration
            for key, value in updates.items():
                if hasattr(assistant.config, key):
                    setattr(assistant.config, key, value)
            
            # Save updates to Supabase
            await assistant.save_to_supabase()
            
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
    # Example usage with provided ass_id
    # config_with_id = AssistantConfig(
    #     user_id="0fe175e6-8a82-4fcf-8e45-baeaf289459f",
    #     ass_id=uuid.uuid4(),  # Providing an ass_id
    #     assistant_name='Physics numerical',
    #     subject='Physics',
    #     teacher_instructions='Explain concepts clearly with examples',
    #     knowledge_base=['D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf']
    # )

    assistant_manager = AssistantManager()
    # assistant_with_id = await assistant_manager.create_assistant(config_with_id)

    # print(f"Assistant create with id{assistant_with_id}")
    # Example usage without providing ass_id
    config_without_id = AssistantConfig(
        user_id="0fe175e6-8a82-4fcf-8e45-baeaf289459f",
        assistant_name='Chemist',
        subject='Chemistry',
        teacher_instructions='Provide detailed explanations.',
        knowledge_base=['D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf']
    )

    # assistant_without_id = await assistant_manager.create_assistant(config_without_id)

    # The assistant's config will now have the generated ass_id if it was not provided
    # print(f"Assistant create with id{assistant_without_id}")  # This will show the generated ass_id
    


    # Test Get assistant
    get_assistant = await assistant_manager.get_assistant("a558445a-df9a-4ea1-81ef-3f580dba1742", "0fe175e6-8a82-4fcf-8e45-baeaf289459f")
    print("Get assitant", get_assistant)
    
    # # Process a query
    explanation, examples = await assistant_manager.process_query(
        "855e07bb-332a-4557-a5ef-d95006051390",
        "0fe175e6-8a82-4fcf-8e45-baeaf289459f",
        "Explain the setup python on windows?"
    )
    
    print("Explanation:", explanation)
    print("Examples:", examples)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())