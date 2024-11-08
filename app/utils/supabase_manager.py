import logging
from app.configs.supabase_config import SUPABASE_CLIENT, url, key
from supabase import Client
import uuid
from typing import Optional
import datetime
from pydantic import BaseModel


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    """Pydantic model for document metadata"""
    doc_id: uuid.UUID
    file_name: str
    upload_date: datetime.datetime
    ass_id: uuid.UUID
    user_id: uuid.UUID



class SupabaseManager:
    """Handle Supabase database operations"""
    def __init__(self):

        if not url or not key:
            raise EnvironmentError("Supabase credentials not found in environment variables")
        self.client = SUPABASE_CLIENT

    async def save_assistant(self, assistant_data: dict) -> dict:
        """Save assistant data to Supabase"""
        try:
            logger.info(f"Assistant data: {assistant_data}")
            response = self.client.table('assistants').insert(assistant_data).execute()
            logger.info(f"Assistant data: {response}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving assistant to Supabase: {e}")
            raise

    async def save_document(self, document_metadata: DocumentMetadata) -> dict:
        """Save document metadata to Supabase"""
        try:
            data = document_metadata.model_dump()
            print(data)
            data['doc_id'] = str(data['doc_id'])
            data['ass_id'] = str(data['ass_id'])
            data['user_id'] = str(data['user_id'])
            data['upload_date'] = data['upload_date'].isoformat()
            
            print(f"\n\nsupabase data: {data}\n\n")
            response = await self.client.table('documents').insert(data).execute()
            print(f"\n\nsupabase response: {response}\n\n")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving document to Supabase: {e}")
            raise

    async def get_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
        """Retrieve assistant data from Supabase"""
        logger.info(f"Get Assistant data from supabase: {ass_id} {user_id}\n")
        try:
            response = self.client.table('assistants').select("*").eq('ass_id', str(ass_id)).eq('user_id', str(user_id)).execute()
            logger.info(f"After Get Assistant data from supabase: {response}\n")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error retrieving assistant from Supabase: {e}")
            raise