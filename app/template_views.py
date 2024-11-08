from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist

def index_view(request):
    try:
        return render(request, 'index.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)

def auth_view(request):
    try:
        return render(request, 'auth/auth_page.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)

def create_assistant(request):
    try:
        return render(request, 'assistant/assistant_form.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404) 