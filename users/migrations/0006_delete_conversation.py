# Generated by Django 5.1.2 on 2024-11-21 13:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_pdfdocument_pdfchunk'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Conversation',
        ),
    ]