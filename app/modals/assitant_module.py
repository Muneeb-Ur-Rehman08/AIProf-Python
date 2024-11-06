import dspy
import logging
from typing import List, Tuple
from dataclasses import dataclass


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AssistantInput:
    subject: str
    context: str
    query: str
    teaching_instructions: str 


# Define DSPy signatures for assistant operations
class AssistantSignature(dspy.Signature):
    """Signature for assistant operations"""
    subject = dspy.InputField(desc="The subject area being taught")
    context = dspy.InputField(desc="Relevant context from knowledge base")
    query = dspy.InputField(desc="The query or concept to process")
    teaching_instructions = dspy.InputField(desc="Teaching instructions")  # Renamed field
    
    explanation = dspy.OutputField(desc="Generated explanation or response")
    examples = dspy.OutputField(desc="List of relevant examples")


class AssistantModule(dspy.Module):
    """DSPy module for assistant operations"""
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(AssistantSignature)
    
    def forward(self, input_data: AssistantInput) -> Tuple[str, List[str]]:
        """Generate response using the assistant"""
        try:
            prediction = self.predict(
                subject=input_data.subject,
                context=input_data.context,
                query=input_data.query,
                teaching_instructions=input_data.teaching_instructions  # Using renamed field
            )
            
            # Convert output fields to appropriate format
            explanation = prediction.explanation if isinstance(prediction.explanation, str) else ""
            examples = prediction.examples if isinstance(prediction.examples, list) else []
            
            return explanation, examples
            
        except Exception as e:
            logger.error(f"Error in AssistantModule: {e}")
            return "Unable to process query at this time.", []
        