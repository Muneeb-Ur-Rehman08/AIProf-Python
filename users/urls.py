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
    path('assistants/generate-instructions/', views.generate_instructions, name='generate_instructions'),
    
    
    # Delete assistant
    path('assistants/delete/<str:ass_id>/', views.delete_assistant, name='delete_assistant'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

