from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.contrib.auth.decorators import login_required
import uuid

def index_view(request):
    try:
        return render(request, 'index.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)

def auth_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    try:
        return render(request, 'auth/auth_page.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)
# assistant form is show only if user is logged in
@login_required(login_url='auth_view')
def create_assistant_view(request):
    try:
        print(f"user is authenticated: {request.user}")
        
        assistant_id = uuid.uuid4()

        assistant = request.session.get('assistant', None)

        print(f"assistant: {assistant}")

        return render(request, 'assistant/assistant_form.html', {'assistant': assistant})
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)
def assistant_chat_view(request):
    return render(request, 'assistant/assistant_chat.html')

