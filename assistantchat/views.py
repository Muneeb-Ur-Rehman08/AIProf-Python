from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse
from typing import Optional, Dict
import json
import logging
import uuid

from users.models import Assistant, SupabaseUser
from .utils import ChatModule
from app.utils.assistant_manager import AssistantManager

logger = logging.getLogger(__name__)

def format_response(
    data: Optional[Dict] = None, 
    error: Optional[str] = None, 
    status: int = 200
) -> Dict:
    """
    Standardize API response formatting.
    
    :param data: Response payload
    :param error: Error message
    :param status: HTTP status code
    :return: Formatted response dictionary
    """
    return {
        "success": error is None,
        "data": data or {},
        "error": error,
        "status": status
    }

@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process streaming chat queries with robust error handling.
    
    :param request: HTTP request object
    :param ass_id: Optional assistant identifier
    :return: Streaming HTTP response
    """
    def generate_response():
        try:
            # Extract assistant data from session
            assistant_data = request.session.get("assistant", {})
            
            # Parse request body
            try:
                data = json.loads(request.body)
                prompt = data.get('prompt')
                conversation_id = data.get('conversation_id')
                ass_id = assistant_data.get("ass_id")
                
                if not prompt:
                    yield json.dumps(format_response(error='Prompt is required', status=400))
                    return
                    
            except json.JSONDecodeError:
                yield json.dumps(format_response(error='Invalid JSON body', status=400))
                return
                
            # Authentication checks
            if not request.user.is_authenticated:
                yield json.dumps(format_response(error="User not authenticated", status=401))
                return

            try:
                user = SupabaseUser.objects.get(email=request.user)
                user_id = str(user.id)
            except (SupabaseUser.DoesNotExist, ValueError):
                yield json.dumps(format_response(error="Invalid user authentication", status=401))
                return
            
            # Validate assistant
            if not ass_id:
                yield json.dumps(format_response(error='Assistant ID is required', status=400))
                return
                
            try:
                assistant_uuid = uuid.UUID(str(ass_id))
                assistant_manager = AssistantManager()
                assistant = assistant_manager.get_assistant(ass_id=assistant_uuid)
            except (ValueError, TypeError):
                yield json.dumps(format_response(error='Invalid assistant ID format', status=400))
                return
            except Assistant.DoesNotExist:
                yield json.dumps(format_response(error='Assistant not found', status=404))
                return
                
            # Generate conversation ID
            conv_id = uuid.UUID(conversation_id) if conversation_id else uuid.uuid4()
             
            # Prepare assistant configuration
            assistant_config = {
                "subject": assistant.config.subject,
                "teacher_instructions": assistant.config.teacher_instructions,
                "prompt": prompt,
            }
            
            # Process message
            chat_module = ChatModule()
            response_generator = chat_module.process_message(
                prompt=prompt,
                ass_id=assistant,
                user_id=user_id,
                assistant_config=assistant_config,
                conversation_id=conv_id
            )
            
            # Stream response
            for chunk in response_generator:
                yield chunk
        
        except Exception as e:
            logger.error(f"Unexpected error in chat query: {e}")
            yield json.dumps(format_response(error='Server error', status=500))

    # Return streaming response
    return StreamingHttpResponse(
        generate_response(), 
        content_type='text/event-stream'
    )