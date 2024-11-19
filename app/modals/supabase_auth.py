from supabase import create_client
from django.contrib.auth.models import User
from app.configs.supabase_config import SUPABASE_CLIENT

def login_with_supabase(email, password):
    if not email or not password:
        raise ValueError("Email and password are required")
    
    try:
        user = SUPABASE_CLIENT.auth.sign_in_with_password({"email": email, "password": password})
        print(f"user: {user}")
                
        return user
    except Exception as e:
        print(f"Authentication failed: {e}")
        if e.message:
            raise ValueError(f"{e.message}")
        else:
            raise ValueError(f"{e or 'some thing went wrong please try again or contact support'}")

def register_with_supabase(email, password, name):
    try:
        response = SUPABASE_CLIENT.auth.sign_up( {"email": email, "password": password, "options": {
            "data": {
                "first_name": name
            },
        }})
        return response
    except Exception as e:
        return {"error": str(e)}


def logout_with_supabase():
    try:
        # Check if sign_out requires any parameters like a session token
        response = SUPABASE_CLIENT.auth.sign_out({"scope": "global"})
        if response:
            print(f"Logout successful: {response}")
            return response
        else:
            print(f"Logout failed: No response from Supabase, {response}")
            return {"error": "No response from Supabase"}
    except Exception as e:
        print(f"Logout failed: {e}")
        return {"error": str(e)}

