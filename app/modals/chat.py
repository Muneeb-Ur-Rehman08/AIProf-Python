import os

from groq import Groq
from app.modals.anon_conversation import fetch_conversation_history  # Updated import
from app.utils.prompts import get_system_instruction

def get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    return Groq(api_key=api_key)

def get_chat_completion(conversation_history, message_content):
    print('get_chat_completion')
    # Retrieve the API key from the environment variable
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    
    llm =  get_llm()

    try:
        # Prepare the messages for the LLM, including the conversation history
        messages = [
            {"role": "system", "content": get_system_instruction()}
        ] + (conversation_history or []) + [
            {
                "role": "user",
                "content": message_content,
            }
        ]

        chat_completion = llm.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
            stream=True,
            max_tokens=1000,
        )
        
        # Yield each part of the streamed response
        for response in chat_completion:
            content = response.choices[0].delta.content
            if content is not None:
                yield content

    except Exception as e:
        raise RuntimeError(f"Failed to get chat completion: {e}")



def get_chat_completion_with_conversation_id(conversation_id, message_content, conversation_history):
    print('get_chat_completion_with_conversation_id')
    if not conversation_id:
        raise ValueError("conversation_id is required")
    
    return get_chat_completion(conversation_history, message_content=message_content)


