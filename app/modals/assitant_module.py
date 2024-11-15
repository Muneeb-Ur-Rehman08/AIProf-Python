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
    Signature for assistant operations with chain of thought reasoning.

    Args:
        subject (str): The subject area being taught.
        context (str): Content used as relevant context to query from the knowledge base.
        query (str): The query or concept to process.
        teaching_instructions (str): Teaching instructions used for how to responding to the query.
    """
    subject = dspy.InputField(description="The subject area being taught")
    context = dspy.InputField(description="Content used as relevant context to query from the knowledge base")
    query = dspy.InputField(description="The query or concept to process")
    teaching_instructions = dspy.InputField(description="Teaching instructions used for how to responding to the query")
    
    # reasoning_chain = dspy.OutputField(description="Chain of thought reasoning steps")
    answer = dspy.OutputField(description="Generate complete answer of the query, from given relevant context follow the teaching_instructions.")
    # examples = dspy.OutputField(description="List of relevant examples")

    

class AssistantModule(dspy.Module):
    """
    DSPy module for assistant operations.
    """

    def __init__(self):
        """
        Initializes the AssistantModule with a predict function.
        """
        super().__init__()
        self.explain = dspy.Predict(AssistantSignature)

    def forward(self,
                input_data: AssistantInput
     ) -> Tuple[str, List[str]]:
        """
        Generates a response using the assistant module.
        
        Args:
            input_data (AssistantInput): The input data for the assistant module.
        
        Returns:
            Tuple[str, List[str]]: A tuple containing the explanation and examples (if any).
        """
        try:
            
            
            # Generate the response
            response = self.explain(
                context=input_data.context,
                subject=input_data.subject,
                query=input_data.query,
                teaching_instructions=input_data.teaching_instructions
            )
            print(response)

            # If the model returns an empty explanation or examples, use a default response
            explanation = response.answer or "I'm sorry, I don't have enough information to provide a detailed explanation. Could you please provide more context?"
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