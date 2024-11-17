from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.contrib.auth.decorators import login_required
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
@login_required
def create_assistant(request):
    try:
        print(f"user is authenticated: {request.user}")
        return render(request, 'assistant/assistant_form.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)