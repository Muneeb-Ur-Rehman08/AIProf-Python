from django.contrib import admin
from .models import Assistant, PDFDocument, PDFChunk, AnonConvo

# Register your models here.
admin.site.register(Assistant)

admin.site.register(PDFDocument)
admin.site.register(PDFChunk)
admin.site.register(AnonConvo)

