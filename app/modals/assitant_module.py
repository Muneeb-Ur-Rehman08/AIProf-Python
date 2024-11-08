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
    subject = dspy.InputField(description="The subject area being taught")
    context = dspy.InputField(description="Content used as relevant context from the knowledge base not to go outside from the knowledge base content provided to answer the query")
    query = dspy.InputField(description="The query or concept to process")
    teaching_instructions = dspy.InputField(description="Teaching instructions used for responding to the query should be restrict on the instructions")
    
    explanation = dspy.OutputField(description="Generated explanation or response")
    examples = dspy.OutputField(description="List of relevant examples")


class AssistantModule(dspy.Module):
    """DSPy module for assistant operations"""
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(AssistantSignature)
        
    
    def forward(self, input_data: AssistantInput, max_context_length: int = 2000) -> Tuple[str, List[str]]:
        """Generate response using the assistant"""
        try:
            # Preprocess the context
            context_sentences = self.preprocess_context(input_data.context, max_context_length)

            # Generate the response
            explanation, examples = self.generate_response(
                subject=input_data.subject,
                context=context_sentences,
                query=input_data.query,
                teaching_instructions=input_data.teaching_instructions
            )

            # If the model returns an empty explanation or examples, use a default response
            if not explanation:
                explanation = "I'm sorry, I don't have enough information to provide a detailed explanation. Could you please provide more context?"
            if not examples:
                examples = ["Unfortunately, I don't have any relevant examples to share. Please let me know if you have any other questions."]

            return explanation, examples
        except ValueError as e:
            logger.error(f"ValueError in AssistantModule: {e}")
            return "I'm sorry, I couldn't understand your query. Please try rephrasing it.", []
        except TypeError as e:
            logger.error(f"TypeError in AssistantModule: {e}")
            return "I'm sorry, there was an issue processing your request. Please check the input data and try again.", []
        except Exception as e:
            logger.error(f"Unexpected error in AssistantModule: {e}")
            return "Unable to process query at this time.", []

    def preprocess_context(self, context: List[str], max_length: int) -> List[str]:
        """Preprocess the context by splitting it into sentences and truncating if necessary"""
        # Split the context into sentences
        context_sentences = [sentence.strip() for doc in context for sentence in doc.split('.')]

        # Truncate the context if it exceeds the maximum length
        if sum(len(sentence) for sentence in context_sentences) > max_length:
            context_sentences = context_sentences[:max_length // 10]

        return context_sentences

    def generate_response(self, subject: str, context: List[str], query: str, teaching_instructions: str) -> Tuple[str, List[str]]:
        """Generate the explanation and examples based on the input data"""
        # Use the model to generate the explanation and examples
        explanation = self.predict(
            subject=subject,
            context=context,
            query=query,
            teaching_instructions=teaching_instructions
        )
        examples = self.predict(
            subject=subject,
            context=context,
            query=query,
            teaching_instructions=teaching_instructions
        )
        return explanation, examples
        
    
    async def process_query(self, input_data: AssistantInput) -> Tuple[str, List[str]]:
        """Async wrapper for processing queries"""
        try:
            return self.forward(input_data)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return "Unable to process query at this time.", []