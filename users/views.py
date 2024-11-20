import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
from typing import Dict, Any, Optional
import logging
from django.conf import settings

# Ensure these imports match your project structure
from app.modals.assistants import AssistantConfig
from app.utils.assistant_manager import AssistantManager
from .models import SupabaseUser
# Configure logging
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
@require_http_methods(["GET", "OPTIONS"])
def get_assistant(request, ass_id: Optional[str] = None):
    """
    Endpoint to retrieve specific or all assistants for a user
    - GET /users/assistants/ - List all assistants
    - GET /users/assistants/<ass_id>/ - Get specific assistant
    """

    try:
        
        # Initialize assistant manager
        assistant_manager = AssistantManager()

        if ass_id:
            # Get specific assistant
            try:
                uuid_ass_id = uuid.UUID(ass_id)  # Validate UUID format
            except ValueError:
                return format_response(error="Invalid assistant ID format", status=400)

            assistant = assistant_manager.get_assistant(uuid_ass_id)
            if not assistant:
                return format_response(error="Assistant not found", status=404)
            
            # Return single assistant data
            return format_response(data=assistant.config.__dict__)
        else:
            # List all assistants
            assistants = assistant_manager.list_assistants()
            logger.info(f"Get all assistants: {assistants}")
            assistants_data = [assistant.config.__dict__ for assistant in assistants]
            return format_response(data=assistants_data)

    except Exception as e:
        logger.error(f"Error retrieving assistant(s): {str(e)}")
        return format_response(error="Internal server error", status=500)

@csrf_exempt
@require_http_methods(["POST", "PUT", "GET", "OPTIONS"])
def create_assistant(request):
    """
    Flexible endpoint for managing assistants.
    
    Endpoint: assistants/manage/
    Methods:
        - POST: Create new assistant
        - PUT: Update existing assistant
        - GET: Retrieve assistant data
        - OPTIONS: Get allowed methods
    """
    # Handle OPTIONS request
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "POST, PUT, GET, OPTIONS"
        return response

    try:
        # Extract request data
        data = request.POST.dict() if request.method in ["POST", "PUT"] else request.GET
        logger.info(f"Received data: {data}")

        # Validate user and get user_id
        if not request.user.is_authenticated:
            return format_response(error="User not authenticated", status=400)

        try:
            user = SupabaseUser.objects.get(email=request.user)
            user_id = str(user.id)  # Convert UUID to string
            # uuid.UUID(user_id)  # Validate UUID format
        except (SupabaseUser.DoesNotExist, ValueError):
            return format_response(error="Invalid user authentication", status=400)

        logger.info(f"Processing request for user_id: {user_id}")

        # Prepare assistant data
        assistant_data = {
            "user_id": user_id,  # Using string version of UUID
            "assistant_name": data.get('assistant_name'),
            "subject": data.get('subject'),
            "teacher_instructions": data.get('teacher_instructions'),
        }

        

        # Handle file uploads if present
        if files := request.FILES.getlist('knowledge_base'):
            temp_dir = os.path.join('temp')
            os.makedirs(temp_dir, exist_ok=True)
            file_paths = []
            
            for file in files:
                temp_file_path = os.path.join(temp_dir, file.name)
                with open(temp_file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                file_paths.append(temp_file_path)
            
            assistant_data["knowledge_base"] = file_paths
            
        print(f"Assistant Data: {assistant_data}")
        # Initialize assistant manager
        assistant_manager = AssistantManager()

        try:
            # Handle update or creation based on ass_id presence
            if ass_id := data.get('ass_id'):
                try:
                    # Convert ass_id to string if it's a UUID
                    assistant_data["ass_id"] = str(uuid.UUID(ass_id))
                except ValueError:
                    return format_response(error="Invalid ass_id format", status=400)

                # Update existing assistant
                result = assistant_manager.update_assistant(assistant_data)
                
                if not result:
                    return format_response(error="Assistant not found", status=404)
                
                success_message = "Assistant updated successfully"
                
            else:
                # Create new assistant
                config = AssistantConfig(
                    user_id=user_id,
                    assistant_name=assistant_data['assistant_name'],
                    subject=assistant_data['subject'],
                    teacher_instructions=assistant_data['teacher_instructions'],
                    knowledge_base=assistant_data['knowledge_base']
                )
                result = assistant_manager.create_assistant(config)
                success_message = "Assistant created successfully"

            # Prepare response data based on the result structure
            response_data = {
                "ass_id": str(result.config.ass_id),
                "user_id": str(result.config.user_id),
                "assistant_name": result.config.assistant_name,
                "subject": result.config.subject,
                "teacher_instructions": result.config.teacher_instructions,
                "message": success_message
            }
            

            return format_response(data=response_data)

        except AttributeError as e:
            logger.error(f"Error accessing assistant data: {str(e)}")
            return format_response(error="Error processing assistant data", status=500)

    except json.JSONDecodeError:
        return format_response(error="Invalid JSON data", status=400)
    except Exception as e:
        logger.error(f"Error managing assistant: {str(e)}")
        return format_response(error="Internal server error", status=500)



@csrf_exempt
@require_http_methods(["DELETE", "OPTIONS"])
def delete_assistant(request, ass_id):
    """Delete an existing teaching assistant"""
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "DELETE, OPTIONS"
        return response

    try:
        # Get user_id from authenticated user
        if not request.user.is_authenticated:
            return format_response(error="User not authenticated", status=401)

        try:
            user = SupabaseUser.objects.get(email=request.user.email)
            user_id = str(user.id)  # Convert to string to ensure consistency
        except SupabaseUser.DoesNotExist:
            return format_response(error="User not found", status=404)
        
        # Convert IDs to UUID
        try:
            ass_uuid = uuid.UUID(ass_id)
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return format_response(error="Invalid ID format", status=400)

        # Initialize AssistantManager
        assistant_manager = AssistantManager()
        
        # Delete the assistant
        success = assistant_manager.delete_assistant(ass_uuid, user_uuid)
        
        if not success:
            return format_response(error="Assistant not found or deletion failed", status=404)
        
        return format_response(data={"message": "Assistant successfully deleted"})

    except Exception as e:
        logger.error(f"Error deleting assistant: {str(e)}")
        return format_response(error="Internal server error", status=500)