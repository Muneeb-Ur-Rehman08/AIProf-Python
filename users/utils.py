from app.modals.chat import get_llm
from venv import logger
from typing import Any, Generator

from langchain.schema import HumanMessage, AIMessage

import json
import time


def generate_instruction_stream(
    subject: str, 
    topic: str, 
    current_instructions: str,
    description: str
) -> Generator[Any, Any, Any]:
    """
    Generator function to stream instruction generation process
    
    Args:
        subject: The subject of the assistant
        topic: The specific topic
        current_instructions: Existing instructions
    
    Yields:
        Streaming JSON responses with generation status
    """
    try:
        # Yield initial status
        yield json.dumps({
            'status': 'start', 
            'message': 'Starting instruction generation...'
        }) + '\n'

        # Simulate initial processing stages
        time.sleep(0.5)
        yield json.dumps({
            'status': 'progress', 
            'message': 'Analyzing subject and topic context...'
        }) + '\n'

        # Langchain Setup
        llm = get_llm()

        # Construct detailed prompt
        full_prompt = f"""
        Context:
        - Subject: {subject}
        - Topic: {topic}
        - Description: {description}
        - Current Instructions: {current_instructions}

        Generate comprehensive AI assistant instructions that:
        1. Capture the educational essence of the subject
        2. Provide clear, adaptive communication guidelines
        3. Ensure pedagogically sound interaction
        4. Create a framework for engaging and effective learning

        Focus on:
        - Precise communication strategies
        - Subject-specific explanation techniques
        - Adaptive learning support
        - Motivation and engagement methods

        Generated Instructions:
        """

        # Initialize message 
        messages = [HumanMessage(content=full_prompt)]
        
        # Track full generated content
        full_content = ""
        
        # Stream generation process
        for chunk in llm.stream(messages):
            if chunk.content:
                full_content += chunk.content
                
                # Yield partial content
                yield json.dumps({
                    'status': 'generating',
                    'partial_content': chunk.content
                }) + '\n'
        
        # Final yield with complete instructions
        yield json.dumps({
            'status': 'complete',
            'full_content': full_content
        }) + '\n'

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield json.dumps({
            'status': 'error',
            'message': str(e)
        }) + '\n'