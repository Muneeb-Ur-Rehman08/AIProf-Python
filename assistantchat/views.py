from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, StreamingHttpResponse
from typing import Optional, Any, Dict
import json
import logging
import uuid
from users.models import Assistant, SupabaseUser
from .utils import ChatModule
from app.utils.assistant_manager import AssistantManager

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process chat queries and save conversations.
    """
    def format_response_dict(data: Any = None, error: str = None, status: int = 200) -> Dict:
        """Helper function to format consistent API responses as a dictionary"""
        return {
            "success": error is None,
            "data": data if data is not None else {},
            "error": error,
            "status": status
        }

    def generate_response():
        assistant_data = request.session.get("assistant")  
        try:
            assistant_manager = AssistantManager()
            
            # Parse request body
            try:
                data = json.loads(request.body)
                prompt = data.get('prompt')
                
                conversation_id = data.get('conversation_id')
                ass_id = assistant_data["ass_id"]  
                print(f"assistant id in chat: {ass_id}")          
                if not prompt:
                    yield json.dumps(format_response_dict(error='Prompt is required', status=400))
                    return
                    
            except json.JSONDecodeError:
                yield json.dumps(format_response_dict(error='Invalid JSON body', status=400))
                return
                
            # User authentication check
            if not request.user.is_authenticated:
                yield json.dumps(format_response_dict(error="User not authenticated", status=400))
                return

            try:
                user = SupabaseUser.objects.get(email=request.user)
                user_id = str(user.id)
                print(f"user id from chat: {user_id}")
            except (SupabaseUser.DoesNotExist, ValueError):
                yield json.dumps(format_response_dict(error="Invalid user authentication", status=400))
                return
            
            # Assistant validation
            if not assistant_data["ass_id"]:
                yield json.dumps(format_response_dict(error='Assistant ID is required', status=400))
                return
                
            try:
                assistant_uuid = uuid.UUID(str(assistant_data["ass_id"]))
                assistant = assistant_manager.get_assistant(ass_id=assistant_uuid)
                print(f"assistant get for chat: {assistant.config.ass_id}")
            except (ValueError, TypeError):
                yield json.dumps(format_response_dict(error='Invalid assistant ID format', status=400))
                return
            except Assistant.DoesNotExist:
                yield json.dumps(format_response_dict(error='Assistant not found', status=404))
                return
                
            # Conversation ID handling
            conv_id = None
            if conversation_id:
                try:
                    conv_id = uuid.UUID(conversation_id)
                except ValueError:
                    yield json.dumps(format_response_dict(error='Invalid conversation ID format', status=400))
                    return
            else:
                conv_id = uuid.uuid4()
             
            assistant_config = {
                "subject": assistant.config.subject,
                "teacher_instructions": assistant.config.teacher_instructions,
                "prompt": prompt,
            }
            print(f"assistant_chat_config: {assistant_config}")
            
            # Initialize chat module and assistant
            chat_module = ChatModule()
            
            # Process message and get response
            response = chat_module.process_message(
                prompt=prompt,
                ass_id=assistant,
                user_id=user_id,
                assistant_config=assistant_config,
                conversation_id=conv_id
            )
            
            # Collect and yield responses
            full_response = ""
            for chunk in response:
                content = chunk
                if content:
                    yield content
            
        except Exception as e:
            logger.error(f"Error in chat query endpoint: {e}")
            yield json.dumps(format_response_dict(error='Failed to process chat query', status=500))

    # Return a StreamingHttpResponse with the generator
    return StreamingHttpResponse(
        generate_response(), 
        content_type='application/json'
    )