import os
import time
from app.configs.supabase_config import SUPABASE_CLIENT
from app.utils.supabase_methods import supabase_methods
import sys

def save_conversation(content, conversation_id, parent_message_id, role, created_at, updated_at, user_id):
    SUPABASE_CLIENT.table("anon_conversations").insert({
        "user_id": user_id,
        "content": content,
        "conversation_id": conversation_id,
        "parent_message_id": parent_message_id or "",
        "role": role,
        "created_at": created_at,
        "updated_at": updated_at
    }).execute()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def fetch_conversation_history(user_id):  # Renamed function
    response = supabase_methods["fetch"]("anon_conversations", {"user_id": user_id})
    re_arranged_data = []

    for data in response.data:
        # Ensure content is a string
        text_content = str(data['content']['parts'][0]) if data['content']['parts'][0] is not None else ""
        re_arranged_data.append({
            "role": data['role'],
            "content": text_content
        })
    return re_arranged_data