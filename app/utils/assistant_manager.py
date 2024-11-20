import os
from typing import List, Dict, Optional, Any, Generator, Tuple
import dspy
import uuid
import logging

from app.utils.supabase_manager import SupabaseManager
from app.modals.assistants import TeachingAssistant, AssistantConfig
from app.modals.assitant_module import AssistantModule, AssistantInput
from app.utils.vector_store import vector_store
from dotenv import load_dotenv

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantManager:
    def __init__(self):
        """Initialize the AssistantManager with necessary components."""
        self.assistants: Dict[str, TeachingAssistant] = {}
        self.supabase_manager = SupabaseManager()
        self.assistant_module = AssistantModule()
        
        # Initialize DSPy with preferred language model
        self.lm = dspy.GROQ(model="llama-3.1-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
        dspy.settings.configure(lm=self.lm)

    # Create and save new assistant here
    def create_assistant(self, config) -> TeachingAssistant:
        """Create and save a new teaching assistant.

        Args:
            config: Configuration for the assistant.

        Returns:
            TeachingAssistant: The created assistant instance.
        """
        try:
            assistant = TeachingAssistant(config)
            
            # Log the user_id being used
            logger.info(f"Creating assistant for user_id: {assistant.config.user_id}")
        
            # Save assistant configuration to Supabase
            assistant_data = assistant.save_to_supabase()
            logger.info(f"\nSuccessfully saved assistant with: {assistant_data}\n")
            
            # Initialize knowledge base if provided
            if config.knowledge_base:
                assistant.initialize_knowledge_base(config.knowledge_base)
            
            # Cache the assistant
            self.assistants[assistant.config.assistant_name] = assistant
            
            return assistant
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise
    
    def get_assistant(self, ass_id: uuid.UUID) -> Optional[TeachingAssistant]:
        """Retrieve an assistant by ID with caching"""
        try:
            # Check local cache first
            cache_key = f"G-{ass_id}_jk"
            if cache_key in self.assistants:
                logger.info(f"Retrieved assistant from cache: {cache_key}")
                return self.assistants[cache_key]

            # If not found locally, check Supabase
            assistant_data = self.supabase_manager.get_assistant(ass_id)
            # logger.info(f"Successfully get Assistant data: {assistant_data} \n")
            if assistant_data:
                config = AssistantConfig(**assistant_data)
                assistant = TeachingAssistant(config)
                
                # Cache the assistant
                self.assistants[cache_key] = assistant
                logger.info(f"Retrieved assistant from Supabase: {cache_key}")
                return assistant
            
            logger.warning(f"Assistant not found: {ass_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving assistant: {e}")
            return None
    
    def list_assistants(self) -> List[TeachingAssistant]:
        """Retrieve all assistants for a given user."""
        try:
            # Retrieve assistant data from Supabase
            assistants_data = self.supabase_manager.list_assistants()
            
            assistants = []
            for assistant_data in assistants_data:
                config = AssistantConfig(**assistant_data)
                assistant = TeachingAssistant(config)
                assistants.append(assistant)
            
            return assistants
        except Exception as e:
            logger.error(f"Error listing assistants: {e}")
            return []

    def process_query(self, ass_id, user_id, query: str) -> Tuple[str, List[str]]:
        """Process a query using the appropriate assistant.

        Args:
            ass_id: The assistant's ID.
            user_id: The user's ID.
            query: The query string to process.

        Returns:
            Tuple[str, List[str]]: The explanation and any examples generated.
        """
        try:
            assistant = self.get_assistant(ass_id, user_id)
            logger.info(f"get assistant in process query: {assistant.config.ass_id}\n")
            if not assistant:
                return "Assistant not found.", []
            
            context = assistant.get_relevant_context_in_chunks(query, user_id, ass_id)
            text_context = context.replace('\t', ' ')

            complete_context = self.supabase_manager.get_documents(assistant.config.ass_id, assistant.config.user_id)
            # text = "\n".join([x.page_content for x in complete_context])
            

            input_data = AssistantInput(
                subject=assistant.config.subject,
                # context="\n".join(text_context),
                context=text_context,
                query=query,
                teaching_instructions=assistant.config.teacher_instructions
            )
            # logger.info(f"Input data send to process query: {input_data}\n")
            
            # Process query using assistant module
            result = self.assistant_module.process_query(input_data)

            return result
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Unable to process query at this time.", []
        
    def update_assistant(self, ass_id, user_id, updates: Dict) -> Optional[TeachingAssistant]:
        """Update an existing assistant's configuration.

        Args:
            ass_id: The assistant's ID.
            user_id: The user's ID.
            updates: A dictionary of updates to apply.

        Returns:
            Optional[TeachingAssistant]: The updated assistant or None if not found.
        """
        try:
            assistant = self.get_assistant(ass_id, user_id)
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
            self.supabase_manager.update_assistant(data)
            
            # Update cache
            cache_key = f"{ass_id}_{user_id}"
            self.assistants[cache_key] = assistant
            
            
            return assistant
        except Exception as e:
            logger.error(f"Error updating assistant: {e}")
            return None
    
    def delete_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete an assistant and its associated data.

        Args:
            ass_id (uuid.UUID): The assistant's ID.
            user_id (uuid.UUID): The user's ID.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            success = self.supabase_manager.delete_assistant(ass_id, user_id)
            
            # Remove from cache
            cache_key = f"{ass_id}_{user_id}"
            if cache_key in self.assistants:
                del self.assistants[cache_key]
            
            return success
        except Exception as e:
            logger.error(f"Error deleting assistant: {e}")
            return False
        



def main():

    assistant_manager = AssistantManager()

    # config_without_id = AssistantConfig(
    #     user_id="efbfba82-eb0e-4019-b9c5-370b24a7f9c1",
    #     
    #     assistant_name='Pythonic',
    #     subject='Python Basics and Advance Level',
    #     teacher_instructions='Provide detailed explanations according to the knowledge_base documents provided.',
    #     knowledge_base=['D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf']
    # )

    # # Test for create assistant
    # create_assistant = assistant_manager.create_assistant(config_without_id)
    # print(f"Successfully create assistant: {create_assistant.config}")
    
    # update_data = {
    #     "user_id":"efbfba82-eb0e-4019-b9c5-370b24a7f9c1",
    #     "ass_id": "4e3e58e8-620a-4a3b-b143-1097f4ce613f",
    #     "assistant_name": 'Pythonic',
    #     "subject": 'Python Basics and Advance Level',
    #     "teacher_instructions": 'Provide complete explanations that align with the knowledge base context and cover all topics according to the query, ensuring all information is derived from the knowledge_base documents without any external references.',
    #     # "knowledge_base": ['D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf']
    # }

    # Test for get assistant
    # get_assistant = assistant_manager.get_assistant(create_assistant.config.ass_id, "efbfba82-eb0e-4019-b9c5-370b24a7f9c1")
    # print("Get assitant", get_assistant.config.ass_id)
    
    # Test for update assistant
    # assistant_without_id = assistant_manager.update_assistant(updates=update_data, ass_id="4e3e58e8-620a-4a3b-b143-1097f4ce613f", user_id="efbfba82-eb0e-4019-b9c5-370b24a7f9c1")
    # The assistant's config will now have the generated ass_id if it was not provided
    # print(f"Successfully Assistant update with id: {assistant_without_id.config.assistant_name}")  # This will show the generated ass_id
    

    # # Process a query
    explanation = assistant_manager.process_query(
        "4e3e58e8-620a-4a3b-b143-1097f4ce613f",
        "efbfba82-eb0e-4019-b9c5-370b24a7f9c1",
        "Write a factorial program in python."
    )
    
    # for response in explanation:
    print("Streaming response:", explanation)
    # print("Rationale:", rationale)

if __name__ == "__main__":
    main()