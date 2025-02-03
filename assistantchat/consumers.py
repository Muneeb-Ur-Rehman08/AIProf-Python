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
import audioop
def get_llm(model):
    api_key = os.environ.get("OPENAI_API_KEY")
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.5,
        max_retries=3
    )

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# Fetch the audio file and convert it to a base64 encoded string
url = "https://openaiassets.blob.core.windows.net/$web/API/docs/audio/alloy.wav"
response = requests.get(url)
response.raise_for_status()
wav_data = response.content
encoded_string = base64.b64encode(wav_data).decode('utf-8')


class VoiceAssistantConsumer(AsyncWebsocketConsumer):
    # MODEL_NAME = "gpt-4o-mini-audio-preview"
    # MODEL_NAME = "gpt-4o-mini-audio-preview-2024-12-17"
    MODEL_NAME = "gpt-4o-audio-preview"
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
            # "control" signals the beginning of conversation
            if data.get("control") == "start_conversation":
                await self.send_greeting()

            # "audio_data" => user has sent base64 WAV for STT
            elif "audio_data" in data:
                await self.get_response_from_audio(data["audio_data"])

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

    async def get_response_from_audio(self, audio_data_b64):
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
                        "content": """
                        You are a friendly and helpful voice assistant focused on clear communication. Your responses should be:
                        - Concise and to the point (5-10 seconds of audio by default)
                        - Natural and conversational in tone
                        - Well-structured with clear transitions
                        - Longer only when the user specifically requests more detail
                        
                        Guidelines:
                        - Start responses with a direct answer
                        - Use simple language and short sentences
                        - Include brief acknowledgments when appropriate
                        - Maintain a consistent, friendly voice
                        - Ask clarifying questions if needed
                        
                        Remember: The goal is to provide helpful information efficiently while maintaining a natural conversation flow.
                        """
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



