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

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS", "GET"])
def chat_query(request, ass_id: Optional[str] = None):
    """
    Endpoint to process chat queries and save conversations.
    """

    def generate_response():
        try:
            # Parse request body
            data = json.loads(request.body)
            try:

                prompt = data.get('message')
                assistant_id = data.get('id')
                if not prompt:
                    yield "Prompt is required"
                    return

            except json.JSONDecodeError:
                yield "Invalid JSON body"
                return

            # User authentication check
            if not request.user.is_authenticated:
                yield "User not authenticated"
                return

            try:
                user = User.objects.get(id=request.user.id)
                user_id = str(user.id)
            except (SupabaseUser.DoesNotExist, ValueError):
                yield "Invalid user authentication"
                return

            # Assistant validation
            if not assistant_id:
                yield "Assistant ID is required"
                return

            try:
                assistant = Assistant.objects.get(id=assistant_id)
            except (ValueError, TypeError):
                yield "Invalid assistant ID format"
                return
            except Assistant.DoesNotExist:
                yield "Assistant not found"
                return

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
            }

            # Initialize chat module and process message
            chat_module = ChatModule()
            response = chat_module.process_message(
                prompt=prompt,
                assistant_id=assistant.id,
                user_id=user_id,
                assistant_config=assistant_config,
            )

            # Collect and yield responses
            for chunk in response:
                if chunk:
                    yield chunk

        except Exception as e:
            logger.error(f"Error in chat query endpoint: {e}")
            yield "Failed to process chat query"

    # Return a StreamingHttpResponse with the generator
    return StreamingHttpResponse(
        generate_response(),
        content_type='text/plain'
    )
