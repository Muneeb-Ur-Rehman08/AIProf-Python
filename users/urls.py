from django.urls import path
from . import views


urlpatterns = [
    # Manage (create/update) assistants
    path('assistant/', views.create_assistant, name='create_assistant'),
    path('assistant/<str:ass_id>/', views.create_assistant, name='assistant'),
    
    # Get assistants (list or specific)
    path('assistants/', views.get_assistant, name='get_assistants'),
    path('assistants/<str:ass_id>/', views.get_assistant, name='get_assistant'),
    
    
    # Delete assistant
    path('assistants/delete/<str:ass_id>/', views.delete_assistant, name='delete_assistant'),
]