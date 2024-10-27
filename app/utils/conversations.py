import os
import json
from app.utils.prompts import get_system_instruction

# In-memory store for tracking user requests and conversations
user_requests = {}
user_conversations = {}

# Rate limit configuration
REQUEST_LIMIT = 10
TIME_WINDOW = 3600  # 1 hour in seconds

def get_user_id(request):
    """Identify the user (using IP address here, but you can use a more robust method)."""
    return request.META.get('REMOTE_ADDR')

def initialize_user(user_id):
    """Initialize user request tracking and conversation history."""
    if user_id not in user_requests:
        user_requests[user_id] = []
        user_conversations[user_id] = []

def update_user_requests(user_id, current_time):
    """Update the user's request timestamps."""
    user_requests[user_id] = [
        timestamp for timestamp in user_requests[user_id]
        if current_time - timestamp < TIME_WINDOW
    ]

def check_request_limit(user_id):
    """Check if the user has exceeded the request limit."""
    return len(user_requests[user_id]) >= REQUEST_LIMIT

def record_request(user_id, current_time):
    """Record a new request for the user."""
    user_requests[user_id].append(current_time)

def save_prompt(user_id, prompt):
    """Save the user's prompt to their conversation history."""
    user_conversations[user_id].append({"role": "user", "content": prompt})

def save_response(user_id, response):
    """Save the assistant's response to the user's conversation history."""
    user_conversations[user_id].append({"role": "assistant", "content": response})

def get_conversation_history(user_id):
    """Retrieve the conversation history for a user."""
    return user_conversations.get(user_id, [])

def clear_conversation(user_id):
    """Clear the conversation history for a user."""
    if user_id in user_conversations:
        del user_conversations[user_id]
