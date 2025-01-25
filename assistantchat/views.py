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
        # Get user and assistant details
        user = User.objects.get(id=request.user.id)
        user_id = str(user.id)

        if not assistant_id:
            return StreamingHttpResponse("Assistant ID is required", content_type='text/plain')

        assistant = Assistant.objects.get(id=assistant_id)

        # Define the namespace
        namespace = ("chat", user_id, assistant_id)
        chat_summary = "helo abc hello"
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

        # Add the new user message to memory
        next_key = f"chat-{len(keys)}"
        new_entry = {"User": prompt, "AI": "", "summary": chat_summary}  # Placeholder for assistant response
        memory_store.put(namespace, next_key, new_entry)
        chat_history.append(new_entry)
        keys.append(next_key)
        

        # Dynamically apply sliding window logic if memory exceeds MAX_MEMORY_SIZE
        if len(chat_history) >= MAX_MEMORY_SIZE:

            logger.info(f"\n\n Now we are in saving memory")
            # Offload the oldest 10 messages to the database
            offloaded_messages = chat_history[:10]

            logger.info(f"\n\nstart Save to db in views\n\n")

            chat_module.save_chat_history(user_id, assistant_id, offloaded_messages)


            chat_summary = chat_module.analyze_chat_history(offloaded_messages)


            # Remove the oldest 10 messages from memory
            chat_history = chat_history[10:]

            # Add the generated summary to memory
            chat_history.append({"summary": chat_summary})


        # Save updated chat history back to the memory store
        for idx, message in enumerate(chat_history):
            memory_store.put(namespace, f"chat-{idx}", message)

        # Initialize chat module

        # Define assistant configuration
        assistant_config = {
            "subject": assistant.subject,
            "topic": assistant.topic,
            "teacher_instructions": assistant.teacher_instructions,
            "user_name": user.first_name
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
                    memory_store.put(namespace, next_key, {"User": prompt, "AI": full_response, "summary": chat_summary})
                    # logger.info(f"chat history saved to memory{chat_history}")
                except Exception as e:
                    logger.error(f"Error saving chat memory: {e}")
            except Exception as e:
                logger.error(f"Error in chat query response: {e}")
                yield "Failed to process chat query"

        return StreamingHttpResponse(response_stream(), content_type='text/plain')

    except Exception as e:
        logger.error(f"Error in chat query endpoint: {e}")
        return StreamingHttpResponse("Failed to process chat query", content_type='text/plain')