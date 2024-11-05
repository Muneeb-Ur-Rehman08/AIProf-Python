import os
from typing import List, Dict, Optional, Tuple
import dspy
from datetime import datetime
import uuid
from pydantic import BaseModel
import logging
from app.utils.vector_store import (
    store_embedding_vectors_in_supabase,
    get_split_documents,
    get_answer,
    vector_store
)
from app.utils.supabase_manager import SupabaseManager, DocumentMetadata 
from app.modals.chat import get_llm
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class AssistantConfig(BaseModel):
    """Pydantic model for assistant configuration with validation"""
    user_id: uuid.UUID
    ass_id: uuid.UUID
    name: str
    subject: str
    teacher_instructions: str
    knowledge_base: Optional[List[str]] = None
    
    class Config:
        arbitrary_types_allowed = True


class TeachingAssistant:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.vector_store = vector_store
        self.supabase_manager = SupabaseManager()
        self.documents: List[DocumentMetadata] = []

    async def save_to_supabase(self) -> dict:
        """Save assistant configuration to Supabase"""
        assistant_data = {
            "user_id": str(self.config.user_id),
            "ass_id": str(self.config.ass_id),
            "name": self.config.name,
            "subject": self.config.subject,
            "teacher_instructions": self.config.teacher_instructions,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        logger.info(f"Assistant data {assistant_data}")
        return await self.supabase_manager.save_assistant(assistant_data)

    async def initialize_knowledge_base(self, pdf_paths: List[str]) -> None:
        """Initialize knowledge base with PDF documents and save to Supabase"""
        try:
            for pdf_path in pdf_paths:
                # Load and process PDF
                # Create and save document metadata
                doc_metadata = DocumentMetadata(
                    doc_id=str(uuid.uuid4()),
                    file_name=os.path.basename(pdf_path),
                    upload_date=datetime.now().isoformat(),
                    ass_id=str(self.config.ass_id),
                    user_id=str(self.config.user_id)
                )
                saved_document = await self.supabase_manager.save_document(doc_metadata)
                self.documents.append(doc_metadata)
                print(f"Document saved: {saved_document}")  # Fetch and print the saved document

                # Process and store embeddings with metadata
                split_documents = get_split_documents(pdf_path)
                for doc in split_documents:
                    doc.metadata["doc_id"] = str(doc_metadata.doc_id)
                    doc.metadata["file_name"] = doc_metadata.file_name
                    doc.metadata["upload_date"] = doc_metadata.upload_date
                    doc.metadata["ass_id"] = doc_metadata.ass_id
                    doc.metadata["user_id"] = doc_metadata.user_id

                # Store the document data in vector form with metadata in Supabase
                result_data = {
                    "id": str(doc_metadata.doc_id),
                    "source": doc_metadata.file_name,
                    "metadata": {
                        "doc_id": str(doc_metadata.doc_id),
                        "file_name": doc_metadata.file_name,
                        "upload_date": doc_metadata.upload_date,
                        "ass_id": doc_metadata.ass_id,
                        "user_id": doc_metadata.user_id
                    }
                }
                await store_embedding_vectors_in_supabase(result_data)
                print(f"Document data stored in vector form with metadata: {result_data}")
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            raise
    async def get_relevant_context(self, query: str) -> str:
        """Get relevant context from vector store with error handling"""
        try:
            if not self.vector_store:
                logger.warning("Vector store not initialized")
                return ""
            
            docs = await self.vector_store.similarity_search(
                query,
                k=1,
                filter={
                    "ass_id": str(self.config.ass_id),
                    
                    "user_id": str(self.config.user_id)
                }
            )
            return "\n".join(doc.page_content for doc in docs)
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

class AssistantManager:
    def __init__(self):
        self.assistants: Dict[str, TeachingAssistant] = {}
        self.supabase_manager = SupabaseManager()
        
        # Initialize DSPy with preferred language model
        self.lm = dspy.GROQ(model="gemma2-9b-it", api_key=os.getenv("GROQ_API_KEY"))
        dspy.settings.configure(lm=self.lm)

    async def create_assistant(self, config: AssistantConfig) -> TeachingAssistant:
        """Create and save a new teaching assistant"""
        try:
            assistant = TeachingAssistant(config)
            await assistant.save_to_supabase()
            self.assistants[assistant.config.name] = assistant
            return assistant
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise

    async def get_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> Optional[TeachingAssistant]:
        """Retrieve an assistant by ID"""
        try:
            # Check local cache first
            for assistant in self.assistants.values():
                if assistant.config.ass_id == ass_id and assistant.config.user_id == user_id:
                    return assistant

            # If not found locally, check Supabase
            assistant_data = await self.supabase_manager.get_assistant(ass_id, user_id)
            if assistant_data:
                config = AssistantConfig(**assistant_data)
                assistant = TeachingAssistant(config)
                self.assistants[assistant.config.name] = assistant
                return assistant
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving assistant: {e}")
            return None
        

async def main():
       test_config = AssistantConfig(
           user_id=uuid.uuid4(),
           ass_id=uuid.uuid4(),
           name="Math Teaching Assistant",
           subject="Mathematics",
           teacher_instructions="""
           Explain concepts clearly with examples and visual aids.
           Focus on step-by-step problem solving.
           Provide practice problems for reinforcement.
           """,
           knowledge_base=["D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf"]
       )

       # Initialize manager and create assistant
       async def test_initialize_knowledge_base():
           try:
               # Create a TeachingAssistant instance
               assistant = TeachingAssistant(test_config)
               # Initialize knowledge base with a PDF path
               pdf_path = "D:\\MyProjects\\pythonProject\\Python-Learn-in-24hrs.pdf"
               await assistant.initialize_knowledge_base([pdf_path])
               print("Knowledge base initialized successfully.")
           except Exception as e:
               logger.error(f"Error initializing knowledge base: {e}")
               raise

       # Call the test function
       await test_initialize_knowledge_base()
       manager = AssistantManager()
       assistant = await manager.create_assistant(test_config)
       print("successfully create assistant",assistant)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())