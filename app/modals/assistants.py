import os
from typing import List, Dict, Optional, Tuple
import dspy
from datetime import datetime
import uuid
from pydantic import BaseModel
import logging
from dotenv import load_dotenv

from app.utils.vector_store import (
    store_embedding_vectors_in_supabase,
    vector_store
)
from app.utils.supabase_manager import SupabaseManager, DocumentMetadata 
from app.configs.supabase_config import SUPABASE_CLIENT


load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class AssistantConfig(BaseModel):
    """Pydantic model for assistant configuration with validation"""
    user_id: uuid.UUID
    ass_id: Optional[uuid.UUID] = None
    assistant_name: str
    subject: str
    teacher_instructions: str
    knowledge_base: Optional[List[str]] = None
    
    class Config:
        arbitrary_types_allowed = True


class TeachingAssistant:
    def __init__(self, config: AssistantConfig):
        """Initialize the TeachingAssistant with configuration.

        Args:
            config (AssistantConfig): The configuration for the assistant.
        """
        self.config = config
        self.supabase_manager = SupabaseManager()
        self.supabase_client = SUPABASE_CLIENT
        self.documents: List[DocumentMetadata] = []
        
    
    def save_to_supabase(self) -> dict:
        """Save assistant configuration to Supabase.

        Returns:
            dict: The response from Supabase containing assistant data.
        """
        assistant_data = {
            "user_id": str(self.config.user_id),
            # "ass_id": str(self.config.ass_id),
            "assistant_name": self.config.assistant_name,
            "subject": self.config.subject,
            "teacher_instructions": self.config.teacher_instructions,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Save to Supabase and retrieve the generated ass_id if not provided
        response = self.supabase_manager.save_assistant(assistant_data)
        
        # If ass_id was not provided, update the config with the generated ass_id
        if not self.config.ass_id:
            self.config.ass_id = response['ass_id']
        return response


    def initialize_knowledge_base(self, pdf_paths: List[str]) -> None:
        """Initialize knowledge base with PDF documents and save to Supabase.

        Args:
            pdf_paths (List[str]): List of paths to PDF documents.
        """
        try:
            for pdf_path in pdf_paths:
                
                store_embedding_vectors_in_supabase(pdf_path, self.config.user_id, self.config.ass_id)
                
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            raise

    def get_relevant_context_in_chunks(self, query: str, user_id: uuid.UUID, ass_id: uuid.UUID) -> List[str]:
        """Retrieve relevant context from the vector store in chunks.

        Args:
            query (str): The query string to search for.
            user_id (uuid.UUID): The user's ID.
            ass_id (uuid.UUID): The assistant's ID.

        Returns:
            List[str]: The relevant context retrieved.
        """
        try:
            context = vector_store.similarity_search(
                query,
                k=5,
                filter={
                    "ass_id": str(ass_id),
                    "user_id": str(user_id)
                }
            )
            return "\n".join([x.page_content for x in context])
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return []

    def explain_concept(self, concept: str) -> Tuple[str, List[str]]:
        """Explain a concept using the ConceptExplainer module with context.

        Args:
            concept (str): The concept to explain.

        Returns:
            Tuple[str, List[str]]: The explanation and any examples generated.
        """
        try:
            context = self.get_relevant_context(concept)
            prompt = dspy.Template(
                """
                Subject: {subject}
                Context: {context}
                Concept to explain: {concept}
                Teacher instructions: {instructions}
                
                Provide a clear explanation and relevant examples.
                """
            )
            
            response = self.lm.generate(
                prompt.format(
                    subject=self.config.subject,
                    context=context,
                    concept=concept,
                    instructions=self.config.teacher_instructions
                )
            )
            
            # Parse response into explanation and examples
            # This is a simplified version - you might want to add more structure
            explanation = response.text.split("Examples:")[0].strip()
            examples = response.text.split("Examples:")[1].strip().split("\n") if "Examples:" in response.text else []
            
            return explanation, examples
        except Exception as e:
            logger.error(f"Error explaining concept: {e}")
            return "Unable to explain concept at this time.", []

