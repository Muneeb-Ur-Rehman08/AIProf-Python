from django.urls import path
from . import views


urlpatterns = [
    path('chat/', views.chat_query, name='chat'),
    path('voice/', views.voice_chat, name='voice_chat'),
    path("submit-review/<str:assistant_id>/", views.submit_review, name="submit_review"),
    path("notes/c/<str:assistant_id>/", views.create_notes, name="notes"),
    path("notes/del/<str:note_id>/", views.delete_note, name="delnotes")
    
]