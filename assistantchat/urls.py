from django.urls import path
from . import views


urlpatterns = [
    path('chat/', views.chat_query, name='chat'),
    path('voice/', views.voice_chat, name='voice_chat'),
    path("submit-review/<str:assistant_id>/", views.submit_review, name="submit_review"),
    path("notes/c/<str:assistant_id>/", views.create_notes, name="notes"),
    path("note/c/<str:assistant_id>/", views.create_note, name="note"),
    path("notes/del/<str:note_id>/", views.delete_note, name="delnotes"),
    path('quiz/generate/<str:assistant_id>/', views.quiz_view, name='quiz_generate'),
    path('quiz/check/<str:question_id>/', views.check_answer, name='check_answer')
    
]