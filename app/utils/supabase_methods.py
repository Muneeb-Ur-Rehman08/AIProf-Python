from app.configs.supabase_config import SUPABASE_CLIENT
def fetch(table, query):
    if isinstance(query, dict) and query:
        column, value = list(query.items())[0]
        if column and value:
            response = SUPABASE_CLIENT.table(table).select("*").eq(column, value).execute()
    else:
        response = SUPABASE_CLIENT.table(table).select("*").execute()

    
    return response

def insert(table, data):
    response = SUPABASE_CLIENT.table(table).insert(data).execute()
    return response

def get_vector_store(embeddings):
    return SUPABASE_CLIENT.table("teacher").select("*").execute()

supabase_methods = {
    "fetch": fetch,
    "insert": insert,
    "get_vector_store": get_vector_store
}
