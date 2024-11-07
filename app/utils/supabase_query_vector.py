from typing import List, Dict
import numpy as np
from supabase import Client
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from app.configs.supabase_config import SUPABASE_CLIENT

class SupabaseVectorStore:
    def __init__(self, embedding: OpenAIEmbeddings, table_name: str):
        self.embedding = embedding
        self.supabase = SUPABASE_CLIENT
        self.table_name = table_name

    async def similarity_search(self, query: str, k: int, filters: Dict[str, str] = None) -> List[Document]:
        try:
            # Embed the query
            query_vector = np.array(self.embedding.embed_query(query))

            # Construct the Supabase query
            query = self.supabase.rpc("vector_search", {
                "query_vector": query_vector.tolist(),
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