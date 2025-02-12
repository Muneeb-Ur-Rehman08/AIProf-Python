import logging
from app.configs.supabase_config import SUPABASE_CLIENT, url, key
from supabase import Client
import uuid
from typing import Optional, List, Dict, Any
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

    # Save assistant to Supabase
    def save_assistant(self, assistant_data: dict) -> dict:
        """Save assistant data to Supabase"""
        try:
            response = self.client.table('assistants').insert(assistant_data).execute()
            logger.info(f"Assistant data save: {response}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving assistant to Supabase: {e}")
            raise

    def update_assistant(self, assistant_data: dict) -> dict:
        """Save assistant data to Supabase"""
        try:
            logger.info(f"data send for the update: {assistant_data}")
            response = self.client.table('assistants')\
                .update(assistant_data)\
                .eq("ass_id", assistant_data["ass_id"])\
                .eq("user_id", assistant_data["user_id"])\
                .execute()
            logger.info(f"Assistant data update: {response}")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving assistant to Supabase: {e}")
            raise

    def save_document(self, document_metadata: DocumentMetadata) -> dict:
        """Save document metadata to Supabase"""
        try:
            data = document_metadata.model_dump()
            print(data)
            data['doc_id'] = str(data['doc_id'])
            data['ass_id'] = str(data['ass_id'])
            data['user_id'] = str(data['user_id'])
            data['upload_date'] = data['upload_date'].isoformat()
            
            print(f"\n\nsupabase data: {data}\n\n")
            response = self.client.table('documents').insert(data).execute()
            print(f"\n\nsupabase response: {response}\n\n")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving document to Supabase: {e}")
            raise

    def get_assistant(self, ass_id: uuid.UUID) -> Optional[dict]:
        """Retrieve assistant data from Supabase"""
        try:
            response = self.client.table('assistants').select("*").eq('ass_id', str(ass_id)).execute()
            logger.info(f"After Get Assistant data from supabase: {response}\n")
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error retrieving assistant from Supabase: {e}")
            raise
    
    def list_assistants(self) -> List[Dict[str, Any]]:
        """Retrieve all assistants for a given user from Supabase."""
        try:
            # Adjust the query based on your Supabase table structure
            result = self.client.table('assistants').select("*").execute()
            print("Assistants", result)
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Supabase error listing assistants: {e}")
            return []

    def delete_assistant(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete assistant data from Supabase"""
        try:
            response = self.client.table('assistants').delete().eq('ass_id', str(ass_id)).eq('user_id', str(user_id)).execute()
            return response
        except Exception as e:
            logger.error(f"Error deleting assistant from Supabase: {e}")
            raise

    def get_documents(self, ass_id: uuid.UUID, user_id: uuid.UUID) -> Optional[dict]:
        """Retrieve documents data from Supabase"""
        logger.info(f"Get Assistant data from supabase: {ass_id} {user_id}\n")
        try:
            response = self.client.table("documents") \
                .select("*") \
                .filter("metadata->>ass_id", "eq", str(ass_id)) \
                .filter("metadata->>user_id", "eq", str(user_id)) \
                .execute()
            # print(f"supabase content: {[x["content"] for x in response.data]}")
            content = [x["content"] for x in response.data]
            return content
        except Exception as e:
            logger.error(f"Error retrieving document from Supabase: {e}")
            raise

    def save_chat_history(self, chat_data: dict) -> None:
        """Save chat interaction to Supabase."""
        try:
            self.supabase_client.table('conversations').insert(chat_data).execute()
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            raise

    def get_chat_history(self, ass_id: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve chat history from Supabase."""
        try:
            response = (self.supabase_client
                    .table('conversations')
                    .select('*')
                    .eq('ass_id', ass_id)
                    .eq('user_id', user_id)
                    .order('timestamp', desc=True)
                    .limit(limit)
                    .execute())
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []