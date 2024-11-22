"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import chat_view, upload_doc, get_rag_answer, create_assistant, custom_login, logout
from .template_views import create_assistant_view, auth_view, index_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', chat_view, name='chat'),
    path('api/upload_doc/', upload_doc, name='upload_doc'),
    path('api/rag/', get_rag_answer, name='rag'),
    path('api/create_assistant/', create_assistant, name='create_assistant'),
    path('', index_view, name='index'),
    path('auth/', auth_view, name='auth_view'),

    # users app route
    path('users/', include('users.urls')),
    path('assistantchat/', include('assistantchat.urls')),
    path('create_assistant/', create_assistant_view, name='create_assistant'),
    path('login/', custom_login, name='login'),
    path('logout/', logout, name='logout'),
    # demo app route
]
