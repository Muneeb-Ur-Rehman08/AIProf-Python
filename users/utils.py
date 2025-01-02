from app.modals.chat import get_llm
from venv import logger
from typing import Any, Generator

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

import json
import time


def generate_instruction_stream(
    name: str,
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
        # full_prompt = f"""
        # Context:
        # - Subject: {subject}
        # - Topic: {topic}
        # - Description: {description}
        # - Current Instructions: {current_instructions}

        # Generate comprehensive AI assistant instructions that:
        # 1. Capture the educational essence of the subject
        # 2. Provide clear, adaptive communication guidelines
        # 3. Ensure pedagogically sound interaction
        # 4. Create a framework for engaging and effective learning

        # Focus on:
        # - Precise communication strategies
        # - Subject-specific explanation techniques
        # - Adaptive learning support
        # - Motivation and engagement methods

        # Generated Instructions:
        # """

        full_prompt = f"""
        Context:
        - Teacher: {name}
        - Subject: {subject}
        - Topic: {topic}
        - Description: {description}
        - Current Instructions: {current_instructions}

        Task:
        Use the above context to generate a thorough set of AI assistant instructions that:

        1. Capture the educational goals and essential concepts of the subject and topic.
        2. Provide clear, adaptive communication guidelines for different learning levels and styles.
        3. Incorporate pedagogically sound methods for knowledge scaffolding, feedback, and assessment.
        4. Outline a structured framework for engaging and effective learning experiences.

        Areas of Focus:
        - Clear, context-sensitive communication strategies
        - Subject-specific explanation techniques for deeper understanding
        - Adaptive support for different learner needs and paces
        - Motivational and engagement tactics to sustain learner interest

        Constraints & Requirements:
        - Output only the final instructions as plain text.
        - Do not include or restate the context in the output.
        - Integrate or refine any relevant parts of the current instructions where appropriate.
        - Instructions must be detailed enough to guide AI teaching, interactions, and learner support.
        - Exclude headings, markdown, disclaimers, or any extra explanations.

        Output Format:
        Provide only the instructions in plain text (with or without line breaks). No additional text or formatting is allowed.

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