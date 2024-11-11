import dspy
import logging
from typing import List, Tuple
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AssistantInput:
    """
    Represents the input data for the assistant module.
    
    Attributes:
        subject (str): The subject area of the query.
        context (str): The context in which the query is being asked.
        query (str): The specific question or topic to address.
        teaching_instructions (str): Guidelines for structuring and delivering the response.
    """

    subject: str
    context: str
    query: str
    teaching_instructions: str

class AssistantSignature(dspy.Signature):
    """
    Signature for educational assistant operations with enhanced context utilization.
    
    Attributes:
        subject (dspy.InputField): The specific academic or training subject area that frames the context of the response.
        context (dspy.InputField): Strictly use ONLY the provided context passages to answer the query.
        query (dspy.InputField): The specific question or topic to address.
        teaching_instructions (dspy.InputField): Specific pedagogical guidelines that define how to structure and deliver the response.
        explanation (dspy.OutputField): Provide a clear, structured and comprehensive explanation that addresses the query using only information from the provided context.
    """

    subject = dspy.InputField(
        description="The specific academic or training subject area that frames the context of the response."
        "Use this to tailor explanations and examples to the appropriate field and difficulty level."
    )

    context = dspy.InputField(
        description="Strictly use ONLY the provided context passages to answer the query. "
        "Do not introduce external knowledge. "
        "If the context doesn't fully address the query, acknowledge the limitations. "
        "Synthesize information from multiple context passages when relevant. "
        "Always maintain accuracy to the source material."
    )

    query = dspy.InputField(
        description="The specific question or topic to address. "
        "Break down complex queries into key components. "
        "Ensure the response directly answers all aspects of the query. "
        "If the query is unclear, focus on the most relevant interpretation based on context."
    )

    teaching_instructions = dspy.InputField(
        description="Specific pedagogical guidelines that define how to structure and deliver the response. "
        "Follow these instructions precisely for tone, complexity level, and teaching approach. "
        "Adapt examples and explanations to match the specified teaching style. "
        "Maintain consistency with any defined learning objectives or methodologies."
    )

    explanation = dspy.OutputField(
        description="Provide a Complete, structured and comprehensive explanation that: "
        "1. Directly addresses the query using only information from the provided context\n"
        "2. Organizes ideas in a logical flow with clear transitions\n"
        "3. Uses appropriate terminology for the subject and audience level\n"
        "4. Includes relevant supporting details from the context\n"
        "5. Acknowledges any limitations in the available information\n"
        "6. Follows the specified teaching instructions for style and approach"
    )

    

class AssistantModule(dspy.Module):
    """
    DSPy module for assistant operations.
    """

    def __init__(self):
        """
        Initializes the AssistantModule with a predict function.
        """
        super().__init__()
        self.predict = dspy.Predict(AssistantSignature)

    def forward(self, input_data: AssistantInput) -> Tuple[str, List[str]]:
        """
        Generates a response using the assistant module.
        
        Args:
            input_data (AssistantInput): The input data for the assistant module.
        
        Returns:
            Tuple[str, List[str]]: A tuple containing the explanation and examples (if any).
        """
        try:
            # Generate the response
            prediction = self.predict(
                subject=input_data.subject,
                context=input_data.context,
                query=input_data.query,
                teaching_instructions=input_data.teaching_instructions
            )

            # If the model returns an empty explanation or examples, use a default response
            explanation = prediction.explanation or "I'm sorry, I don't have enough information to provide a detailed explanation. Could you please provide more context?"
            
            return explanation

        except Exception as e:
            logger.error(f"Error in AssistantModule: {e}")
            return "Unable to process query at this time.", []

    def process_query(self, input_data: AssistantInput) -> Tuple[str, List[str]]:
        """
        Async wrapper for processing queries.
        
        Args:
            input_data (AssistantInput): The input data for the assistant module.
        
        Returns:
            Tuple[str, List[str]]: A tuple containing the explanation and examples (if any).
        """
        try:
            return self.forward(input_data)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Unable to process query at this time.", []