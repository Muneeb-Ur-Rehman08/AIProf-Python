from app.modals.auth import create_user, sign_in as auth_sign_in, continue_with_social
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from app.configs.supabase_config import SUPABASE_CLIENT
from app.utils.supabase_methods import supabase_methods
import json
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def sign_up(request):
    if request.method == "OPTIONS":
        response = JsonResponse({"message": "Options request allowed"})
        response["Allow"] = "POST, OPTIONS"
        return response
    
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if name and email and password:
            create_user(name, email, password)
            return JsonResponse({"message": "User created successfully"}, status=201)
        else:
            return JsonResponse({"message": "Username and password are required"}, status=400)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def sign_in(request):
    if request.method == "OPTIONS":
        response = JsonResponse({"message": "Options request allowed"})
        response["Allow"] = "POST, OPTIONS"
        return response
    
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        if email and password:
            try:
                auth_response = SUPABASE_CLIENT.auth.sign_in_with_password({"email": email, "password": password})
                user = auth_response.user
                if user:
                    print(f"user: {user}")
                    # Assuming the correct attribute is 'session' instead of 'access_token'
                    session = auth_response.session
                    print(f"session: {session}")
                    # store user in session storage
                    # SUPABASE_CLIENT.auth.set_session(session.access_token, session.refresh_token)
                    return redirect('index')
                else:
                    return JsonResponse({"message": "Invalid credentials"}, status=400)
            except Exception as e:
                if "'AuthResponse' object has no attribute 'access_token'" in str(e):
                    return JsonResponse({"message": "Authentication failed: 'AuthResponse' object has no attribute 'access_token'"}, status=400)
                return JsonResponse({"message": f"Authentication failed: {str(e)}"}, status=400)
        else:
            return JsonResponse({"message": "Email and password are required"}, status=400)
        
@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def continue_with_google(request):
    response = continue_with_social('google')
    print(f"response: {response}")
    if response:
        if response.url:
            # remove the code_challenge and code_challenge_method from the url and add the provider and redirect_to=http://localhost:8000/
            url = response.url.split('?')[0] + f"?provider=google&redirect_to=http://localhost:8000/"
            return JsonResponse({"message": "User signed in successfully", "url": url}, status=200)
        else:
            return JsonResponse({"message": "Failed to continue with Google"}, status=400)
    else:
        return JsonResponse({"message": "Failed to continue with Google"}, status=400)
    

@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def sign_out(request):
    # all the session data is deleted
    response = SUPABASE_CLIENT.auth.sign_out({'scope': 'global'})
    print(f"response: {response}")
    return redirect('auth_view') if response else JsonResponse({"message": "Failed to sign out"}, status=400)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def store_session(request):
    if request.method == "OPTIONS":
        response = JsonResponse({"message": "Options request allowed"})
        response["Allow"] = "POST, OPTIONS"
        return response
    
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        print(f"access_token: {access_token}")
        print(f"refresh_token: {refresh_token}")
        session = supabase_methods['set_session'](access_token,refresh_token)
    return JsonResponse({"message": "Session stored"}, status=200)


