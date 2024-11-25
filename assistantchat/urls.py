from django.urls import path
from . import views


urlpatterns = [
    path('chat/<str:ass_id>/', views.chat_query, name='chat')
    
]