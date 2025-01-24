from django.urls import path
from . import views


urlpatterns = [
    path('chat/', views.chat_query, name='chat'),
    path('voice/', views.voice_chat, name='voice_chat'),
]