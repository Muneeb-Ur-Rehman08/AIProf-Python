from django.db import models

# Create your models here.


class TestModels(models.Model):
    name = models.TextField()
    password = models.TextField()