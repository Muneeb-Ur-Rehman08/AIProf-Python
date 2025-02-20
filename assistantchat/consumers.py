import json
from channels.generic.websocket import AsyncWebsocketConsumer
from langchain_openai import ChatOpenAI
import os
import base64
from openai import OpenAI
import requests
from dotenv import load_dotenv
from .utils import ChatModule
from .views import assistant_config, get_history
from users.models import Assistant
from django.contrib.auth.models import User
from typing import Optional
from asgiref.sync import sync_to_async
from .views import save_history


load_dotenv()


def get_llm(model):
    api_key = os.getenv("OPENAI_API_KEY")

    return ChatOpenAI(api_key=api_key, model=model, temperature=0.5, max_retries=3)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chat_module = ChatModule()

# Wrap the synchronous function
get_context_async = sync_to_async(
    chat_module.get_relevant_context, thread_sensitive=False
)
get_assistant_config_async = sync_to_async(assistant_config, thread_sensitive=False)
get_history_async = sync_to_async(get_history, thread_sensitive=False)
save_history_async = sync_to_async(save_history, thread_sensitive=False)

class VoiceAssistantConsumer(AsyncWebsocketConsumer):
    MODEL_NAME = "gpt-4o-mini-audio-preview"
    # MODEL_NAME = "gpt-4o-mini-audio-preview-2024-12-17"
    # MODEL_NAME = "gpt-4o-audio-preview"
    VOICE_ID = "alloy"
    AUDIO_FORMAT = "pcm16"



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_buffer = bytes()
        self.vad_state = {
            "speech_detected": False,
            "last_active": None,
            "sample_rate": 16000,  # Silero VAD required sample rate
        }
        self.is_playing = False

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
            # assistant_id = "e74ea4ce-da6e-4c2e-befa-99132fc76876"
            # user_id = "21"
            # "control" signals the beginning of conversation
            if data.get("control") == "start_conversation":
                await self.send_greeting()

            # "audio_data" => user has sent base64 WAV for STT
            elif "audio_data" in data:
                await self.get_response_from_audio(
                    audio_data_b64=data["audio_data"],
                    query=query,
                    assistant_id=data["assistant_id"],
                    user_id=data["user_id"]
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

    async def get_response_from_audio(
        self,
        audio_data_b64,
        query: Optional[str],
        assistant_id: Optional[str],
        user_id: Optional[str],
    ):
        # Decode and process audio
        audio_data = base64.b64decode(audio_data_b64)
        self.audio_buffer += audio_data

        # Convert to VAD-compatible format
        audio_np = self._convert_audio_to_vad_format()

        # Retry speech detection up to 3 times for better accuracy
        for _ in range(3):  
            speech_confirmed = await self._detect_speech(audio_np)
            if speech_confirmed:
                break
            await asyncio.sleep(0.1)  # Small delay before retrying
        
        print(f"Final speech confirmation: {speech_confirmed}")

        if speech_confirmed:
            # Process full question with existing OpenAI flow
            await self._process_confirmed_question(
                audio_data_b64, assistant_id, user_id, query
            )
        else:
            await self.send(
                json.dumps(
                    {
                        "type": "vad_status",
                        "message": "Listening...",
                        "status": "waiting_for_speech",
                    }
                )
            )


    def _convert_audio_to_vad_format(self):
        # Convert webm/wav to raw PCM
        try:
            audio = AudioSegment.from_file(
                io.BytesIO(self.audio_buffer), 
                format="wav"  # Explicitly specify WAV format
            )
            print(f"Original audio info - Channels: {audio.channels}, Frame rate: {audio.frame_rate}, Duration: {len(audio)}ms")
            
            audio = audio.set_frame_rate(self.vad_state["sample_rate"]).set_channels(1)
            print(f"Converted audio info - Channels: {audio.channels}, Frame rate: {audio.frame_rate}, Duration: {len(audio)}ms")
            
            samples = np.array(audio.get_array_of_samples())
            print(f"Audio samples - dtype: {samples.dtype}, shape: {samples.shape}, min: {np.min(samples)}, max: {np.max(samples)}")
            return samples
        except Exception as e:
            print(f"Error converting audio: {str(e)}")
            return np.array([])


    async def _detect_speech(self, audio_np):
        if len(audio_np) == 0:
            print("Audio array is empty. Skipping VAD detection.")
            return False

        try:
            print(f"VAD Input - dtype: {audio_np.dtype}, shape: {audio_np.shape}, min: {np.min(audio_np)}, max: {np.max(audio_np)}")
            
            # Convert numpy array to Torch tensor
            audio_tensor = torch.from_numpy(audio_np).float()
            
            # Run speech detection using optimized parameters
            timestamps = get_speech_timestamps(
                audio_tensor,
                model,
                threshold=0.4,
                min_speech_duration_ms=150,
                min_silence_duration_ms=300,
                window_size_samples=30,
            )

            print(f"Raw VAD output: {timestamps}")
            print(f"Detected speech timestamps: {timestamps}")
            return len(timestamps) > 0
        except Exception as e:
            print(f"Error in VAD detection: {str(e)}")
            return False


    async def _process_confirmed_question(
        self, audio_data_b64, assistant_id, user_id, query
    ):
        
        if self.is_playing:
            await self.stop_audio_playback()    
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
        - If the user confirms understanding (e.g., "yes", "I understand", "that's clear"), automatically proceed to provide relevant exercises.
        - If the user asks for clarification, provide additional explanation before moving to exercises.
        - If the user modifies the query, adjust the explanation and exercises accordingly.
        6. Allow the user to submit questions or exercise solutions via text, image, or file upload.
        7. **Do not use notes in the responses**.

        ## Teaching Strategy (Guided by Teacher Instructions):
        - Use pedagogical approaches as defined by the teacher instructions provided.
        - Tailor explanations and exercises to suit the user's understanding and goals.
        - Focus on engaging and effective teaching methods as per the teacher's approach.

        ## Exercise Generation Protocol:
        1. After confirmation of understanding:
        - For beginners: Provide 1-2 foundational exercises focusing on basic concepts.
        - For intermediate users: Offer 2-3 scenario-based exercises with increasing complexity.
        - For advanced users: Present 1-2 complex real-world problems or case studies.
        2. Structure each exercise with:
        - Clear problem statement.
        - Expected learning outcome.
        - Hints (optional, based on difficulty level).
        - Solution submission instructions.
        3. Always include a clear transition phrase like "Now that you understand, let's practice with these exercises:".

        ## Diagram Usage (Mermaid):
        - If applicable, use **Mermaid diagrams** for visualizing non-textual concepts like processes or structures.
        - Only include diagrams when a visual representation adds clarity.
        - Do not explicitly mention "Mermaid" or the tool unless necessary.

        ## Interaction Flow:
        1. **Analyze and Explain**:
            - Process the user's query (including image/file content if provided).
            - Provide thorough explanation using context (without directly including it).
            - Explicitly check for understanding.
        2. **Exercise Delivery**:
            - After user confirms understanding or changes the topic/query, automatically transition to exercises.
            - Include clear submission instructions.
        3. **Solution Review**:
            - Analyze submitted solutions.
            - Provide detailed feedback.
            - Offer follow-up exercises if needed.

        ## Contextual Inputs:
        - **Provided Context**: {get_context} (strictly use this context to generate responses. If the query is unrelated to the context, please respond with a polite message stating that you lack knowledge about the query and **do not use context in the final response**).
        - **Chat Summary**: {chat_summary} (to assess learning progress and knowledge level, but do **not** include or reference the chat history in final response).
        - **Prompt Instructions**: {assistant_config_data.get('prompt_instructions')} (use these to guide the response generation, but do **not** include them in the final answer).

        Focus on maintaining a clear flow: explanation → understanding check → exercise generation → solution review. Always proceed to exercises after confirmed understanding.
        """

        try:

            # Now that the old audio is stopped, process the new response
            self.is_playing = True
            
            
            completion = client.chat.completions.create(
                model=self.MODEL_NAME,
                modalities=["text", "audio"],
                audio={"voice": 'alloy', "format": self.AUDIO_FORMAT},
                stream=True,
                temperature=0.5,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": system_message},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_data_b64,
                                    "format": "wav",
                                },
                            }
                        ],
                    },
                ],
            )

            import re
            # Initialize buffers for text and audio accumulation.
            buffer_text = ""
            buffer_audio = b""

            for chunk in completion:

                # Safely check for choices and the delta attribute.
                if not chunk.choices or len(chunk.choices) == 0:
                    continue

                delta = chunk.choices[0].delta
                if not delta:
                    continue

                text_chunk = ""
                # Process audio: check if a transcript is provided and audio data is available.
                if hasattr(delta, 'audio') and delta.audio:
                    transcript_piece = delta.audio.get('transcript')
                    if transcript_piece:
                        text_chunk = transcript_piece
                    audio_piece = delta.audio.get('data')
                    if audio_piece:
                        # Decode and accumulate audio binary data.
                        audio_binary = base64.b64decode(audio_piece)
                        buffer_audio += audio_binary

                # Accumulate text if available.
                if text_chunk:
                    buffer_text += text_chunk

                    # Check for sentence boundaries using regex.
                    # This splits the buffered text into sentences based on ending punctuation (.?!).
                    sentences = re.split(r'(?<=[.!?])\s+', buffer_text)
                    # If there is at least one full sentence (i.e. more than one segment) or
                    # the entire buffer ends with a sentence-ending punctuation, send the completed sentences.
                    if len(sentences) > 1 or buffer_text.endswith(('.', '?', '!')):
                        # If the buffer does not end with punctuation then the last segment is incomplete.
                        complete_sentences = sentences[:-1] if not buffer_text.endswith(('.', '?', '!')) else sentences
                        for sent in complete_sentences:
                            # Aggregate audio (if available) into a base64-encoded string.
                            audio_base64 = base64.b64encode(buffer_audio).decode("utf-8") if buffer_audio else None
                            await self.send(json.dumps({
                                "type": "assistant_response",
                                "message": sent,
                                "audio_data": audio_base64,
                                "id": chunk.id
                            }))
                        # Retain any incomplete sentence in the buffer and reset the audio buffer.
                        buffer_text = sentences[-1] if len(sentences) > 1 else ""
                        buffer_audio = b""

            # Flush any remaining text or audio after the stream completes.
            if buffer_text or buffer_audio:
                audio_base64 = base64.b64encode(buffer_audio).decode("utf-8") if buffer_audio else None
                await self.send(json.dumps({
                    "type": "assistant_response",
                    "message": buffer_text,
                    "audio_data": audio_base64,
                    "id": chunk.id  # using the last chunk's id or a new unique identifier
                }))

        except Exception as e:
            error_message = f"Error processing audio: {str(e)}"
            await self.send(json.dumps({
                "type": "error",
                "message": error_message,
                "audio_data": None,
            }))


    async def stop_audio_playback(self):
        """
        Notify the client to stop the current audio playback.
        """
        await self.send(
            json.dumps({
                "type": "audio_control",
                "message": "stop_audio",  # Message to stop audio
                "status": "stop",
            })
        )