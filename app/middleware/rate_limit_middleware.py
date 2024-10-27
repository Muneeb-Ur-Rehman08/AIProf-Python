import time
from django.http import JsonResponse
from app.modals.anon_conversation import fetch_conversation_history

# Rate limit configuration
REQUEST_LIMIT = 10

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply rate limiting to the /api/chat route
        if request.path == '/api/chat/':
            user_id = self.get_user_identifier(request)

            # Fetch user request history from Supabase
            conversation_history = fetch_conversation_history(user_id)

            user_requests = []
            for entry in conversation_history:
                if entry['role'] == 'user':
                    user_requests.append(entry)

            # Check if user has exceeded the request limit
            if len(user_requests) >= REQUEST_LIMIT:
                error_message = "`Request limit exceeded`"
                return JsonResponse({"error": error_message}, status=429)

        response = self.get_response(request)
        return response

    def get_user_identifier(self, request):
        # Use IP address as user identifier
        return request.META.get('REMOTE_ADDR')
    def parse_timestamp(self, timestamp_str):
        # Parse the timestamp string into a Unix timestamp
        return time.mktime(time.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ'))
