from django.db import models
from users.models import SupabaseUser, Assistant
from django.contrib.auth.models import User
import uuid
# Create your models here.


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
