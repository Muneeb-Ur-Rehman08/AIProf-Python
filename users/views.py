import os
from django.http import JsonResponse, HttpResponseRedirect
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
from django_htmx.http import HttpResponseClientRedirect
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

# Ensure these imports match your project structure
from .models import SupabaseUser, Assistant, PDFDocument, AssistantRating
from django.template.loader import TemplateDoesNotExist
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .add import populate_subjects_and_topics



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

@login_required(login_url='accounts/login/')
@csrf_exempt
@require_http_methods(["POST", "PUT", "GET", "OPTIONS"])
def create_assistant(request, ass_id: Optional[str] = None):
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
    
    if request.method == "GET":
        data = request.GET.dict()

        assistant_data = Assistant.objects.get(id=ass_id)
        documents = PDFDocument.objects.filter(assistant_id=ass_id)

        urls = [document.title for document in documents if document.metadata.get('document_type') == 'url']
        pdfs = [document.title for document in documents if document.metadata.get('document_type') == 'pdf']
        is_creator = request.user.id == assistant_data.user_id.id
        
        if is_creator:
            return render(request, 'assistant_form.html', {
                'assistant': assistant_data,
                'subject': assistant_data.subject,
                'topic': assistant_data.topic,
                'teacher_instructions': assistant_data.teacher_instructions,
                'urls': urls,
                'knowledge_base': pdfs
            })
        else:
            return HttpResponseRedirect(f'/assistants')

    try:
        # Extract request data flexibly
        data = request.POST.dict() if request.method in ["POST", "PUT"] else request.GET
        logger.info(f"Received data: {data}")

        # Authentication check
        if not request.user.is_authenticated:
            return format_response(error="Authentication required", status=401)

        try:
            user = User.objects.get(id=request.user.id)
        except User.DoesNotExist:
            return format_response(error="Invalid user", status=400)

        # Retrieve or create assistant
        assistant_id = data.get("assistant_id")

        if not data.get('assistant_id') or assistant_id == "":

            print("No assistant id")
            
            try:
                assistant = Assistant.objects.create(
                    user_id=user,
                    is_published=False
                )
                response_data = {
                    'id': str(assistant.id),
                    'message': 'Initial assistant profile created'
                }
                request.session['assistant'] = response_data
                print("After Session: ", request.session.get("assistant"))
                # now redirect to the assistant form page
                
                return create_assistant_view(request, str(assistant.id))
                

            except Exception as e:
                logger.error(f"Assistant creation error: {e}")
                return format_response(error=f"Creation failed: {str(e)}", status=500)
        
        # Existing assistant workflow
        try:
            assistant = Assistant.objects.get(id=assistant_id, user_id=user)
        except Assistant.DoesNotExist:
            return format_response(error="Assistant not found", status=404)

        # Field mapping for updating
        field_mapping = {
            'assistant_name': 'name',
            'subject': 'subject',
            'description': 'description',
            'topic': 'topic',
            'teacher_instructions': 'teacher_instructions',
            'url': 'url'
        }

        changes_made = False

        # Update fields dynamically
        for request_field, model_field in field_mapping.items():
            if request_field in data:
                current_value = getattr(assistant, model_field, '')
                new_value = data.get(request_field, '').strip()

                if new_value and new_value != current_value:
                    # Special validation for URL field
                    if model_field == 'url':
                        try:
                            URLValidator()(new_value)
                        except ValidationError:
                            return format_response(error="Invalid URL format", status=400)
                    setattr(assistant, model_field, new_value)
                    changes_made = True

        # Explicitly set is_published only when save button is clicked
        if data.get('save_button_clicked') == 'true':
            assistant.is_published = True
            changes_made = True


        # Track if a document was uploaded
        document_uploaded = False
        # Handle file uploads
        if files := request.FILES.getlist('knowledge_base'):
            for file in files:
                try:
                    pdf_document = PDFDocument.objects.create(
                        user_id=user,
                        assistant_id=assistant,
                        file=file,
                        title=file.name
                    )
                    
                    # Asynchronous PDF processing recommended
                    pdf_document.process_pdf()
                    document_uploaded = True
                    changes_made = True
                
                except Exception as e:
                    logger.error(f"PDF processing error for {file.name}: {e}")

        url_list = []
        # Handle URL input
        url = data.get('url')
        if url:
            try:
                # Additional URL validation
                # URLValidator()(url)
                url_list.append(url)
                
                # Create PDFDocument with URL
                url_document = PDFDocument.objects.create(
                    user_id=user,
                    assistant_id=assistant,
                    urls=url_list,
                    title=url  # Use URL as title
                )
                
                # Process the URL document
                url_document.process_pdf()
                document_uploaded = True
                changes_made = True
            
            except ValidationError:
                return format_response(error="Invalid URL format", status=400)
            except Exception as e:
                logger.error(f"URL processing error for {url}: {e}")

        # Save changes if detected
        if changes_made:
            try:
                assistant.save()
                response_data = {
                    "ass_id": str(assistant.id),
                    "assistant_name": assistant.name,
                    "subject": assistant.subject,
                    "description": assistant.description,
                    "topic": assistant.topic,
                    "teacher_instructions": assistant.teacher_instructions,
                    "is_published": assistant.is_published,
                    "message": "Assistant updated successfully"
                }
                return format_response(data=response_data)
            
            except Exception as e:
                logger.error(f"Save error: {e}")
                return format_response(error="Update failed", status=500)
        
        # No changes scenario
        return format_response(data={
            "ass_id": str(assistant.id),
            "message": "No changes detected"
        })

    except json.JSONDecodeError:
        return format_response(error="Invalid JSON", status=400)
    
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return format_response(error="Server error", status=500)



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
    


@login_required(login_url='accounts/login/')
def create_assistant_view(request, ass_id):
    try:
        assistant = request.session.get('assistant', None)
        assistant_id = ass_id or assistant.get('id')

        if not assistant_id:
            return redirect('index')
        
        return HttpResponseClientRedirect(f'/assistant/{str(assistant_id)}/')
    except TemplateDoesNotExist:
        return format_response(error="Template not found", status=404)