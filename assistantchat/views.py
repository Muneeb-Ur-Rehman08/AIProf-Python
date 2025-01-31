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
from langgraph.store.memory import InMemoryStore
from PIL import Image
import pytesseract
import PyPDF2

logger = logging.getLogger(__name__)

os.getenv('LANGCHAIN_TRACING_V2')
os.getenv('LANGCHAIN_API_KEY')


memory_store = InMemoryStore()  # Global in-memory store

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

        chat_module = ChatModule()


        # Handle file uploads (images, PDFs)
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            file_extension = uploaded_file.name.split('.')[-1].lower()

            if file_extension in ['jpg', 'jpeg', 'png']:
                # Process image (use OCR for text extraction)
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(image)
                prompt += f"\nExtracted from image: {extracted_text}"
            elif file_extension == 'pdf':
                # Process PDF (extract text from PDF)
                pdf_reader = PyPDF2.PdfFileReader(uploaded_file)
                extracted_text = ''
                for page_num in range(pdf_reader.numPages):
                    extracted_text += pdf_reader.getPage(page_num).extract_text()
                prompt += f"\nExtracted from PDF: {extracted_text}"



        # Get user and assistant details
        user = User.objects.get(id=request.user.id)
        user_id = str(user.id)

        if not assistant_id:
            return StreamingHttpResponse("Assistant ID is required", content_type='text/plain')

        assistant = Assistant.objects.get(id=assistant_id)

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
        except Exception as e:
            logger.error(f"Error retrieving keys: {e}")
            chat_history, keys = [], []

        # Define sliding window parameters
        MAX_MEMORY_SIZE = 20  # Maximum allowed entries in memory

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
        if len(chat_history) >= MAX_MEMORY_SIZE:

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

        # Define assistant configuration
        assistant_config = {
            "subject": assistant.subject,
            "topic": assistant.topic,
            "teacher_instructions": assistant.teacher_instructions,
            "user_name": user.first_name,
            "prompt_instructions": mermaid_instructions
        }

        # Process the message with chat history
        response = chat_module.process_message(
            prompt=prompt,
            assistant_id=str(assistant.id),
            user_id=str(user),
            assistant_config=assistant_config,
            chat_history=chat_history     
        )

        # Streaming the response
        def response_stream():
            full_response = ""
            try:
                for chunk in response:
                    if chunk:
                        full_response += chunk
                        yield chunk

                # Save the current interaction in memory
                try:
                    key = f"chat-{len(memory_store.search(namespace))}"
                    memory_store.put(namespace, next_key, {"User": prompt, "AI": full_response, "summary": chat_summary, "knowledge_level": knowledge_level})
                   

                    # logger.info(f"Saved memory: namespace={namespace}, key={key}, data={{'user': '{prompt}', 'assistant': '{full_response}', 'summary': '{chat_summary}'}}")
                except Exception as e:
                    logger.error(f"Error saving chat memory: {e}")
            except Exception as e:
                logger.error(f"Error in chat query response: {e}")
                yield "Failed to process chat query"

        return StreamingHttpResponse(response_stream(), content_type='text/plain')

    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return StreamingHttpResponse("Failed to process chat query", content_type='text/plain')