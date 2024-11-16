from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from app.modals.supabase_auth import login_with_supabase

class SupabaseBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        response = login_with_supabase(email, password)
        if "error" in response:
            return None

        # Check if user exists in Django, else create a new one
        user_data = response.get('user', {})
        user, created = User.objects.get_or_create(username=user_data['email'], email=user_data['email'])
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
