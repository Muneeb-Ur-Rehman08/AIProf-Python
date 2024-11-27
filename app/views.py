from venv import logger
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from app.modals.chat import get_chat_completion
from app.modals.anon_conversation import save_conversation, fetch_conversation_history
from app.utils.conversations import get_user_id
from app.utils.vector_store import store_embedding_vectors_in_supabase, get_answer, is_valid_uuid
import json
import time
import os
import uuid
from app.template_views import index_view   # Import the moved methods
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from app.modals.supabase_auth import login_with_supabase
from django.contrib.auth.decorators import login_required
from app.utils.auth_backend import SupabaseBackend
from app.utils.assistant_manager import AssistantManager
from app.modals.assistants import AssistantConfig

# Ensure the GROQ_API_KEY is loaded from the environment
api_key = os.getenv('GROQ_API_KEY')
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable is not set")

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat_view(request):
    if request.method == "OPTIONS":
        # Respond to the OPTIONS request
        response = JsonResponse({"message": "Options request allowed"})
        response["Allow"] = "POST, OPTIONS"
        return response

    # Handle POST request
    try:
        data = json.loads(request.body.decode('utf-8'))
        content = data.get("content", {})
        prompt = content.get("parts", [None])[0]
        conversation_id = data.get("conversation_id")
        parent_message_id = data.get("parent_message_id")
        role = content.get("role", "user")
        # Fix the timestamp format string
        created_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        updated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        user_id = get_user_id(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not prompt:
        return JsonResponse({"error": "prompt is required"}, status=400)
    conversation_history = fetch_conversation_history(user_id)

    def stream_response():
        response_chunks = []  # Define response_chunks outside the try block

        try:
            chat_completion = get_chat_completion(conversation_history, prompt)
                
            for chunk in chat_completion:
                response_chunks.append(chunk)
                yield chunk
        except RuntimeError as e:
            yield f"Error: {str(e)}"
        finally:
            # Save the complete response after streaming
            complete_response = ''.join(response_chunks)
            content_assistant = {
                "id": str(uuid.uuid4()),
                "role": 'assistant',
                "parts": [
                    complete_response
                ],
                "content_type": "text",
                "created_time": created_at
            }
            save_conversation(content, conversation_id, parent_message_id, role, created_at, updated_at, user_id)
            save_conversation(content_assistant, conversation_id, parent_message_id, 'assistant', created_at, updated_at, user_id)

    return StreamingHttpResponse(stream_response(), content_type='text/plain')


@csrf_exempt
@require_http_methods(["POST"])
def upload_doc(request):
    if request.method == 'POST':
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']

            # Define a temporary directory within your project
            temp_dir = os.path.join('temp')
            os.makedirs(temp_dir, exist_ok=True)  # Create the directory if it doesn't exist

            # Save the uploaded file temporarily
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, 'wb+') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)

            # Pass the path of the temporary file to `store_embedding_vectors_in_supabase`
            result = store_embedding_vectors_in_supabase(temp_file_path)

            # Clean up the temporary file after processing
            os.remove(temp_file_path)

            return JsonResponse({'message': 'File uploaded successfully', 'result': result})
        else:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def get_rag_answer(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        question = data.get("question")
        doc_id = data.get("doc_id")

        if not question:
            return JsonResponse({'error': 'question is required'}, status=400)
        if not doc_id:
            return JsonResponse({'error': 'doc_id is required'}, status=400)
        # check if doc_id is valid uuid 
        if not is_valid_uuid(doc_id):
            return JsonResponse({'error': 'doc_id is not a valid uuid'}, status=400)
        
        answer = get_answer(question, doc_id)

        return JsonResponse({'answer': answer}, status=200)
    
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def custom_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        user = authenticate(request, username=email, password=password, name=name)
        if user:
            login(request, user)
            return redirect('index')
        else:
            return JsonResponse({'error': 'Authentication failed'}, status=400)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

# logout view
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    # Create an instance of SupabaseBackend
    backend = SupabaseBackend()
    # Call the logout method with the request
    return backend.logout(request)


# create assistant view
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_assistant(request):
    if request.method == 'POST':
        data = request.POST
        assistant_name = data.get("assistant_name")
        subject = data.get("subject")
        teacher_instructions = data.get("teacher_instructions")
        knowledge_base = []
        if 'knowledge_base' in data:
            uploaded_files = data.get("knowledge_base")
            for file in uploaded_files:
                temp_dir = os.path.join('temp')
                os.makedirs(temp_dir, exist_ok=True)  # Create the directory if it doesn't exist

                # Save the uploaded file temporarily
                temp_file_path = os.path.join(temp_dir, file.name)
                with open(temp_file_path, 'wb+') as temp_file:
                    for chunk in file.chunks():
                        temp_file.write(chunk)
                knowledge_base.append(temp_file_path)

        assistant_manager = AssistantManager()

        print(f"knowledge_base: {knowledge_base}, assistant_name: {assistant_name}, subject: {subject}, teacher_instructions: {teacher_instructions}, user_id: {request.user.id}")

        config = AssistantConfig(
            user_id=request.user.id,
            assistant_name=assistant_name,
            subject=subject,
            teacher_instructions=teacher_instructions,
            knowledge_base=knowledge_base
        )
        assistant_manager.create_assistant(config)

        return JsonResponse({'message': 'Assistant created successfully'}, status=200)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


# @login_required
@csrf_exempt
@require_http_methods(["GET"])
def list_assistants(request):
    return render(request, 'assistant/list.html')


# @login_required
@csrf_exempt
@require_http_methods(["GET"])
def list_assistant_partial(request):
    keyword = request.GET.get('keyword')
    # Initialize assistant manager
    assistants = AssistantManager().list_assistants()
    assistants_data = [assistant.config.__dict__ for assistant in assistants]
    if keyword and len(keyword) > 2:
        assistants_data = [assistant for assistant in assistants_data if keyword in assistant['assistant_name']]
    logger.info(f"Get all assistants: {assistants_data}")
    return render(request, 'assistant/list_partials.html', {"assistants": assistants_data})
