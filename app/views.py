# Standard library imports
import json
import os
import time
import uuid
from decimal import Decimal, InvalidOperation
from typing import Optional
from venv import logger

# Django core imports
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


# Local/project imports
from app.modals.anon_conversation import save_conversation, fetch_conversation_history
from app.modals.assistants import AssistantConfig
from app.modals.chat import get_chat_completion
from app.modals.supabase_auth import login_with_supabase
from app.template_views import index_view
from app.utils.assistant_manager import AssistantManager
from app.utils.auth_backend import SupabaseBackend
from app.utils.conversations import get_user_id
from app.utils.vector_store import (
    store_embedding_vectors_in_supabase, 
    get_answer, 
    is_valid_uuid
)
from assistantchat.models import Conversation
from users.models import Assistant, AssistantRating, Subject, Topic
from users.add import populate_subjects_and_topics

# populate_subjects_and_topics()

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
    # Fetch subjects with topics in a single query using select_related/prefetch_related
    subjects_data = Subject.objects.prefetch_related('topics').all()
    # Fetch Assistants from the database with conversation counts
    assistants = Assistant.objects.all()

    user = request.user
    
    # Apply filters
    filters = Q()
    
    # Keyword search (only if keyword is long enough)
    keyword = request.GET.get('keyword', '').strip()
    if keyword and len(keyword) > 2:
        filters &= Q(name__icontains=keyword) | Q(description__icontains=keyword)
    
    # Subject and Topic filtering
    subjects = request.GET.getlist('subject')
    topics = request.GET.getlist('topic')
    
    if subjects:
        filters &= Q(subject__in=subjects)
    if topics:
        filters &= Q(topic__in=topics)
    
    # Rating filter
    if request.GET.getlist('filter_rating'):
        rating_q = Q()
        for rating in request.GET.getlist('filter_rating'):
            try:
                rating = Decimal(rating)
                rating_q |= Q(
                    average_rating__gte=rating,
                    average_rating__lt=rating + Decimal('1')
                )
            except (ValueError, InvalidOperation):
                continue
        if rating_q:
            filters &= rating_q
    
    # Associated Assistants filter
    if request.GET.get("created_by_me"):
        filters &= Q(user_id=user)

    # Apply all filters at once
    if filters:
        assistants = assistants.filter(filters)
    
    # Sorting Options - Map labels to values
    sorting_options = {
        'newest_first': {
            'label': 'Newest First',
            'value': '-created_at'
        },
        'oldest_first': {
            'label': 'Oldest First',
            'value': 'created_at'
        },
        'highest_interactions': {
            'label': 'Highest Interactions',
            'value': '-interactions'
        },
        'lowest_interactions': {
            'label': 'Lowest Interactions',
            'value': 'interactions'
        },
        'most_reviews': {
            'label': 'Most Reviews',
            'value': '-total_reviews'
        },
        'least_reviews': {
            'label': 'Least Reviews',
            'value': 'total_reviews'
        },
        'name_asc': {
            'label': 'Name (A-Z)',
            'value': 'name'
        },
        'name_desc': {
            'label': 'Name (Z-A)',
            'value': '-name'
        }
    }
    
    # Get sort parameter from request, default to 'Newest First'
    sort_label = request.GET.get('sort', 'Newest First')
    sort_value = next(
        (opt['value'] for opt in sorting_options.values() if opt['label'] == sort_label),
        '-created_at'
    )
    
    # Apply sorting
    assistants = assistants.order_by(sort_value)
    
    # Get rating counts in a single query
    rating_counts = (
        AssistantRating.objects
        .values('rating')
        .annotate(count=Count('id'))
        .order_by('-rating')
    )
    
    # Format rating counts
    formatted_rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for rating in rating_counts:
        if rating['rating'] is not None:
            rating_value = float(rating['rating'])
            if rating_value >= 4.8:
                formatted_rating_counts[5] += rating['count']
            elif 4.0 <= rating_value < 4.8:
                formatted_rating_counts[4] += rating['count']
            elif 3.0 <= rating_value < 4.0:
                formatted_rating_counts[3] += rating['count']
            elif 2.0 <= rating_value < 3.0:
                formatted_rating_counts[2] += rating['count']
            elif 1.0 <= rating_value < 2.0:
                formatted_rating_counts[1] += rating['count']
    
    # Prepare context
    context = {
        "subjects_data": subjects_data,
        "filtered_assistants": [
            {
                "id": str(a.id),
                "name": a.name,
                "subject": a.subject,
                "topic": a.topic,
                "description": a.description,
                "created_at": a.created_at,
                "interactions": a.interactions,
                "average_rating": a.average_rating,
                "total_reviews": a.total_reviews
            }
            for a in assistants
        ],
        "sorting_options": {opt['value']: opt['label'] for opt in sorting_options.values()},
        "current_sort": sort_label,
        "rating_counts": formatted_rating_counts
    }
    
    # Return appropriate template
    if request.htmx:
        return render(request, 'assistant/list_partials.html', {
            'assistants': context["filtered_assistants"],
            'current_sort': sort_label
        })
    
    return render(request, 'assistant/list.html', context)



@csrf_exempt
@require_http_methods(["GET", "POST"])
def assistant_detail(request, assistant_id: Optional[str] = None):
    """
    Handle assistant detail view for both GET and POST requests.
    GET: Returns assistant data as JSON
    POST: Updates rating and returns to the same page
    """
    # Get logged in user id
    user_id = request.user.id
    
    # Get assistant or return 404
    assistant = get_object_or_404(Assistant, id=assistant_id)
    
    if request.method == "GET":
        # Get related data
        interactions = Conversation.objects.filter(assistant_id=assistant_id).count()
        ratings = AssistantRating.objects.filter(assistant=assistant_id)
        is_creator = user_id == assistant.user_id.id
        
        # Return JSON response for GET requests
        return render(request, 'assistant/assistant.html', {
            'assistant': assistant,
            'interactions': interactions,
            'reviews_count': len(ratings),
            'is_creator': is_creator
        })
    
    else:  # POST request
        try:
            # Extract request data
            data = request.POST.dict()
            logger.info(f"Received data: {data}")

            rating = data.get("rating", "")
            review = data.get("review", "")

            # Update or create rating
            AssistantRating.objects.update_or_create(
                assistant=assistant,
                user=user_id,
                defaults={
                    'rating': rating,
                    'review': review
                }
            )

            # Get updated data for the template
            interactions = Conversation.objects.filter(assistant_id=assistant_id).count()
            ratings = AssistantRating.objects.filter(assistant=assistant_id)
            is_creator = user_id == assistant.user_id.id

            # Return to the same page with updated context
            return render(request, 'assistant/assistant.html', {
                "assistant": assistant,
                "interactions": interactions,
                "reviews": len(ratings),
                "is_creator": is_creator,
                "success_message": "Rating updated successfully"
            })

        except Exception as e:
            logger.error(f"Error updating rating: {str(e)}")
            return render(request, 'assistant/assistant.html', {
                "assistant": assistant,
                "error_message": "Error updating rating"
            })