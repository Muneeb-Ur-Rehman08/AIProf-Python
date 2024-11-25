from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from typing import Optional, Any
import json
import logging
import uuid
from users.models import Assistant, SupabaseUser
from .utils import ChatModule
from app.utils.assistant_manager import AssistantManager

logger = logging.getLogger(__name__)

def format_response(data: Any = None, error: str = None, status: int = 200) -> JsonResponse:
    """Helper function to format consistent API responses"""
    response = {
        "success": error is None,
        "data": data if data is not None else {},
        "error": error
    }
    return JsonResponse(response, status=status)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process chat queries and save conversations.
    
    Args:
        request: HTTP request object
        ass_id (Optional[str]): Assistant ID to interact with
        
    Request Body:
        {
            "message": str,            # The user's message
            "conversation_id": str,    # Optional - existing conversation ID
        }
        
    Returns:
        JsonResponse containing:
        - success (bool): Whether the request was successful
        - response (str): The assistant's response
        - conversation_id (str): The conversation ID
        - error (Optional[str]): Error message if request failed
    """

    # Initialize assistant
    assistant_manager = AssistantManager()

    try:
        # Parse request body
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt')
            conversation_id = data.get('conversation_id')
            
            if not prompt:
                return format_response(error='Message is required', status=400)
                
        except json.JSONDecodeError:
            return format_response(error='Invalid JSON body', status=400)
            
        # Get user ID from request (adjust based on your auth implementation)
        if not request.user.is_authenticated:
            return format_response(error="User not authenticated", status=400)

        try:
            user = SupabaseUser.objects.get(email=request.user)
            user_id = str(user.id)  # Convert UUID to string
            # uuid.UUID(user_id)  # Validate UUID format
        except (SupabaseUser.DoesNotExist, ValueError):
            return format_response(error="Invalid user authentication", status=400)
        
        # Validate assistant exists
        try:
            assistant = assistant_manager.get_assistant(ass_id=uuid.UUID(ass_id)) 
        except Assistant.DoesNotExist:
            return format_response(error='Assistant not found', status=404)
            
        # Convert conversation_id to UUID if provided
        conv_id = None
        if conversation_id:
            try:
                conv_id = uuid.UUID(conversation_id)
            except ValueError:
                return format_response(error='Invalid conversation ID format', status=400)
            

        assistant_config = {
            "subject": assistant.config.subject,
            "teacher_instructions": assistant.config.teacher_instructions,
            
            "question": prompt,
            # Add any other configuration fields from your Assistant model
        }
        
        # Initialize chat module and assistant
        chat_module = ChatModule()
        
        
        # Process message and get response
        response = chat_module.process_message(
            message=prompt,
            ass_id=assistant.config.ass_id,
            user_id=user_id,
            assistant_config=assistant_config,
            conversation_id=conv_id
        )
        
        # Get the conversation ID (either existing or new one created by process_message)
        latest_conversation = chat_module.get_chat_history(
            ass_id=assistant.config.ass_id,
            user_id=user_id,
            limit=1
        )
        
        current_conversation_id = str(latest_conversation[0]['conversation_id']) if latest_conversation else None
        
        return format_response(data={
            'response': response,
            'conversation_id': current_conversation_id
        })
        
    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return format_response(error='Failed to process chat query', status=500)