import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
import speech_recognition as sr
from io import BytesIO
import wave

logger = logging.getLogger(__name__)

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connection attempt")
        try:
            await self.accept()
            logger.info("WebSocket connection accepted")
            await self.send(text_data=json.dumps({
                'message': 'Connected to voice assistant. You can start speaking.',
                'role': 'system'
            }))
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, bytes_data=None, text_data=None):
        try:
            if bytes_data:
                # Convert audio data to text
                text = await self.process_audio(bytes_data)
                if text:
                    await self.send(text_data=json.dumps({
                        'message': f'You said: {text}',
                        'role': 'user'
                    }))
                    
                    # Here you can process the text with your chat system
                    # For now, we'll just echo it back
                    response = f"I heard you say: {text}"
                    await self.send(text_data=json.dumps({
                        'message': response,
                        'role': 'assistant'
                    }))
            elif text_data:
                logger.info(f"Received text message: {text_data}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'message': 'Error processing audio',
                'role': 'system'
            }))

    async def process_audio(self, audio_data):
        try:
            # Convert the audio data to WAV format
            audio_file = BytesIO(audio_data)
            
            # Use speech recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)
                return text
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return None 