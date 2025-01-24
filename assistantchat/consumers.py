import json
from channels.generic.websocket import AsyncWebsocketConsumer
import openai
import os
import base64
import tempfile
from openai import OpenAI

openai.api_key = os.getenv("OPENAI_API_KEY")

class VoiceAssistantConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(json.dumps({"type": "system", "message": "Connected to Voice Assistant."}))
        self.client = OpenAI()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)

            if data.get("control") == "start_conversation":
                await self.send_greeting()
            elif "audio_data" in data:
                await self.process_audio_data(data["audio_data"])
            elif "transcript" in data:
                await self.get_assistant_response(data["transcript"])

    async def send_greeting(self):
        greeting = "Hello! How can I assist you today?"
        audio_data = await self.text_to_speech(greeting)
        await self.send(json.dumps({"type": "assistant_response", "message": greeting, "audio_data": audio_data}))

    async def process_audio_data(self, audio_base64):
        audio_bytes = base64.b64decode(audio_base64)
        with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            transcription = await self.transcribe_audio(audio_base64)

        if transcription:
            await self.send(json.dumps({"type": "transcription", "text": transcription}))
            await self.get_assistant_response(transcription)
        else:
            await self.send(json.dumps({"type": "system", "message": "No speech detected."}))

    async def transcribe_audio(self, audio_data):
        try:
            # Create a temporary file with delete=False to ensure we can close it before reading
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                temp_path = temp_file.name
                # Write the decoded audio data
                temp_file.write(base64.b64decode(audio_data))
            
            # Now read the file for transcription
            try:
                with open(temp_path, "rb") as audio_file:
                    transcript = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                return transcript.text
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            print(f"Error in transcribe_audio: {str(e)}")
            return None

    async def get_assistant_response(self, user_text):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_text}],
                temperature=0.7
            )
            # Access the message content correctly from the response object
            message = response.choices[0].message.content
            audio_data = await self.text_to_speech(message)
            await self.send(json.dumps({
                "type": "assistant_response", 
                "message": message, 
                "audio_data": audio_data
            }))
        except Exception as e:
            print(f"Error in get_assistant_response: {str(e)}")
            await self.send(json.dumps({
                "type": "system",
                "message": f"Error: {str(e)}"
            }))

    async def text_to_speech(self, text):
        speech_response = self.client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=text
        )
        return base64.b64encode(speech_response.content).decode("utf-8")
