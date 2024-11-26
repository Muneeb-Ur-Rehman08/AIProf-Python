from django.db import models
from users.models import SupabaseUser, Assistant
import uuid
# Create your models here.


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    users_id = models.ForeignKey(
        SupabaseUser,
        on_delete=models.CASCADE,
        db_column='users_id',
        to_field='id',
        null=False,
        blank=False,
        default=uuid.uuid4,
        db_constraint=True
    )
    # ass_id = models.ForeignKey(Assistant, on_delete=models.CASCADE)
    assistant_id = models.UUIDField(unique=True, default=uuid.uuid4)
    prompt = models.TextField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    conversation_id = models.UUIDField(unique=False, default=uuid.uuid4)
