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

def get_llm(model):
    api_key = os.environ.get("OPENAI_API_KEY")
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.5,
        max_retries=3
    )

client = OpenAI()


# Fetch the audio file and convert it to a base64 encoded string
url = "https://openaiassets.blob.core.windows.net/$web/API/docs/audio/alloy.wav"
response = requests.get(url)
response.raise_for_status()
wav_data = response.content
encoded_string = base64.b64encode(wav_data).decode('utf-8')


class VoiceAssistantConsumer(AsyncWebsocketConsumer):
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

    def convert_wav_to_pcm16(self, wav_base64):
        """
        Converts a base64 WAV file to PCM16 format for OpenAI API.
        """
        try:
            # Decode base64 to raw WAV bytes
            wav_bytes = base64.b64decode(wav_base64)

            # Read WAV file
            with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                pcm_data = wav_file.readframes(wav_file.getnframes())

            if sample_width != 2:
                raise ValueError("Audio must be 16-bit PCM")

            if channels > 1:
                # Convert stereo to mono (average channels)
                pcm_array = np.frombuffer(pcm_data, dtype=np.int16)
                pcm_array = pcm_array.reshape((-1, channels)).mean(axis=1).astype(np.int16)
                pcm_data = pcm_array.tobytes()

            return base64.b64encode(pcm_data).decode('utf-8')

        except Exception as e:
            print(f"Error converting WAV to PCM16: {e}")
            return None
        

    async def get_response_from_audio(self, audio_data_b64):
        try:

            pcm16_audio = self.convert_wav_to_pcm16(audio_data_b64)
            if not pcm16_audio:
                raise ValueError("Failed to convert audio to PCM16 format")
        
            completion = client.chat.completions.create(
                model=self.MODEL_NAME,
                modalities=["text", "audio"],
                audio={"voice": self.VOICE_ID, "format": self.AUDIO_FORMAT},
                stream=True,
                messages=[
                    {
                        "role": "system",
                        "content": """
                        you are a helpful assistant. who does short and concise answers. default audio response should be less 5 second unless user asks for more.
                        """
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": pcm16_audio,
                                    "format": self.AUDIO_FORMAT
                                }

                            }
                        ]
                    },
                ]
            )

            for chunk in completion:
                print(chunk)

            # transcript = completion.choices[0].message.audio.transcript
            # audio_data = completion.choices[0].message.audio.data

            # await self.send(
            #     json.dumps(
            #         {
            #             "type": "assistant_response",
            #             "message": transcript,
            #             "audio_data": audio_data,
            #         }
            #     )
            # )

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



