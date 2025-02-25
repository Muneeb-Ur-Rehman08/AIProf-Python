from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from typing import Optional, Any, Dict, Generator
import json
import logging
import uuid
from users.models import Assistant, SupabaseUser, AssistantRating
from .models import AssistantNotes,Quiz, QuestionAttempt, Question, QuizAttempt
from .utils import ChatModule
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import os
from langgraph.store.memory import InMemoryStore
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader
from django.shortcuts import render, get_object_or_404, redirect
from app.modals.chat import get_llm
from langchain_core.messages import HumanMessage
import time
import sys

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
        show_review = len(chat_history) >= 9 and not has_reviewed

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

        logger.info(f"Response: {response}")

        # Streaming the response
        def response_stream() -> Generator[Any, Any, Any]:
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
                        }) + "\n"
                        
                        # Explicitly flush the output buffer to ensure streaming
                        sys.stdout.flush()

                save_history(assistant_id, user_id, prompt, full_response)

                # Send final chunk with review status
                yield json.dumps({
                    'text': '',
                    'showReview': show_review,
                    'isLastChunk': True
                }) + "\n"

                sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error in chat query response: {e}")
                # Send final chunk with review status
                yield json.dumps({
                    'text': '',
                    'showReview': show_review,
                    'isLastChunk': True
                }) + "\n"
                sys.stdout.flush()

        return StreamingHttpResponse(response_stream(), content_type='text/event-stream')

    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return StreamingHttpResponse(json.dumps({
                'text': "Failed to process chat query",
                'showReview': False,
                'isLastChunk': True
            }) + "\n",
            content_type='text/event-stream')
    

def voice_chat(request):
    return render(request, 'voiceAssistantview.html')



@login_required(login_url='accounts/login/')
@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_notes(request, assistant_id):

    user_id = request.user.id  # Current authenticated user
    user = User.objects.get(id=user_id)

    assistant = Assistant.objects.get(id=assistant_id)

    if request.method == 'GET':
        

        # Try to retrieve notes (you can add more filtering logic as needed)
        notes = AssistantNotes.objects.filter(assistant_id=assistant, user_id=user)
        
        html = render_to_string('notes_item.html', {
            'note': notes,
            'all_notes': True
            })
        return HttpResponse(html)
        

    elif request.method == 'POST':
        try:
            # Handle POST request to create new notes
            
            prompt = request.POST.get('prompt', '')
            response = request.POST.get('response', '')
            
            if not prompt or not response:
                return HttpResponseBadRequest("Missing 'prompt' or 'response' fields.")
            
            notes_content = generate_notes(prompt=prompt, response=response)

            logger.info(f"Generate notes are: {notes_content}")

            # Create a new AssistantNotes entry
            assistant_note = AssistantNotes.objects.create(
                user_id=user,
                assistant_id=assistant,
                question=prompt,
                notes=notes_content
            )
            
            # assistant_note.save()
            html = render_to_string('notes_item.html', {
                'note': assistant_note,
                'all_notes': False
                })
            # Return success response
            return HttpResponse(html)

        except Exception as e:
            logger.error(f"Error generating/saving notes: {str(e)}")
            return HttpResponseBadRequest(f"Error generating/saving notes: {str(e)}")

    else:
        return HttpResponseBadRequest("Invalid request method.")


def create_note(request, assistant_id):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    assistant = Assistant.objects.get(id=assistant_id)

    if request.method == 'GET':
        notes = AssistantNotes.objects.filter(assistant_id=assistant, user_id=user)
        html = render_to_string('notes_item.html', {
            'note': notes,
            'all_notes': True
        })
        return HttpResponse(html)

    elif request.method == 'POST':
        try:
            # Get chat history from memory store
            chat_history, keys = get_history(str(assistant_id), str(user_id))

            logger.info(f"chat history against \nuser:{user} \nassistant:{assistant} \nhistory: {chat_history}")
            
            if not chat_history:
                return HttpResponseBadRequest("No chat history found")
            
            # Get the last message pair (user prompt and AI response)
            last_messages = chat_history[-2:]  # Get last two messages
            
            if len(last_messages) < 2:
                return HttpResponseBadRequest("Insufficient chat history")
                
            chat_history_str = "\n".join([
                f"Human: {chat['User']}\nAssistant: {chat['AI']}"
                for chat in last_messages
            ])
            
            # Get the ID of the button that triggered the request
            trigger_id = request.headers.get('HX-Trigger')
            
            # Generate notes based on which button was clicked
            if trigger_id == 'study-guide':
                notes_content = generate_study_guide(chat_history_str)
            elif trigger_id == 'briefing-doc':
                notes_content = generate_briefing_doc(chat_history_str)
            else:
                notes_content = generate_study_guide(chat_history_str)

            logger.info(f"Generated notes are: {notes_content}")

            assistant_note = AssistantNotes.objects.create(
                user_id=user,
                assistant_id=assistant,
                question="",
                notes=notes_content
                
            )

            html = render_to_string('notes_item.html', {
                'note': assistant_note,
                'all_notes': False
            })
            return HttpResponse(html)

        except Exception as e:
            logger.error(f"Error generating/saving notes: {str(e)}")
            return HttpResponseBadRequest(f"Error generating/saving notes: {str(e)}")

    return HttpResponseBadRequest("Invalid request method.")


def delete_note(request, note_id):
    if request.method == 'DELETE':
        try:
            user_id = request.user.id
            note = AssistantNotes.objects.get(id=note_id, user_id=user_id)
            note.delete()
            # Return a response with HX-Trigger to remove the element
            response = HttpResponse()
            response['HX-Trigger'] = 'noteDeleted'
            return response
        except AssistantNotes.DoesNotExist:
            return HttpResponseNotFound("Note not found or unauthorized")
    return HttpResponseBadRequest("Invalid request method")


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


@login_required
@require_http_methods(["GET", "POST"])
def quiz_view(request, assistant_id):

    user = User.objects.get(id=request.user.id)
    assistant = Assistant.objects.get(id=assistant_id)

    if request.method == "GET":
        

        # Get chat history from memory store
        chat_history, keys = get_history(assistant_id, str(user.id))
        
        if not chat_history:
            return HttpResponseBadRequest("No chat history found")

        context = "\n".join([
            f"{chat['AI']}"
            for chat in chat_history
        ])
        
        # Generate or retrieve existing quiz
        quiz = Quiz.objects.create(
            assistant_id=assistant,
            user_id=user,
            context=context
        )
        
        # Generate questions using LLM
        questions_data = generate_quiz_questions(context)

        logger.info(f"Questions: {questions_data}")
        # Store questions in database
        for q_data in eval(questions_data):
            Question.objects.create(
                quiz=quiz,
                question_text=q_data['question_text'],
                option_a=q_data['option_a'],
                option_b=q_data['option_b'],
                option_c=q_data['option_c'],
                option_d=q_data['option_d'],
                correct_answer=q_data['correct_answer']
            )
        
        # Create quiz attempt
        quiz_attempt = QuizAttempt.objects.create(
            user_id=user,
            assistant_id=assistant,
            quiz=quiz
        )
        
        # Return first question template
        return render(request, 'quiz_question.html', {
            'quiz': quiz,
            'question': quiz.questions.first(),
            'attempt': quiz_attempt,
            'assistant': assistant
        })

    elif request.method == "POST":
        question_id = request.POST.get('question_id')
        selected_option = request.POST.get('answer')


        logger.info(f"Question id: {question_id} selected option: {selected_option}")

        # Fetch the question
        question = Question.objects.get(id=question_id)
        quiz_attempt = QuizAttempt.objects.get(
            user_id=user,
            assistant_id=assistant,
            quiz=question.quiz,
            completed=False
        )

        # Record the user's answer and determine if it is correct
        is_correct = selected_option == question.correct_answer
        QuestionAttempt.objects.create(
            quiz_attempt=quiz_attempt,
            question=question,
            selected_option=selected_option,
            is_correct=is_correct
        )

        # Get the next question or finish the quiz
        next_question = question.quiz.questions.filter(id__gt=question.id).first()

        if next_question:
            return render(request, 'quiz_question.html', {
                'quiz': question.quiz,
                'question': next_question,
                'attempt': quiz_attempt,
                'previous_result': {
                    'is_correct': is_correct,
                    'correct_answer': question.correct_answer
                },
                'assistant': assistant
            })
        else:
            # Complete the quiz
            quiz_attempt.completed = True
            quiz_attempt.completed_at = timezone.now()
            quiz_attempt.total_correct = quiz_attempt.questionattempt_set.filter(is_correct=True).count()
            quiz_attempt.save()

            # Calculate the percentage of correct answers
            total_questions = quiz_attempt.questionattempt_set.count()
            correct_percentage = (quiz_attempt.total_correct / total_questions) * 100 if total_questions > 0 else 0


            return render(request, 'quiz_result.html', {
                'attempt': quiz_attempt,
                'assistant': assistant,
                'correct_percentage': correct_percentage
            })

    return HttpResponseBadRequest("Invalid request method")


@login_required
def check_answer(request, question_id):
    """Check the answer and return next question or results"""
    question = Question.objects.get(id=question_id)
    selected_option = request.POST.get('answer')
    quiz_attempt = QuizAttempt.objects.get(
        user=request.user,
        quiz=question.quiz,
        completed=False
    )
    
    # Record the attempt
    is_correct = selected_option == question.correct_answer
    QuestionAttempt.objects.create(
        quiz_attempt=quiz_attempt,
        question=question,
        selected_option=selected_option,
        is_correct=is_correct
    )
    
    # Get next question or finish quiz
    next_question = question.quiz.questions.filter(id__gt=question.id).first()
    
    if next_question:
        return render(request, 'quiz_question.html', {
            'quiz': question.quiz,
            'question': next_question,
            'attempt': quiz_attempt,
            'previous_result': {
                'is_correct': is_correct,
                'correct_answer': question.correct_answer
            }
        })
    else:
        # Complete the quiz
        quiz_attempt.completed = True
        quiz_attempt.completed_at = timezone.now()
        quiz_attempt.total_correct = quiz_attempt.questionattempt_set.filter(is_correct=True).count()
        quiz_attempt.save()
        
        return render(request, 'quiz_result.html', {
            'attempt': quiz_attempt
        })


# Helper Functions

def generate_study_guide(messages):
    study_guide_prompt = f"""
    Create educational study notes that focus on learning and retention:
    
    Requirements:
    1. Begin with a clear topic heading that captures the main subject
    2. Include 3-4 key learning points
    3. Highlight important concepts, formulas, or procedures
    4. Define any technical terms or jargon
    5. Make complex ideas easier to understand
    
    Format:
    - Topic name as heading
    - 3-4 bullet points
    - Each point should be 1-2 sentences
    
    Source Material:
    {messages}
    """
    
    llm = get_llm()
    messages = [HumanMessage(content=study_guide_prompt)]
    result = llm.invoke(messages)
    return result.content

def generate_briefing_doc(messages):
    briefing_prompt = f"""
    Create a concise briefing document summarizing this conversation:
    
    Requirements:
    1. Create a clear summary title
    2. Extract key points and decisions
    3. Identify action items or next steps
    4. Keep it business-focused and actionable
    
    Format:
    - Document title
    - 3-4 main points
    - Each point should be clear and actionable
    
    Source Material:
    {messages}
    """
    
    llm = get_llm()
    messages = [HumanMessage(content=briefing_prompt)]
    result = llm.invoke(messages)
    return result.content

def generate_notes(
    prompt, response
) :
    # Langchain Setup
    llm = get_llm()

    full_prompt = f"""
        Create clear and concise notes based on the provided question and response.
        - Assign a relevant topic name as a heading for the notes, reflecting the question.
        - Ensure the notes are informative yet brief, summarizing key points.
        - The notes should consist of 3 to 4 bullet points that cover the entire response.
        - Highlight essential aspects and key takeaways related to the topic.

        Format the response in bullet points without using markdown.

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


def generate_quiz_questions(
    context
) :
    # Langchain Setup
    llm = get_llm()

    full_prompt = f"""
    Generate 5 multiple choice questions based on this context:
    {context}
    
    Format: Without adding any extra text or character in response return pure list of dict. Return a list of dictionaries with keys:
    - question_text
    - option_a
    - option_b
    - option_c
    - option_d
    - correct_answer (as 'A', 'B', 'C', or 'D')
    """

    # Initialize message
    messages = [HumanMessage(content=full_prompt)]

    # Generate response
    response = llm.invoke(messages)

    return response.content

# Get chat history from memory
def get_history(assistant_id, user_id):
    # Define the namespace
        namespace = ("chat", user_id, assistant_id)
        print(f"Fetching chat history from namespace: {namespace}")  # Debugging



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

# Save chat history to memory
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

# Get assistant config
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