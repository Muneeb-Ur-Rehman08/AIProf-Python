import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import uuid
from typing import Dict, Any, Optional
import logging
from django.conf import settings
from django.core.files import File
from django.shortcuts import redirect
from django.contrib.auth.models import User

# Ensure these imports match your project structure
from .models import SupabaseUser, Assistant, PDFDocument


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
        
        if  request.user.is_authenticated:

            if ass_id:
                # Get specific assistant
                try:
                    uuid_ass_id = uuid.UUID(ass_id)  # Validate UUID format
                except ValueError:
                    return format_response(error="Invalid assistant ID format", status=400)

                # assistant = assistant_manager.get_assistant(uuid_ass_id)
                assistant = Assistant.objects.get(id=ass_id)
                if not assistant:
                    return format_response(error="Assistant not found", status=404)
                
                
                assistant_data = {
                    'id': str(assistant.id),
                    'name': assistant.name,
                    'subject': assistant.subject,
                    'user_id': str(assistant.user_id.id),
                    'teacher_instructions': assistant.teacher_instructions
                }
                
                # Return single assistant data
                return format_response(data=assistant_data)
                
            else:
                # List all assistants
                assistants = Assistant.objects.all()  # Fetch all assistants
                logger.info(f"Get all assistants: {assistants}")
                assistants_data = [
                    {
                        'id': str(assistant.id),
                        'name': assistant.name,
                        'subject': assistant.subject,
                        'user_id': str(assistant.user_id.id),
                        'descriotion': assistant.description,
                        'topic': assistant.topic
                    } for assistant in assistants
                ]
                # assistants_data = [assistant.config.__dict__ for assistant in assistants]
                return format_response(data=assistants_data)
        else:
            return format_response(error="User not authenticated", status=400)

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
    logger.info(f"data in request: {request.method}")
    # Handle OPTIONS request
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "POST, PUT, GET, OPTIONS"
        return response

    try:
        
        # Extract request data
        data = request.POST.dict() if request.method in ["POST", "PUT"] else request.GET
        logger.info(f"Received data: {data}")
        logger.info(f"Received data: {request.user}")
        # Validate user and get user_id
        if not request.user.is_authenticated:
            return format_response(error="User not authenticated", status=400)

        try:
            user = User.objects.get(id=request.user.id)
            user_id = str(user.id)  # Convert UUID to string
            
        except (User.DoesNotExist, ValueError):
            return format_response(error="Invalid user authentication", status=400)
        logger.info(f"Processing request for user_id: {user_id}")

        # del request.session["assistant"]

        assistant_id = data.get("assistant_id")

        if not data.get('assistant_id'):
            
            try:
                
                # name = data.get("assistant_name")
                # print(name)
                
                print("Session: ", request.session.get("assistant"))
                # Create assistant to django models
                assistant = Assistant.objects.create(
                    user_id=user,
                    # name=name,
                )
                print(f"Created assistant model: {assistant.id}")

                # Prepare response
                response_data = {
                    'id': str(assistant.id),
                    # 'name': assistant.name,
                    'message': 'Initial assistant profile created. Complete your profile to finish.'
                }
                request.session['assistant'] = response_data
                print("After Session: ", request.session.get("assistant"))
                return redirect(f'/assistant/{str(assistant.id)}')

            except Exception as e:
                return format_response(error=f"Error creating initial assistant: {str(e)}", status=500)
        
        else:
            
            # Prepare assistant data
            # Validate required fields
            required_fields = ['assistant_name', 'subject', 'description', 'topic', 'teacher_instructions']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return format_response(
                    error=f"Missing required fields: {', '.join(missing_fields)}", 
                    status=400
                )
                
            assistant_data = {
                "user_id": user_id,  # Using string version of UUID
                "assistant_name": data.get('assistant_name'),
                "subject": data.get('subject'),
                "description": data.get('description'),
                "topic": data.get('topic'),
                "teacher_instructions": data.get('teacher_instructions'),
            }

            assistant = Assistant.objects.get(id=assistant_id)

            # Handle file uploads if present
            if files := request.FILES.getlist('knowledge_base'):
                for file in files:
                    print(file)
                    try:
                        # Create PDFDocument instance directly
                        pdf_document = PDFDocument.objects.create(
                            user_id=user,
                            assistant_id=assistant,
                            file=file,
                            title=file.name
                        )
                        
                        # Process the PDF (this method will handle temp directory and file processing internally)
                        pdf_document.process_pdf()
                    
                    except Exception as e:
                        logger.error(f"Error processing PDF {file.name}: {str(e)}")
                        # Cleanup if processing fails
                        pdf_document.delete()
                
                # assistant_data["knowledge_base"] = file_paths
                
            print(f"Assistant Data: {assistant_data}")
            
            try:
                
                print("assistant_id", assistant_id)
                # Handle update or creation based on ass_id presence
                if assistant_id:

                    assistant.subject = assistant_data["subject"]
                    assistant.description = assistant_data['description']
                    assistant.topic = assistant_data['topic']
                    assistant.teacher_instructions = assistant_data["teacher_instructions"]
                    assistant.save()

                    success_message = "Assistant updated successfully"
                    
                # # Prepare response data based on the result structure
                    response_data = {
                        "ass_id": str(assistant.id),
                        "user_id": str(assistant.user_id.id),
                        "assistant_name": assistant.name,
                        "subject": assistant.subject,
                        "description": assistant.description,
                        "topic": assistant.topic,
                        "teacher_instructions": assistant.teacher_instructions,
                        "message": success_message
                    }
                    print("assistant id when user created", response_data)
                    request.session['assistant'] = response_data
                    print("Session", request.session.get("assistant"))
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
@require_http_methods(["DELETE", "OPTIONS", "GET"])
def delete_assistant(request, ass_id):
    """Delete an existing teaching assistant"""
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Methods"] = "DELETE, OPTIONS, GET"
        return response

    try:
        # Get user_id from authenticated user
        if not request.user.is_authenticated:
            return format_response(error="User not authenticated", status=401)

        try:
            user = User.objects.get(id=request.user.id)
            user_id = str(user.id)  # Convert to string to ensure consistency
            print(user_id)
        except User.DoesNotExist:
            return format_response(error="User not found", status=404)
        
        
        # Delete the assistant from the model
        assistant = Assistant.objects.get(id=ass_id, user_id=user.id)
        assistant.delete()
        
        if not assistant:
            return format_response(error="Assistant not found or deletion failed", status=404)
        
        return format_response(data={"message": "Assistant successfully deleted"})

    except Exception as e:
        logger.error(f"Error deleting assistant: {str(e)}")
        return format_response(error="Internal server error", status=500)