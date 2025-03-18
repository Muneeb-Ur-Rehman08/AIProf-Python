from django.db import models, transaction
from users.models import SupabaseUser, Assistant
from django.contrib.auth.models import User
import uuid
import logging
# Create your models here.

# Initialize logger
logger = logging.getLogger(__name__)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    
    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        db_column="user_id",
        to_field='id'
        
    )
    
    assistant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE,
        db_column="assistant_id",
        to_field='id'
        
        )
    prompt = models.TextField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    conversation_id = models.UUIDField(unique=False, default=uuid.uuid4)

    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-created_at']  # Order by most recent first


    def __str__(self):
        """
        String representation of the conversation.
        Shows assistant name and creation date.
        """
        return f"Conversation with {self.assistant_id.name} on {self.created_at}"



    def save(self, *args, **kwargs):
        """
        Override save method to increment assistant interactions
        when a new conversation is created.
        """
        # Check if this is a new conversation entry
        is_new = self._state.adding  # This ensures it checks if it's new before saving
        
        try:
            # Use a transaction to ensure both the conversation save and the assistant interaction update succeed
            with transaction.atomic():
                # Save the conversation first
                super().save(*args, **kwargs)
                
                # If this is a new conversation, increment the assistant's interactions
                if is_new and self.assistant_id:
                    try:
                        logger.info(f"Attempting to increment interactions for assistant {self.assistant_id.id}")
                        
                        # Lock the assistant row for updates
                        assistant = Assistant.objects.select_for_update().get(id=self.assistant_id.id)
                        
                        # Increment interactions, default to 1 if None
                        current_interactions = assistant.interactions or 0
                        assistant.interactions = current_interactions + 1
                        
                        # Save the updated assistant
                        assistant.save()
                        
                        logger.info(f"Interactions incremented for assistant {self.assistant_id.id}: {assistant.interactions}")
                    
                    except Assistant.DoesNotExist:
                        # Log the error with detailed information
                        logger.error(
                            f"Failed to increment interactions: Assistant with ID {self.assistant_id.id} does not exist. "
                            f"Conversation ID: {self.id}"
                        )
                    except Exception as e:
                        # Log any other unexpected errors
                        logger.error(
                            f"Unexpected error incrementing assistant interactions: {str(e)}. "
                            f"Assistant ID: {self.assistant_id.id}, Conversation ID: {self.id}"
                        )
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")


class AssistantNotes(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        db_column="user_id",
        to_field='id'
        
    )
    
    assistant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE,
        db_column="assistant_id",
        to_field='id'
        
        )
    question = models.TextField(blank=True, null=True)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)



class KnowledgeAssessment(models.Model):
    """
    Model to store user knowledge assessments for different assistants and subjects
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_assessments')
    assistant = models.ForeignKey(Assistant, on_delete=models.CASCADE, related_name='knowledge_assessments')
    
    # Assessment metadata
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=100)
    
    # Knowledge level assessment
    knowledge_level = models.CharField(
        max_length=20, 
        choices=[
            ('unassessed', 'Unassessed'),
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'), 
            ('advanced', 'Advanced')
        ],
        default='unassessed'
    )
    
    # Diagnostic questions and user's responses
    diagnostic_questions = models.JSONField(null=True, blank=True)
    user_answers = models.JSONField(null=True, blank=True)
    
    # Assessment score and insights
    assessment_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    assessment_insights = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'assistant', 'subject', 'topic')
        verbose_name_plural = 'Knowledge Assessments'
    
    def __str__(self):
        return f"{self.user.username}'s {self.subject} Assessment for {self.assistant.name}"
    
    def update_assessment(self, knowledge_level, score=None, insights=None, answers=None):
        """
        Method to update the assessment with new results
        """
        self.knowledge_level = knowledge_level
        if score is not None:
            self.assessment_score = score
        if insights is not None:
            self.assessment_insights = insights
        if answers is not None:
            self.user_answers = answers
        self.save()



class Quiz(models.Model):
    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        db_column="user_id",
        to_field='id'
        
    )
    
    assistant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE,
        db_column="assistant_id",
        to_field='id'
        
        )
    context = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz for {self.assistant} - {self.created_at}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_answer = models.CharField(max_length=1)  # 'A', 'B', 'C', or 'D'

    def __str__(self):
        return self.question_text[:50]

class QuizAttempt(models.Model):
    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        db_column="user_id",
        to_field='id'
        
    )
    
    assistant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE,
        db_column="assistant_id",
        to_field='id'
        
        )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    total_correct = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def calculate_score(self):
        total_questions = self.questionattempt_set.count()
        if total_questions == 0:
            return 0
        return (self.total_correct / total_questions) * 100

class QuestionAttempt(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1)  # 'A', 'B', 'C', or 'D'
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)