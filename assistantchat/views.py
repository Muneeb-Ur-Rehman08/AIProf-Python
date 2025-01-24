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
from django.contrib.auth.decorators import login_required
import os
from django.shortcuts import render

logger = logging.getLogger(__name__)

os.getenv('LANGCHAIN_TRACING_V2')
os.getenv('LANGCHAIN_API_KEY')


@login_required(login_url='accounts/login/')
@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process chat queries and save conversations.
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        try:
            prompt = data.get('message')
            assistant_id = data.get('id')
            if not prompt:
                return StreamingHttpResponse("Prompt is required", content_type='text/plain')

        except json.JSONDecodeError:
            return StreamingHttpResponse("Invalid JSON body", content_type='text/plain')

        # User authentication check
        if not request.user.is_authenticated:
            return StreamingHttpResponse("User not authenticated", content_type='text/plain')

        try:
            user = User.objects.get(id=request.user.id)
            user_id = str(user.id)
        except (SupabaseUser.DoesNotExist, ValueError):
            return StreamingHttpResponse("Invalid user authentication", content_type='text/plain')

        # Assistant validation
        if not assistant_id:
            return StreamingHttpResponse("Assistant ID is required", content_type='text/plain')

        try:
            assistant = Assistant.objects.get(id=assistant_id)
        except (ValueError, TypeError):
            return StreamingHttpResponse("Invalid assistant ID format", content_type='text/plain')
        except Assistant.DoesNotExist:
            return StreamingHttpResponse("Assistant not found", content_type='text/plain')

        assist_instructions = assistant.teacher_instructions or ""
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
            
            ```
        '''
        final_instructions = assist_instructions + "\n" + mermaid_instructions
        
        assistant_config = {
            "subject": assistant.subject,
            "topic": assistant.topic,
            "teacher_instructions": assistant.teacher_instructions,
            "prompt_instructions": mermaid_instructions,
            "prompt": prompt,
            "user_name": user.first_name
        }

        # Initialize chat module and process message
        chat_module = ChatModule()
        response = chat_module.process_message(
            prompt=prompt,
            assistant_id=str(assistant.id),
            user_id=user_id,
            assistant_config=assistant_config,
        )

        # Streaming the response
        def response_stream():
            try:
                for chunk in response:
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Error in chat query response: {e}")
                yield "Failed to process chat query"

        return StreamingHttpResponse(response_stream(), content_type='text/plain')

    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return StreamingHttpResponse("Failed to process chat query", content_type='text/plain')

@login_required(login_url='accounts/login/')
def voice_chat(request):
    """
    Render the voice chat interface
    """
    return render(request, 'voice.html')
