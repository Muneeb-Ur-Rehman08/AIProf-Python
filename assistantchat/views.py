from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, HttpResponseBadRequest
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from typing import Optional, Any, Dict
import json
import logging
import uuid
from users.models import Assistant, SupabaseUser, AssistantRating
from .models import AssistantNotes
from .utils import ChatModule
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import os
from langgraph.store.memory import InMemoryStore
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader
from django.shortcuts import render, get_object_or_404
from app.modals.chat import get_llm
from langchain_core.messages import HumanMessage
from urllib.parse import unquote

logger = logging.getLogger(__name__)

os.getenv('LANGCHAIN_TRACING_V2')
os.getenv('LANGCHAIN_API_KEY')


memory_store = InMemoryStore()  # Global in-memory store

# Define sliding window parameters
MAX_MEMORY_SIZE = 20  # Maximum allowed entries in memory

chat_module = ChatModule()

@login_required(login_url='accounts/login/')
@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id=None):
    """
    Endpoint to process chat queries using LangGraph's memory store.
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        # logger.info(f"Data: {data}")
        prompt = data.get('message')
        assistant_id = data.get('id')

        if not prompt:
            return StreamingHttpResponse("Prompt is required", content_type='text/plain')

        if not request.user.is_authenticated:
            return StreamingHttpResponse("User not authenticated", content_type='text/plain')

        


        # Handle file uploads (images, PDFs)
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            # Validate file size (20MB limit)
            MAX_FILE_SIZE = 20 * 1024 * 1024
            if uploaded_file.size > MAX_FILE_SIZE:
                error_message = "File size exceeds 20MB limit"
                return JsonResponse({'status': 'error', 'message': error_message})
            

            file_extension = uploaded_file.name.split('.')[-1].lower()

            try:
                # Process image files
                if file_extension in ['jpg', 'jpeg', 'png']:
                    try:
                        image = Image.open(uploaded_file)
                        # Convert to RGB if necessary
                        if image.mode not in ('L', 'RGB'):
                            image = image.convert('RGB')
                        
                        extracted_text = pytesseract.image_to_string(image)
                        if not extracted_text.strip():
                            error_message = "No text could be extracted from the image"
                            return JsonResponse({'status': 'error', 'message': error_message})
                            
                        prompt += f"\nExtracted from image: {extracted_text}"
                        
                    except Exception as e:
                        error_message = f"Error processing image: {str(e)}"
                        return JsonResponse({'status': 'error', 'message': error_message})
                
                
                # Process PDF files
                elif file_extension == 'pdf':
                    try:
                        pdf_reader = PdfReader(uploaded_file)
                        extracted_text = ''
                        
                        # Extract text from all pages
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                extracted_text += page_text + "\n"
                        
                        if not extracted_text.strip():
                            error_message = "No text could be extracted from the PDF"
                            return JsonResponse({'status': 'error', 'message': error_message})
                            
                        prompt += f"\nExtracted from PDF: {extracted_text}"
                        
                    except Exception as e:
                        error_message = f"Error processing PDF: {str(e)}"
                        return JsonResponse({'status': 'error', 'message': error_message})

            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                return JsonResponse({'status': 'error', 'message': error_message})



        # Get user and assistant details
        user = User.objects.get(id=request.user.id)
        user_id = str(user.id)

        logger.info(f"User_id: {user_id}")

        if not assistant_id:
            return StreamingHttpResponse("Assistant ID is required", content_type='text/plain')

        assistant = Assistant.objects.get(id=assistant_id)


        chat_history, keys = get_history(assistant_id=assistant_id, user_id=user_id)

        has_reviewed = AssistantRating.objects.filter(user=request.user, assistant=assistant).exists()
        show_review = len(chat_history) >= 2 and not has_reviewed

        # Define assistant configuration
        # assistant_config = {
        #     "subject": assistant.subject,
        #     "topic": assistant.topic,
        #     "teacher_instructions": assistant.teacher_instructions,
        #     "user_name": user.first_name,
        #     "prompt_instructions": mermaid_instructions
        # }

        # Process the message with chat history
        response = chat_module.process_message(
            prompt=prompt,
            assistant_id=str(assistant.id),
            user_id=str(user),
            assistant_config=assistant_config(assistant_id=assistant_id, user_id=user_id),
            chat_history=chat_history
        )

        # Streaming the response
        def response_stream():
            full_response = ""
            try:
                for chunk in response:
                    if chunk:
                        full_response += chunk
                        # Send the chunk along with review status
                        yield json.dumps({
                            'text': chunk,
                            'showReview': show_review,
                            'isLastChunk': False
                        })

                save_history(assistant_id, user_id, prompt, full_response)

                # Send final chunk with review status
                yield json.dumps({
                    'text': '',
                    'showReview': show_review,
                    'isLastChunk': True
                })
                
            except Exception as e:
                logger.error(f"Error in chat query response: {e}")
                # Send final chunk with review status
                yield json.dumps({
                    'text': '',
                    'showReview': show_review,
                    'isLastChunk': True
                })

        return StreamingHttpResponse(response_stream(), content_type='text/event-stream')

    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return StreamingHttpResponse(json.dumps({
                'text': "Failed to process chat query",
                'showReview': False,
                'isLastChunk': True
            }),
            content_type='text/event-stream')
    

def voice_chat(request):
    return render(request, 'voiceAssistant.html')



@login_required(login_url='accounts/login/')
@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_notes(request, assistant_id):
    try:

        logger.info(f"Request we get: {request}")
        # Validate user is authenticated
        if not request.user.is_authenticated:
            return HttpResponseBadRequest("User not authenticated")

        # Get assistant and user
        try:
            assistant = Assistant.objects.get(id=assistant_id)
            user = request.user
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Assistant not found")

        # Get and decode parameters
        try:
            notes = request.GET.get('notes', '')
            question = request.GET.get('question', '')
            
            # Validate inputs
            if not notes or not question:
                return HttpResponseBadRequest("Missing required parameters")

            logger.info(f"Processing notes request - User: {user.id}, Assistant: {assistant_id}")
            logger.debug(f"Question: {question[:100]}...")  # Log first 100 chars for debugging
        except Exception as e:
            logger.error(f"Error decoding parameters: {str(e)}")
            return HttpResponseBadRequest("Invalid parameters")

        # Generate and save notes
        try:
            generated_notes = generate_notes(question, notes)
            AssistantNotes.objects.create(
                user=user,
                assistant=assistant,
                question=question,
                notes=generated_notes
            )
        except Exception as e:
            logger.error(f"Error generating/saving notes: {str(e)}")
            return HttpResponseBadRequest("Error creating notes")

        # Get all notes for rendering
        all_notes = AssistantNotes.objects.filter(
            user=user,
            assistant=assistant
        ).order_by('-created_at')

        # Render template
        try:
            html = render_to_string('notes_panel.html', {
                'notes': all_notes,
                'success': True
            })
            
            # Add HX-Trigger for success notification
            response = HttpResponse(html)
            response['HX-Trigger'] = json.dumps({
                'showNotification': {
                    'message': 'Notes created successfully',
                    'type': 'success'
                }
            })
            return response

        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return HttpResponseBadRequest("Error rendering notes")

    except Exception as e:
        logger.error(f"Unexpected error in create_notes: {str(e)}")
        return HttpResponseBadRequest("An unexpected error occurred")


@login_required
@require_http_methods(["POST", "GET"])
def submit_review(request, assistant_id):
    assistant = get_object_or_404(Assistant, id=assistant_id)

    # Prevent duplicate reviews
    if AssistantRating.objects.filter(user=request.user, assistant=assistant).exists():
        return JsonResponse({"status": "error", "message": "You have already submitted a review."})

    if request.method == "POST":
        rating = request.POST.get("rating")
        review = request.POST.get("review")

        AssistantRating.objects.create(
            user=request.user,
            assistant=assistant,
            rating=rating,
            review=review
        )

        return JsonResponse({"status": "success", "message": "Thank you for your feedback!"})

    return JsonResponse({"status": "error", "message": "Invalid submission."}, status=400)

def get_history(assistant_id, user_id):
    # Define the namespace
        namespace = ("chat", user_id, assistant_id)

        count = 0
        # Retrieve all keys and values in the namespace
        try:
            items = memory_store.search(namespace)  # Retrieve all items in namespace
            items.sort(key=lambda x: x.key)  # Ensure items are ordered by keys
            chat_history = [item.value for item in items]  # Extract chat data
            keys = [item.key for item in items]  # Extract keys
            # logger.info(f"Retrieved keys in namespace: {keys}")
            return chat_history, keys
        except Exception as e:
            logger.error(f"Error retrieving keys: {e}")
            chat_history, keys = [], []


def save_history(assistant_id, user_id, prompt, full_response):

    namespace = ("chat", user_id, assistant_id)

    chat_history, keys = get_history(assistant_id, user_id)

    chat_summary = next(
            (entry["summary"] for entry in chat_history if "summary" in entry),
            "No summary available. Use chat history only to generate chat summary."
        )
    knowledge_level = next(
        (entry["knowledge_level"] for entry in chat_history if "knowledge_level" in entry),
        "No knowledge level available. Use chat history only to generate assessment."
    )

    # Add the new user message to memory
    next_key = f"chat-{len(keys)}"
    new_entry = {"User": prompt, "AI": "", "summary": chat_summary}  # Placeholder for assistant response
    memory_store.put(namespace, next_key, new_entry)
    chat_history.append(new_entry)
    keys.append(next_key)

    # Dynamically apply sliding window logic if memory exceeds MAX_MEMORY_SIZE
    if len(chat_history) >= 20:

        oldest_keys = keys[:10]
        # Offload the oldest 10 messages to the database
        offloaded_messages = chat_history[:10]

        chat_module.save_chat_history(user_id, assistant_id, offloaded_messages)

        logger.info(f"\n\nCurrent sumamry : {chat_summary}\n\n")

        chat_summary = chat_module.analyze_chat_history(offloaded_messages, chat_summary)

        knowledge_level = chat_module.assess_user_knowledge(offloaded_messages)


        # **Delete old messages using BaseStore.delete()**
        for key in oldest_keys:
            memory_store.delete(namespace, key)

    # Save the current interaction in memory
    try:
        key = f"chat-{len(memory_store.search(namespace))}"
        memory_store.put(namespace, next_key, {
            "User": prompt,
            "AI": full_response,
            "summary": chat_summary,
            "knowledge_level": knowledge_level
            }
        )

        # logger.info(f"Saved memory: namespace={namespace}, key={key}, data={{'user': '{prompt}', 'assistant': '{full_response}', 'summary': '{chat_summary}'}}")
    except Exception as e:
        logger.error(f"Error saving chat memory: {e}")


def assistant_config(assistant_id, user_id):
    assistant = Assistant.objects.get(id=assistant_id)
    user = User.objects.get(id=user_id)

    mermaid_instructions = '''
            Help me with short and to the point diagrams wherever you see fit using 
            mermaid.js code, as example given below. Double make sure the code error-free 
            and provide one graph per block:\n
            
            note: pie is always in percentage without mentioning %
            
            ```mermaid
            pie title NETFLIX
                 "Time spent looking for movie" : 90
                 "Time spent watching it" : 10
                
            sequenceDiagram
                Alice ->> Bob: Hello Bob, how are you?
                Bob-->>John: How about you John?
                Bob--x Alice: I am good thanks!
                Bob-x John: I am good thanks!
                Note right of John: Bob thinks a long<br/>long time, so long<br/>that the text does<br/>not fit on a row.
            
                Bob-->Alice: Checking with John...
                Alice->John: Yes... John, how are you?

            graph LR
                A[Square Rect] -- Link text --> B((Circle))
                A --> C(Round Rect)
                B --> D(Rhombus)
                C --> D
            
            ```
        '''
    return {
            "subject": assistant.subject,
            "topic": assistant.topic,
            "teacher_instructions": assistant.teacher_instructions,
            "user_name": user.first_name,
            "prompt_instructions": mermaid_instructions
        }

def generate_notes(
    prompt, response
) :
    # Langchain Setup
    llm = get_llm()

    full_prompt = f"""
    Create comprehensive notes based on the given question and response.
    - Give a topic name to the notes according to the question.
    - The notes should be informative and helpful.
    - The notes should be concise yet informative.
    - Summarizing the key points discussed and highlighting important aspects related to the topic.

    Context:
    - Question: {prompt}
    - Response: {response}
    """
    # Construct detailed prompt

    # Initialize message
    messages = [HumanMessage(content=full_prompt)]

    # Generate response
    response = llm.invoke(messages)

    return response.content