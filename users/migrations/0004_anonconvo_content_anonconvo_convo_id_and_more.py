# Generated by Django 5.1.2 on 2024-11-19 09:21

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_assistant_user_id_alter_conversation_user_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='anonconvo',
            name='content',
            field=models.JSONField(null=True),
        ),
        migrations.AddField(
            model_name='anonconvo',
            name='convo_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='anonconvo',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='anonconvo',
            name='parent_msg_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='anonconvo',
            name='role',
            field=models.CharField(default='User', max_length=255),
        ),
        migrations.AddField(
            model_name='anonconvo',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]