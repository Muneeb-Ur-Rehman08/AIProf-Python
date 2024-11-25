from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.contrib.auth.decorators import login_required

def index_view(request):
    faqs = [
        {"question": "What is AI Prof?", 
         "reqs": "reqs",
         "answer": "AI Prof transforms education by revolutionizing learning experiences, improving knowledge retention, and offering instant support, enhancing students' educational journeys."},
        {"question": "Is AI Prof free?", 
         "reqs": "reqs",
         "answer": "We offer a free version with the Meet Your AI Prof chatbot for quick answers, along with two subscription plans for personalized solutions that cater to your specific needs."},
        {"question": "Is AI Prof for Charity?", 
         "reqs": "reqs",
         "answer": "Yes, AI Prof also operates as a charity, dedicated to providing free educational resources and support to students."},
        {"question": "Is AI Prof Safe?", 
         "reqs": "reqs",
         "answer": "AI Prof is committed to data security, employing stringent measures to safeguard your personal and business information, guaranteeing its protection."}
    ]
    try:
        return render(request, 'index.html', {'faqs': faqs})
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
        return render(request, 'assistant/assistant_form.html')
    except TemplateDoesNotExist:
        return HttpResponse("Template not found", status=404)