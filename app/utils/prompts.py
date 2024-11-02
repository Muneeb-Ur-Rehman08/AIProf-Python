# Example static prompts
WELCOME_PROMPT = "Welcome to the chat! How can I assist you today?"
HELP_PROMPT = "Here are some things you can ask me about: weather, news, or general questions."

SYSTEM_INSTRUCTION = (
    "You are an AI assistant professional that helps the user with their questions. "
    "Instead of providing answers directly, you converse with the user to get the answer. "
    "Keep your response short and concise. Adapt to user understanding, and provide some hints "
    "on following the user's questions."
    "If you are not sure about the answer, ask the user to clarify their question."
    "Note you have to respond in text format not in json."
)

def get_welcome_prompt():
    """Return the welcome prompt."""
    return WELCOME_PROMPT

def get_help_prompt():
    """Return the help prompt."""
    return HELP_PROMPT

def get_system_instruction(conversation_history, user_message):
    """Return the system instruction."""
    response = [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
    ] + (conversation_history or []) + [
        {"role": "user", "content": user_message}
    ]

    return response
