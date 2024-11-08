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
        self.config = config
        self.supabase_manager = SupabaseManager()
        self.supabase_client = SUPABASE_CLIENT
        self.documents: List[DocumentMetadata] = []
        

    async def save_to_supabase(self) -> dict:
        """Save assistant configuration to Supabase"""
        logger.info(f"Before save Assistant data: {self.config}")
        assistant_data = {
            "user_id": str(self.config.user_id),
            # "ass_id": str(self.config.ass_id),
            "assistant_name": self.config.assistant_name,
            "subject": self.config.subject,
            "teacher_instructions": self.config.teacher_instructions,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        # Include ass_id if provided
        if self.config.ass_id:
            assistant_data["ass_id"] = str(self.config.ass_id)

        logger.info(f"After add dictAssistant data {assistant_data}")

        # Save to Supabase and retrieve the generated ass_id if not provided
        response = await self.supabase_manager.save_assistant(assistant_data)
        
        # If ass_id was not provided, update the config with the generated ass_id
        if not self.config.ass_id:
            self.config.ass_id = response['ass_id']
        return response

    async def initialize_knowledge_base(self, pdf_paths: List[str]) -> None:
        """Initialize knowledge base with PDF documents and save to Supabase"""
        try:
            for pdf_path in pdf_paths:
                logger.info(f"Assistant data: {self.config}")
                docs = store_embedding_vectors_in_supabase(pdf_path, self.config.user_id, self.config.ass_id)
                logger.info(f"Doc data: {docs}")
                docs
                
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            raise


    async def get_relevant_context(self, query: str) -> str:
        """Get relevant context from vector store with error handling"""
        try:
            logger.info(f"Table name vector store: {vector_store.table_name}\n")
            if not vector_store:
                logger.warning("Vector store not initialized")
                return ""
            
            # Log the filter values
            logger.info(f"Searching for context with ass_id: {self.config.ass_id}, user_id: {self.config.user_id}, query: {query}")
            content_id = self.supabase_client.table("documents") \
                .select("id", "metadata", "embedding") \
                .filter("metadata->>ass_id", "eq", self.config.ass_id) \
                .filter("metadata->>user_id", "eq", self.config.user_id) \
                .execute()
            
            logger.info(f"Content id {content_id.data[0]['id']}")

            
            # Await the similarity_search if it's a coroutine
            docs_data = vector_store.similarity_search(
                query=query,
                k=1,
                filter={
                    "metadata->>ass_id": str(self.config.ass_id),
                    "metadata->>user_id": str(self.config.user_id)
                }
            )
            
            logger.info(f"Docs from similarity search: {docs_data}")
            
            if not docs_data:
                logger.warning("No documents found for the given query and filters.")
                return ""  # Return empty context if no documents found
            
            # Ensure that docs is a list of objects that have a page_content attribute
            return docs_data[0].page_content  # This assumes docs is a list of objects
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return ""

    async def explain_concept(self, concept: str) -> Tuple[str, List[str]]:
        """Explain a concept using the ConceptExplainer module with context"""
        try:
            context = await self.get_relevant_context(concept)
            prompt = dspy.Template(
                """
                Subject: {subject}
                Context: {context}
                Concept to explain: {concept}
                Teacher instructions: {instructions}
                
                Provide a clear explanation and relevant examples.
                """
            )
            
            response = await self.lm.generate(
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

