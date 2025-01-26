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
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            # Create temporary file with .webm extension
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name
                
            try:
                transcription = await self.transcribe_audio(temp_audio_path)
                if transcription:
                    print(f"Transcription: {transcription}")
                    await self.send(json.dumps({"type": "transcription", "text": transcription}))
                    await self.get_assistant_response(transcription)
                else:
                    await self.send(json.dumps({"type": "system", "message": "No speech detected."}))
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except OSError:
                    pass
        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            await self.send(json.dumps({"type": "system", "message": "Error processing audio."}))

    async def transcribe_audio(self, audio_path):
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript.text
        except Exception as e:
            print(f"Error in transcribe_audio: {str(e)}")
            return None

    async def get_assistant_response(self, user_text):
        system_message = "You are a helpful assistant. You have to answer the user's question and provide a helpful response. Use always english language. You are a helpful assistant. You have to answer the user's question and provide a helpful response. Use always english language. Give short answers."
        try:
            # Remove await since client methods are synchronous
            stream = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_message}, {"role": "user", "content": user_text}],
                temperature=0.7,
                stream=True  # Enable streaming
            )

            accumulated_message = ""
            
            # Process each chunk as it arrives
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    accumulated_message += content
                    
                    # Send the chunk immediately to the frontend
                    await self.send(json.dumps({
                        "type": "assistant_stream",
                        "chunk": content
                    }))

            # After streaming is complete, generate and send the audio
            audio_data = await self.text_to_speech(accumulated_message)
            
            # Send the complete message with audio
            await self.send(json.dumps({
                "type": "assistant_response",
                "message": accumulated_message,
                "audio_data": audio_data
            }))

        except Exception as e:
            print(f"Error in get_assistant_response: {str(e)}")
            await self.send(json.dumps({
                "type": "system",
                "message": f"Error: {str(e)}"
            }))

    async def text_to_speech(self, text):
        # Remove await since client methods are synchronous
        speech_response = self.client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=text
        )
        return base64.b64encode(speech_response.content).decode("utf-8")
