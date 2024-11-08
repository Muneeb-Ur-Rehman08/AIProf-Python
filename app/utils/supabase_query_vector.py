from typing import List, Dict
import numpy as np
from supabase import Client
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from app.configs.supabase_config import SUPABASE_CLIENT
from app.utils.vector_store import vector_store

class SupabaseVectorStore:
    def __init__(self):
        self.vector_store = vector_store
        

    async def similarity_search(self, query: str, k: int, filters: Dict[str, str] = None) -> List[Document]:
        try:
            # Embed the query
            query_vector = np.array(self.vector_store.embeddings.embed_query(query))

            # Construct the Supabase query
            query = self.supabase.rpc("match_documents", {
                "query_vector": query_vector,
                "match_count": k,
                "filters": filters or {}
            })

            # Execute the query and get the results
            results = await query.execute()
            data = results.data

            # Convert the results to a list of Documents
            documents = [
                Document(page_content=doc["content"], metadata=doc["metadata"])
                for doc in data
            ]

            return documents
        except Exception as e:
            print(f"Error performing similarity search: {e}")
            return []