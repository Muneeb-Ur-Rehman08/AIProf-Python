import json
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from app.utils.supabase_methods import supabase_methods
from app.configs.supabase_config import SUPABASE_CLIENT

def index_view(request):
    try:
        context = {
            'store_session': supabase_methods['set_session'],
            'message': 'Hello World'
        }
        render(request, './index.html', context)
        
        return HttpResponse(res)
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)

def auth_view(request):
    session = supabase_methods["get_session"]()
    print(f"session: {session}")
    # if session and session.user:
    #     return redirect('index')
    try:
        return render(request, 'auth/auth_page.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)

def create_assistant(request):
    try:
        return render(request, 'assistant/assistant_form.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404) 