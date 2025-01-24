from django.urls import re_path
from assistantchat.consumers import VoiceAssistantConsumer

websocket_urlpatterns = [
    re_path(r'ws/assistant/$', VoiceAssistantConsumer.as_asgi()),
]
