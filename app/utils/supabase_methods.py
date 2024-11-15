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

def get_session():
    return SUPABASE_CLIENT.auth.get_session()

def set_session(access_token, refresh_token):
    SUPABASE_CLIENT.auth.set_session(access_token,refresh_token)

supabase_methods = {
    "fetch": fetch,
    "insert": insert,
    "get_vector_store": get_vector_store,
    "get_session": get_session,
    "set_session": set_session
}
