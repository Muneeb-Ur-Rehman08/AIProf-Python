# Generated by Django 5.1.4 on 2024-12-16 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_assistant_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assistant',
            name='image',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]
