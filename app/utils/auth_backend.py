from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from app.modals.supabase_auth import login_with_supabase, register_with_supabase, logout_with_supabase
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth import logout as django_logout

class SupabaseBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, name=None, **kwargs):
        if not username or not password:
            return None
        if self.verify_with_supabase(username, password):
            print(f"username: {username} is verified")
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            return user
        else:
            # Attempt to register user
            if not name:
                return None  # Return None if name is not provided
            response = register_with_supabase(username, password, name)
            if "error" in response:
                return None  # Return None if there's an error
            return User.objects.get(username=username)

    def verify_with_supabase(self, username, password):
        response = login_with_supabase(username, password)
        return "error" not in response

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()
    
    def logout(self, request):
        try:
            response = logout_with_supabase()
            # if response and "error" not in response:
            django_logout(request)  # Invalidate the session
            return redirect('index')
            # else:
            #     print("Logout failed: Supabase returned an error or no response")
            #     return JsonResponse({'error': 'Logout failed'}, status=400)
        except Exception as e:
            print(f"Logout failed: Exception occurred - {str(e)}")
            django_logout(request)  # Fallback to local logout
            return redirect('index')