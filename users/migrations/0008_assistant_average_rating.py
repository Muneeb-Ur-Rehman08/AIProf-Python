# Generated by Django 5.1.3 on 2024-12-01 10:47

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_alter_assistantrating_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistant',
            name='average_rating',
            field=models.DecimalField(decimal_places=1, default=Decimal('0.0'), max_digits=3),
        ),
    ]
