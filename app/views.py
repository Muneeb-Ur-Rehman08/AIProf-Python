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
from django.shortcuts import render, redirect
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
     # Append subjects data to assistants
    # subjects_data = [
    #     {
    #         "name": "Mathematics",
    #         "topics": [
    #             "Arithmetic", "Addition", "Subtraction", "Multiplication", "Division",
    #             "Fractions", "Decimals", "Percentages", "Algebra", "Linear Equations",
    #             "Quadratic Equations", "Inequalities", "Polynomials", "Geometry", "Shapes",
    #             "Angles", "Theorems", "Coordinate Geometry", "Trigonometry", "Sine",
    #             "Cosine", "Tangent", "Pythagoras' Theorem", "Calculus", "Limits",
    #             "Derivatives", "Integrals", "Differential Equations", "Statistics & Probability",
    #             "Mean", "Median", "Mode", "Standard Deviation"
    #         ]
    #     },
    #     {
    #         "name": "Science",
    #         "topics": [
    #             "Physics", "Newton's Laws of Motion", "Electricity", "Magnetism",
    #             "Thermodynamics", "Waves", "Quantum Mechanics", "Chemistry", "Periodic Table",
    #             "Chemical Reactions", "Molecular Structure", "Acids and Bases", "Organic Chemistry",
    #             "Biology", "Cell Structure", "Human Anatomy", "Genetics", "Ecology", "Evolution"
    #         ]
    #     },
    #     {
    #         "name": "English",
    #         "topics": [
    #             "Grammar", "Sentence Structure", "Tenses", "Vocabulary", "Writing Skills",
    #             "Essay Writing", "Creative Writing", "Literature", "Poetry Analysis",
    #             "Novel Studies", "Drama", "Research and Citation"
    #         ]
    #     },
    #     {
    #         "name": "History",
    #         "topics": [
    #             "Ancient Civilizations", "Greek and Roman History", "Middle Ages", "Renaissance",
    #             "World Wars", "American Revolution", "Industrial Revolution", "Modern History",
    #             "Cold War", "Civil Rights Movement"
    #         ]
    #     },
    #     {
    #         "name": "Geography",
    #         "topics": [
    #             "Physical Geography", "Landforms", "Weather and Climate", "Ecosystems",
    #             "Human Geography", "Population Studies", "Urbanization", "Economic Geography",
    #             "Global Trade"
    #         ]
    #     },
    #     {
    #         "name": "Computer Science",
    #         "topics": [
    #             "Programming Basics", "Algorithms", "Data Structures", "Databases",
    #             "Web Development", "Networking", "Cybersecurity", "Artificial Intelligence",
    #             "Machine Learning"
    #         ]
    #     },
    #     {
    #         "name": "Art",
    #         "topics": [
    #             "Drawing Techniques", "Painting Styles", "Sculpture", "Art History",
    #             "Photography", "Digital Art", "Design Principles"
    #         ]
    #     },
    #     {
    #         "name": "Physical Education",
    #         "topics": [
    #             "Fitness Training", "Team Sports", "Individual Sports", "Health and Nutrition",
    #             "Mental Well-being", "Exercise Physiology"
    #         ]
    #     }
    # ]
    

    # Fetch subjects from the database
    subjects_data = Subject.objects.prefetch_related(
        'topics'
        ).all()
    

    # Fetch Assistants from the database with conversation counts
    assistants = Assistant.objects.all()


    # Retrieve filter parameters
    keyword = request.GET.get('keyword', '').strip()
    subjects = request.GET.getlist('subject')
    topics = request.GET.getlist('topic')
    
    # Rating filter parameters
    if request.GET.getlist('filter_rating'):
        rating_filters = request.GET.getlist('filter_rating')
        rating_q = Q()
        for rating in rating_filters:
            try:
                rating = Decimal(rating)
                rating_q |= Q(
                    average_rating__gte=rating,
                    average_rating__lt=rating + Decimal('1')
                )
            except (ValueError, InvalidOperation):
                continue
        if rating_q:
            assistants = assistants.filter(rating_q)
    
    
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

    # Find the sorting value that matches the label
    sort_value = '-created_at'  # default value
    for sort_option in sorting_options.values():
        if sort_option['label'] == sort_label:
            sort_value = sort_option['value']
            break
    
    logger.info(f"current sort: {sort_value}")
    # Apply sorting
    assistants = assistants.order_by(sort_value)
    
    # Filtering logic
    # Keyword search
    if keyword and len(keyword) > 2:
        assistants = assistants.filter(
            Q(name__icontains=keyword) | 
            Q(description__icontains=keyword)
        )
    
    # Subject and Topic Filtering
    if subjects:
        assistants = assistants.filter(subject__in=subjects)
    
    if topics:
        assistants = assistants.filter(topic__in=topics)
    
    
    # Prepare the data for rendering
    assistants_data = [
        {
            "id": str(assistant.id),
            "name": assistant.name,
            "subject": assistant.subject if assistant.subject else None,
            "topic": assistant.topic if assistant.topic else None,
            "description": assistant.description,
            "created_at": assistant.created_at,
            "interactions": assistant.interactions,
            "average_rating": assistant.average_rating,
            "total_reviews": assistant.total_reviews
        } for assistant in assistants
    ]
    
    # Get rating counts
    rating_counts = AssistantRating.objects.values('rating').annotate(
        count=Count('id')
    ).order_by('-rating')

    # Format rating counts for template
    formatted_rating_counts = {
        5: 0, 4: 0, 3: 0, 2: 0, 1: 0
    }
    
    for rating in rating_counts:
        if rating['rating'] is not None:
            # Get the rating value
            rating_value = float(rating['rating'])
            
            # Determine which bucket this rating belongs in
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

    # Context for template
    context = {
        "subjects_data": subjects_data,
        "filtered_assistants": assistants_data,
        "sorting_options": {opt['value']: opt['label'] for opt in sorting_options.values()},
        "current_sort": sort_label,
        "rating_counts": formatted_rating_counts
    }
    
    # HTMX partial rendering
    if request.htmx:
        return render(request, 'assistant/list_partials.html', {
            'assistants': assistants_data,
            'current_sort': sort_label
        })
    else:
        return render(request, 'assistant/list.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def assistant_detail(request, assistant_id: Optional[str] = None):

    # logged in user id
    user_id = request.user.id

    try:
        interactions = Conversation.objects.filter(assistant_id=assistant_id).count()
        assistant = Assistant.objects.get(id=assistant_id)
        ratings = AssistantRating.objects.filter(assistant=assistant_id)
    except Assistant.DoesNotExist:
        raise Http404("Assistant not found")

    logger.info(f"user_id: {user_id}, assistant: {assistant.user_id.id}")

    is_creator = user_id == assistant.user_id.id
    
    return render(request, 'assistant/assistant.html', {"assistant": assistant, "interactions": interactions, "reviews": len(ratings), "is_creator": is_creator})
