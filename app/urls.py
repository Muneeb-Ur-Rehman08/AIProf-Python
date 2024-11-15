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
from django.urls import path
from app.views import chat_view, upload_doc, get_rag_answer
from app.app_views.template_views import index_view, auth_view, create_assistant
from app.app_views.auth_views import sign_up, sign_in, continue_with_google, sign_out, store_session

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', chat_view, name='chat'),
    path('api/upload_doc/', upload_doc, name='upload_doc'),
    path('api/rag/', get_rag_answer, name='rag'),
    path('', index_view, name='index'),
    path('auth/', auth_view, name='auth_view'),
    path('create_assistant/', create_assistant, name='create_assistant'),
    path('auth/continue_with_google/', continue_with_google, name='google'),
    path('sign_up/', sign_up, name='sign_up'),
    path('sign_in/', sign_in, name='sign_in'),
    path('sign_out/', sign_out, name='sign_out'),
    path('store-session/', store_session, name='store_session'),
]
