import asyncio
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
import os

load_dotenv()


async def entrypoint(ctx: JobContext):
    initial_context = llm.ChatContext().append(
        role="system",
        text=("You are a voice assistant created by AI Prof. Your interface with users will be through voice. "
        "You should use short and concise responses, and avoid usage of unpronouncable punctuation.")
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_context,
    )

    assistant.start(ctx.room)

    await asyncio.sleep(1)
    await assistant.say("Hello, how can I help you today?", allow_interruptions=True)



if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint,))



