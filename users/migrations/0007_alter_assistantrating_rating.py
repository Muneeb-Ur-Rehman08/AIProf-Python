# Generated by Django 5.1.3 on 2024-12-01 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_assistantrating_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assistantrating',
            name='rating',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True),
        ),
    ]