# Generated by Django 5.1.2 on 2024-11-21 13:18

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistantchat', '0001_initial'),
        ('users', '0006_delete_conversation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='conversation',
            old_name='convo_id',
            new_name='id',
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='conversation',
            name='user_id',
        ),
        migrations.AddField(
            model_name='conversation',
            name='conversation_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='conversation',
            name='users_id',
            field=models.ForeignKey(db_column='users_id', default=uuid.uuid4, on_delete=django.db.models.deletion.CASCADE, to='users.supabaseuser'),
        ),
        migrations.AlterField(
            model_name='conversation',
            name='content',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='conversation',
            name='prompt',
            field=models.TextField(),
        ),
    ]