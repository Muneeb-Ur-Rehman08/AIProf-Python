import os

from langchain_groq import ChatGroq
from app.modals.anon_conversation import fetch_conversation_history
from app.utils.prompts import get_system_instruction

def get_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    return ChatGroq(
        api_key=api_key,
        model="llama3-8b-8192",
        temperature=0.5,
        max_retries=3
    )

def get_chat_completion(conversation_history, message_content):
    print('get_chat_completion')
    # Retrieve the API key from the environment variable
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")
    
    llm = get_llm()

    try:
        # Prepare the messages for the LLM, including the conversation history
        messages = get_system_instruction(conversation_history, message_content)

        chat_completion = llm.stream(messages)
        
        # Yield each part of the streamed response
        for response in chat_completion:
            content = response.content
            if content is not None:
                yield content

    except Exception as e:
        raise RuntimeError(f"Failed to get chat completion: {e}")



def get_chat_completion_with_conversation_id(conversation_id, message_content, conversation_history):
    print('get_chat_completion_with_conversation_id')
    if not conversation_id:
        raise ValueError("conversation_id is required")
    
    return get_chat_completion(conversation_history, message_content=message_content)


