from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Manage (create/update) assistants
    path('assistant/', views.create_assistant, name='create_assistant'),
    path('assistant/<str:ass_id>/', views.create_assistant, name='assistant'),
    
    # Get assistants (list or specific)
    path('assistants/', views.get_assistant, name='get_assistants'),
    path('assistants/<str:ass_id>/', views.get_assistant, name='get_assistant'),


    # Generate Instructions
    path('assistants/generate_instructions/<str:assistant_id>', views.generate_instructions, name='generate_instructions'),
    
    # Delete KnowledgeBase
    path('knowledgebasedelete/<str:document_id>/', views.del_knowledgebase, name='del_knowledgebase'),
    
    # Delete assistant
    path('assistants/delete/<str:ass_id>/', views.delete_assistant, name='delete_assistant'),
    path('assistants/get_topics/<str:subject_id>/', views.get_topics, name='get_topics'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

