# Generated by Django 5.1.3 on 2024-11-28 16:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdfdocument',
            name='assistant_id',
            field=models.ForeignKey(db_column='assistant_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pdf_documents', to='users.assistant'),
        ),
        migrations.AlterField(
            model_name='pdfdocument',
            name='user_id',
            field=models.ForeignKey(db_column='user_id', default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pdf_documents', to=settings.AUTH_USER_MODEL),
        ),
    ]
