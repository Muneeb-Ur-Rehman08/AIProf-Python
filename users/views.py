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
def get_assistant(request, ass_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    Endpoint to retrieve specific or all assistants for a user
    - GET /users/assistants/ - List all assistants
    - GET /users/assistants/<ass_id>/ - Get specific assistant
    """

    print(ass_id, user_id)
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    try:
        # Extract user_id from query parameters
        # user_id = request.GET.get('user_id')
        if user_id:
            # return format_response(error="Missing required parameter: user_id", status=400)

            try:
                user_uuid = uuid.UUID(user_id)
            except ValueError:
                return format_response(error="Invalid user_id format", status=400)

        # Initialize AssistantManager
        assistant_manager = AssistantManager()

        # ass_id = request.GET.get("ass_id")
        if ass_id and user_uuid:
            # Get specific assistant
            try:
                ass_uuid = uuid.UUID(ass_id)
            except ValueError:
                return format_response(error="Invalid ass_id format", status=400)

            assistant = assistant_manager.get_assistant(ass_id=ass_uuid, user_id=user_uuid)
            if not assistant:
                return format_response(error="Assistant not found", status=404)

            response_data = {
                "ass_id": str(assistant.config.ass_id),
                "user_id": str(assistant.config.user_id),
                "assistant_name": assistant.config.assistant_name,
                "subject": assistant.config.subject,
                "teacher_instructions": assistant.config.teacher_instructions,
                "knowledge_base": assistant.config.knowledge_base
            }
            print(response_data)
            return format_response(data=response_data)
        else:
            # List all assistants for the user
            assistants = assistant_manager.list_assistants()
            response_data = {
                "assistants": [
                    {
                        "ass_id": str(assistant.config.ass_id),
                        "assistant_name": assistant.config.assistant_name,
                        "subject": assistant.config.subject,
                        "teacher_instructions": assistant.config.teacher_instructions,
                        "knowledge_base": assistant.config.knowledge_base
                    }
                    for assistant in assistants
                ]
            }

            return format_response(data=response_data)

    except Exception as e:
        logger.error(f"Error retrieving assistant(s): {str(e)}")
        return format_response(error="Internal server error", status=500)

@csrf_exempt
@require_http_methods(["POST", "PUT", "GET", "OPTIONS"])
def manage_assistant(request):
    """
    Flexible endpoint for creating or updating assistants
    assistants/manage/
    Supports: POST (create), PUT (update), GET (create/update)
    """
    logger.info(f"Received {request.method} request at /users/assistants/manage/")
    
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "POST, PUT, GET, OPTIONS"
        return response

    try:
        # Parse input data based on request method
        if request.method in ["POST", "PUT", "GET"]:
            # Support both JSON body and GET parameters
            if request.body:
                try:
                    data = json.loads(request.body.decode('utf-8'))
                except json.JSONDecodeError:
                    data = {}
            else:
                data = request.GET.dict()

            # Convert knowledge_base to list if it's a string
            if 'knowledge_base' in data and isinstance(data['knowledge_base'], str):
                data['knowledge_base'] = [
                    kb.strip() for kb in 
                    data['knowledge_base'].strip('[]').split(',') 
                    if kb.strip()
                ]

            # Validate required fields
            required_fields = ["user_id", "assistant_name", "subject", "teacher_instructions"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return format_response(
                    error=f"Missing required fields: {', '.join(missing_fields)}", 
                    status=400
                )

            # Convert user_id to UUID
            try:
                user_id = uuid.UUID(data["user_id"])
            except ValueError:
                return format_response(error="Invalid user_id format", status=400)

            # Initialize AssistantManager
            assistant_manager = AssistantManager()
            
            # Check if updating existing assistant
            if data.get("ass_id") or request.method in ["PUT", "GET"]:
                try:
                    # Convert ass_id to UUID
                    ass_uuid = uuid.UUID(data.get('ass_id', ''))
                    
                    # Try to update existing assistant
                    updated_assistant = assistant_manager.update_assistant(ass_uuid, user_id, data)
                    if not updated_assistant:
                        return format_response(error="Assistant not found or update failed", status=404)
                    
                    response_data = {
                        "ass_id": str(updated_assistant.config.ass_id),
                        "user_id": str(updated_assistant.config.user_id),
                        "assistant_name": updated_assistant.config.assistant_name,
                        "subject": updated_assistant.config.subject,
                        "teacher_instructions": updated_assistant.config.teacher_instructions,
                        "knowledge_base": updated_assistant.config.knowledge_base,
                        "message": "Assistant updated successfully"
                    }
                    return format_response(data=response_data)
                    
                except ValueError:
                    return format_response(error="Invalid ass_id format", status=400)
                
            else:
                # Create new assistant
                config = AssistantConfig(
                    user_id=user_id,
                    assistant_name=data["assistant_name"],
                    subject=data["subject"],
                    teacher_instructions=data["teacher_instructions"],
                    knowledge_base=data.get("knowledge_base", [])
                )
                
                new_assistant = assistant_manager.create_assistant(config)
                
                response_data = {
                    "ass_id": str(new_assistant.config.ass_id),
                    "user_id": str(new_assistant.config.user_id),
                    "assistant_name": new_assistant.config.assistant_name,
                    "subject": new_assistant.config.subject,
                    "teacher_instructions": new_assistant.config.teacher_instructions,
                    "knowledge_base": new_assistant.config.knowledge_base,
                    "message": "Assistant created successfully"
                }

                return format_response(data=response_data)

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
        # Extract user_id from query parameters
        user_id = request.GET.get('user_id')
        if user_id:
            return format_response(error="Missing required parameter: user_id", status=400)
        
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

