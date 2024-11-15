from app.configs.supabase_config import SUPABASE_CLIENT

def create_user(name, email, password):
    if not name or not email or not password:
        raise ValueError("Name, email and password are required")
    
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")
    
    response = SUPABASE_CLIENT.auth.sign_up(
        {"email": email, "password": password, "options": {
            "data": {
                "first_name": name
            },
            "email_confirm": True,
            "email_redirect_to": "http://localhost:8000/create_assistant/"
        }}
    )
    print(f"response: {response}")
    return response
    
    # user = SUPABASE_CLIENT.auth.sign_up(username, password)
    # return user

def sign_in(email, password):
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


def continue_with_social(provider):
    print(f"provider: {provider}")
    response = SUPABASE_CLIENT.auth.sign_in_with_oauth({
        "provider": provider,
    })
    print(f"response: {response}")
    return response
