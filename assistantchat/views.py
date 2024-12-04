from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, StreamingHttpResponse
from typing import Optional, Any, Dict
import json
import logging
import uuid
from users.models import Assistant, SupabaseUser, AssistantRating
from .models import Conversation
from .utils import ChatModule
from app.utils.assistant_manager import AssistantManager
from django.contrib.auth.models import User
from decimal import Decimal
from django.db.models import Q


logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process chat queries and save conversations.
    """
    def generate_response():
        try:
            assistant_manager = AssistantManager()
            
            # Parse request body
            try:
                data = json.loads(request.body)
                prompt = data.get('message')
                assistant_id = data.get('id')  
                print(f"assistant id in chat: {assistant_id}")          
                if not prompt:
                    yield json.dumps({"success": False, "error": "Prompt is required", "status": 400})
                    return
                    
            except json.JSONDecodeError:
                yield json.dumps({"success": False, "error": "Invalid JSON body", "status": 400})
                return
                
            # User authentication check
            if not request.user.is_authenticated:
                yield json.dumps({"success": False, "error": "User not authenticated", "status": 400})
                return

            try:
                user = User.objects.get(id=request.user.id)
                user_id = str(user.id)
                print(f"user id from chat: {user_id}")
            except (SupabaseUser.DoesNotExist, ValueError):
                yield json.dumps({"success": False, "error": "Invalid user authentication", "status": 400})
                return
            
            # Assistant validation
            if not assistant_id:
                yield json.dumps({"success": False, "error": "Assistant ID is required", "status": 400})
                return
                
            try:
                assistant = Assistant.objects.get(id=assistant_id)
                print(f"assistant get for chat: {assistant.id}")
            except (ValueError, TypeError):
                yield json.dumps({"success": False, "error": "Invalid assistant ID format", "status": 400})
                return
            except Assistant.DoesNotExist:
                yield json.dumps({"success": False, "error": "Assistant not found", "status": 404})
                return
            
            assistant_config = {
                "subject": assistant.subject,
                "topic": assistant.topic,
                "teacher_instructions": assistant.teacher_instructions,
                "prompt": prompt,
            }
            print(f"assistant_chat_config: {assistant_config}")

            # Initialize chat module and process message
            chat_module = ChatModule()
            response = chat_module.process_message(
                prompt=prompt,
                assistant_id=assistant.id,
                user_id=user_id,
                assistant_config=assistant_config,
            )
            
            # Collect and yield responses
            for chunk in response:
                if chunk:
                    yield chunk
            
        except Exception as e:
            logger.error(f"Error in chat query endpoint: {e}")
            yield json.dumps({"success": False, "error": "Failed to process chat query", "status": 500})

    # Return a StreamingHttpResponse with the generator
    return StreamingHttpResponse(
        generate_response(), 
        content_type='application/json'
    )