from supabase import create_client
from django.contrib.auth.models import User
from app.configs.supabase_config import SUPABASE_CLIENT

def login_with_supabase(email, password):
    try:
        response = SUPABASE_CLIENT.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        return response
    except Exception as e:
        return {"error": str(e)}

def register_with_supabase(email, password):
    try:
        response = SUPABASE_CLIENT.auth.sign_up({
            "email": email,
            "password": password,
        })
        return response
    except Exception as e:
        return {"error": str(e)}
