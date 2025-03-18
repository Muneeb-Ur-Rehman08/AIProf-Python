from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.contrib.auth.decorators import login_required
import uuid
import logging
from users.models import Assistant
from assistantchat.models import QuizAttempt
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

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


def assistant_chat_view(request, assistant_id):
    assistant = Assistant.objects.get(id=assistant_id)
    is_creator = request.user.id == assistant.user_id.id
    chat_mode = True  # Set this based on your routing/URL logic
    assistants = Assistant.objects.filter(user_id=request.user.id)

    

    # Fetch quiz attempts for the specific user
    user = User.objects.get(id=request.user.id)
    user_id = user.id
    
    quiz_attempts = QuizAttempt.objects.filter(user_id=user, assistant_id=assistant, completed=True)
    
    # Calculate average score across all attempts
    total_attempts = quiz_attempts.count()
    total_score = sum([attempt.calculate_score() for attempt in quiz_attempts])
    avg_score = round(total_score / total_attempts, 3) if total_attempts > 0 else 0

   

    return render(request, 'assistant/chat_wrapper.html', {
        'assistant': assistant, 
        'is_creator': is_creator, 
        'chat_mode': chat_mode,
        'assistants': assistants,
        'user_id': user_id,
        'avg_score': avg_score,
        'total_attempts': total_attempts
    })

def total_score(request, assistant_id):
    assistant = Assistant.objects.get(id=assistant_id)
    # Fetch quiz attempts for the specific user
    user = User.objects.get(id=request.user.id)
    user_id = user.id
    quiz_attempts = QuizAttempt.objects.filter(user_id=user, assistant_id=assistant, completed=True)
    
    # Calculate average score across all attempts
    total_attempts = quiz_attempts.count()
    total_score = sum([attempt.calculate_score() for attempt in quiz_attempts])
    avg_score = round(total_score / total_attempts, 3) if total_attempts > 0 else 0

    return HttpResponse(
        f"<p>Avg Score: { avg_score }% (out of { total_attempts } quizzes)</p>"
    )
