# Generated by Django 5.1.4 on 2024-12-13 12:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistantchat', '0005_alter_conversation_options'),
        ('users', '0016_assistant_total_reviews'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeAssessment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=100)),
                ('topic', models.CharField(max_length=100)),
                ('knowledge_level', models.CharField(choices=[('unassessed', 'Unassessed'), ('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')], default='unassessed', max_length=20)),
                ('diagnostic_questions', models.JSONField(blank=True, null=True)),
                ('user_answers', models.JSONField(blank=True, null=True)),
                ('assessment_score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('assessment_insights', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assistant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_assessments', to='users.assistant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_assessments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Knowledge Assessments',
                'unique_together': {('user', 'assistant', 'subject', 'topic')},
            },
        ),
    ]