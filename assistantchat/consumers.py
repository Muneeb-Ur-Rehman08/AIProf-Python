import json
from channels.generic.websocket import AsyncWebsocketConsumer
from langchain_openai import ChatOpenAI
import os
import base64
import io
from openai import OpenAI
import requests
import wave
import numpy as np
from dotenv import load_dotenv
import audioop
from .utils import ChatModule
from .views import assistant_config, get_history
from users.models import Assistant
from django.contrib.auth.models import User
from typing import Optional
from asgiref.sync import sync_to_async


load_dotenv()

def get_llm(model):
    api_key = os.getenv("OPENAI_API_KEY")


    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.5,
        max_retries=3
    )

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chat_module = ChatModule()

# Wrap the synchronous function
get_context_async = sync_to_async(chat_module.get_relevant_context, thread_sensitive=False)
get_assistant_config_async = sync_to_async(assistant_config, thread_sensitive=False)
get_history_async = sync_to_async(get_history, thread_sensitive=False)

# Fetch the audio file and convert it to a base64 encoded string
url = "https://openaiassets.blob.core.windows.net/$web/API/docs/audio/alloy.wav"
response = requests.get(url)
response.raise_for_status()
wav_data = response.content
encoded_string = base64.b64encode(wav_data).decode('utf-8')


class VoiceAssistantConsumer(AsyncWebsocketConsumer):
    # MODEL_NAME = "gpt-4o-mini-audio-preview"
    # MODEL_NAME = "gpt-4o-mini-audio-preview-2024-12-17"
    MODEL_NAME = "gpt-4o-mini-audio-preview"
    VOICE_ID = "alloy"
    AUDIO_FORMAT = "pcm16"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_data = None
        try:
            self.llm = get_llm(self.MODEL_NAME)
        except Exception as e:
            print(f"Error initializing LLM: {str(e)}")
            self.llm = None

    async def connect(self):
        """
        Called when the websocket is handshaking.
        """
        await self.accept()
        await self.send(
            json.dumps({"type": "system", "message": "Connected to Voice Assistant."})
        )

    async def disconnect(self, close_code):
        """
        Called when websocket closes.
        """
        pass

    async def receive(self, text_data=None, bytes_data=None):
        """
        Called whenever the client sends something over WebSocket.
        """
        if text_data:
            data = json.loads(text_data)
            query = ""
            assistant_id = "e74ea4ce-da6e-4c2e-befa-99132fc76876"
            user_id = "21"
            # "control" signals the beginning of conversation
            if data.get("control") == "start_conversation":
                await self.send_greeting()

            # "audio_data" => user has sent base64 WAV for STT
            elif "audio_data" in data:
                await self.get_response_from_audio(
                    audio_data_b64=data["audio_data"],
                    query=query,
                    assistant_id=assistant_id,
                    user_id=user_id
                )

            # "transcript" => user typed or recognized text
            elif "transcript" in data:
                await self.get_chat_response(data["transcript"])

    async def send_greeting(self):
        """
        Sends an initial text greeting (no TTS, since we can't do openai.Audio.speech).
        """
        greeting = "Hello! How can I assist you today?"
        await self.send(
            json.dumps(
                {
                    "type": "assistant_response",
                    "message": greeting,
                    "audio_data": None,  # No TTS here
                }
            )
        )

    async def get_response_from_audio(self, audio_data_b64, query: Optional[str], assistant_id: Optional[str], user_id: Optional[str]):

        get_context = await get_context_async(query=query, assistant_id=assistant_id)

        assistant_config_data = await get_assistant_config_async(assistant_id, user_id)

        print(f"\n\n Assistant Config Data: {assistant_config_data}\n\n")

        chat_history = await get_history_async(assistant_id=assistant_id, user_id=user_id)


        print(f"Chat history in Consumers: {chat_history}")

        chat_summary = next(
                (entry["summary"] for entry in chat_history if "summary" in entry),
                "No summary available. Use chat history only to generate chat summary."
            )

        system_message = f"""
        You are an adaptive AI educator specializing in {assistant_config_data.get('topic')} in {assistant_config_data.get('subject')}. Your role is to:
        1. **Analyze the user's query first** and tailor your response accordingly, considering context, user history, and knowledge level.
        2. Explain the user's query clearly and thoroughly using the provided **context**.
        3. Adapt explanations and exercises based on user feedback and knowledge level (beginner, intermediate, advanced).
        4. Apply the following **teacher instructions**: {assistant_config_data.get('teacher_instructions')}.
        5. Generate exercises based on the following criteria:
        - After each explanation, explicitly ask "Do you understand this explanation?" or "Would you like me to clarify anything?"
        - If the user confirms understanding (e.g., "yes", "I understand", "that's clear"), automatically proceed to provide relevant exercises
        - If the user asks for clarification, provide additional explanation before moving to exercises
        - If the user modifies the query, adjust the explanation and exercises accordingly
        6. Allow the user to submit questions or exercise solutions via text, image, or file upload.
        7. **Do not use notes in the responses**.

        ## Teaching Strategy (Guided by Teacher Instructions):
        - Use pedagogical approaches as defined by the teacher instructions provided.
        - Tailor explanations and exercises to suit the user's understanding and goals.
        - Focus on engaging and effective teaching methods as per the teacher's approach.

        ## Exercise Generation Protocol:
        1. After confirmation of understanding:
        - For beginners: Provide 1-2 foundational exercises focusing on basic concepts
        - For intermediate users: Offer 2-3 scenario-based exercises with increasing complexity
        - For advanced users: Present 1-2 complex real-world problems or case studies
        2. Structure each exercise with:
        - Clear problem statement
        - Expected learning outcome
        - Hints (optional, based on difficulty level)
        - Solution submission instructions
        3. Always include a clear transition phrase like "Now that you understand, let's practice with these exercises:"

        ## Diagram Usage (Mermaid):
        - If applicable, use **Mermaid diagrams** for visualizing non-textual concepts like processes or structures.
        - Only include diagrams when a visual representation adds clarity.
        - Do not explicitly mention "Mermaid" or the tool unless necessary.

        ## Interaction Flow:
        1. **Analyze and Explain**:
            - Process the user's query (including image/file content if provided)
            - Provide thorough explanation using context (without directly including it)
            - Explicitly check for understanding
        2. **Exercise Delivery**:
            - After user confirms understanding or change the topic or query, automatically transition to exercises
            - Include clear submission instructions
            - Accept solutions via text, image, or file
        3. **Solution Review**:
            - Analyze submitted solutions
            - Provide detailed feedback
            - Offer follow-up exercises if needed

        ## Contextual Inputs:
        - **Provided Context**: {get_context} (strictly use this context to generate responses. If the query is unrelated to the context, please respond with a polite message stating that you lack knowledge about the query and **do not use context in the final response**).
        - **Chat Summary**: {chat_summary} (to assess learning progress and knowledge level, but do **not** include or reference the chat history in final response).
        - **Prompt Instructions**: {assistant_config_data.get('prompt_instructions')} (use these to guide the response generation, but do **not** include them in the final answer).

        Focus on maintaining a clear flow: explanation → understanding check → exercise generation → solution review. Always proceed to exercises after confirmed understanding.
        """


        try:
            completion = client.chat.completions.create(
                model=self.MODEL_NAME,
                modalities=["text", "audio"],
                audio={"voice": 'alloy', "format": self.AUDIO_FORMAT},
                stream=True,
                temperature=0.5,
                stream_options={"include_usage": True},
                max_tokens=1000,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_data_b64,
                                    "format": "wav"
                                }
                            }
                        ]
                    },
                ]
            )

            # Extracting text and audio chunks
            for chunk in completion:
                print(f"chunk: {chunk}")
                
                # Safely check if chunk has choices
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                    
                print(f"chunk.choices[0].delta: {chunk.choices[0].delta}")
                
                # Safely access delta and audio attributes
                delta = chunk.choices[0].delta
                if not delta:
                    continue
                    
                text_chunk = None
                audio_chunk = None
                
                if hasattr(delta, 'audio') and delta.audio:
                    print(f"delta.audio.transcript: {delta.audio.get('transcript')}")
                    if delta.audio.get('transcript'):
                        text_chunk = delta.audio.get('transcript')
                    if delta.audio.get('data'):
                        audio_chunk = base64.b64decode(delta.audio.get('data'))
                        audio_chunk = base64.b64encode(audio_chunk).decode('utf-8')
                        
                        # Only write if we have audio data
                        with open("audio.pcm", "ab") as f:
                            f.write(base64.b64decode(delta.audio.get('data')))
                # Only send if we have actual content
                if text_chunk or audio_chunk:
                    await self.send(
                        json.dumps({
                            "type": "assistant_response", 
                            "message": text_chunk,
                            # Only send audio_data if we have it
                            "audio_data": audio_chunk if audio_chunk else None,
                            "id": chunk.id
                        })
                    )
        except Exception as e:
            error_message = f"Error processing audio: {str(e)}"
            await self.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": error_message,
                        "audio_data": None,
                    }
                )
            )


