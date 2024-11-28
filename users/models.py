from django.db import models
import uuid
from django.core.files.storage import default_storage
from django.conf import settings
import numpy as np
from pypdf import PdfReader
from typing import List
import json
import os
from dotenv import load_dotenv
import logging
from django.contrib.auth.models import User 
from django.contrib.postgres.fields import ArrayField

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

# Create your models here.

class SupabaseUser(models.Model):
    """
    Proxy model for Supabase auth.users table
    This model connects to Supabase's auth.users table, not a Django database.
    
    To get user data from Supabase:
    1. First authenticate with Supabase client
    2. Then query through this model:
       
       # Get single user
       user = SupabaseUser.objects.get(email='user@example.com')
       
       # The id and email fields will be populated from Supabase auth.users table
       user_id = user.id  # UUID from Supabase
       user_email = user.email
       
    Note: This is a read-only proxy to Supabase auth - any changes should be made
    through Supabase authentication APIs, not through this model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    email = models.EmailField(unique=True)
    
    class Meta:
        managed = False  # This tells Django this table exists in Supabase, not Django
        db_table = 'auth\".\"users'  # Points to Supabase auth.users table



class Assistant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    user_id = models.ForeignKey(
        User,  # Changed to Django User model
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        default=uuid.uuid4,
        db_constraint=True,
        to_field='id',  # Explicitly use the primary key of User model
        db_column='user_id'  # This ensures the column name is 'user_id'
    )
    name = models.CharField(max_length=255, default="Assistant", blank=True)
    subject = models.CharField(max_length=255, default="Default Subject", blank=True)
    teacher_instructions = models.TextField(default="Default instructions", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name_plural = 'Assistants'

    
    def __str__(self) -> str:
        return self.name
    


# class AnonConvo(models.Model):
#     anonconvo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
#     user_id = models.ForeignKey(
#         User,  # Changed to Django User model
#         on_delete=models.CASCADE,
#         null=False,
#         blank=False,
#         default=uuid.uuid4,
#         to_field='id',  # Explicitly use the primary key of User model
#         db_column='user_id',  # This ensures the column name is 'user_id'
#         db_constraint=True
#         )
#     content = models.JSONField(null=True)
#     convo_id = models.UUIDField(default=uuid.uuid4)
#     parent_msg_id = models.UUIDField(default=uuid.uuid4)
#     role = models.CharField(max_length=255, default="User")
#     created_at = models.DateTimeField(auto_now_add=True, null=True)
#     updated_at = models.DateTimeField(auto_now=True, null=True)


class PDFDocument(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    doc_id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        related_name='pdf_documents',
        to_field='id',
        db_column='user_id'
    )
    
    assostant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE, 
        null=True,
        related_name='pdf_documents',
        to_field='id',
        db_column='assistant_id'
    )
    
    title = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS_CHOICES, 
        default='pending'
    )
    chunk_content = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    vector_embedding = ArrayField(
        models.FloatField(), 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return self.title or str(self.doc_id)

    def process_pdf(self):
        temp_dir = os.path.join('temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = None
        
        try:
            # Create temporary file path
            temp_file_path = os.path.join(temp_dir, self.file.name)
            
            # Save uploaded file to temporary location
            with open(temp_file_path, 'wb+') as destination:
                for chunk in self.file.chunks():
                    destination.write(chunk)
            
            # Set status to processing
            self.status = 'processing'
            self.save()

            # Load PDF using PyPDFLoader
            loader = PyPDFLoader(temp_file_path)
            pages = loader.load_and_split()

            # Text splitting for creating chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_documents(pages)

            # Store chunk contents
            self.chunk_content = json.dumps([
                chunk.page_content for chunk in chunks
            ])

            # Initialize OpenAI client
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Prepare metadata
            self.metadata = {
                'filename': os.path.basename(temp_file_path),
                'user_id': str(self.user_id.id) if self.user_id else None,
                'ass_id': str(self.ass_id.id) if self.ass_id else None,
                'chunks': [
                    {
                        'id': chunk.metadata.get('id'),
                        'page_number': chunk.metadata.get('page_number')
                    } for chunk in chunks
                ]
            }

            # Generate embeddings
            embeddings = []
            for chunk in chunks:
                response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=chunk.page_content
                )
                embeddings.extend(response.data[0].embedding)

            # Store vector embeddings
            self.vector_embedding = embeddings

            # Set status to completed
            self.status = 'completed'
            self.save()

            return self

        except Exception as e:
            # Set status to failed
            self.status = 'failed'
            self.save()
            
            raise RuntimeError(f"PDF Processing Error: {str(e)}")
        
        finally:
            # Cleanup temporary files
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")

    @classmethod
    def similarity_search(cls, query: str, k: int = 5):
        """
        Find most similar documents to the query using cosine similarity.
        """
        try:
            # Generate embedding for query
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            query_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = np.array(query_response.data[0].embedding)

            # Get all documents with embeddings
            documents = cls.objects.exclude(vector_embedding__isnull=True)
            
            # Calculate cosine similarity
            similarities = []
            
            for doc in documents:
                doc_embedding = np.array(doc.vector_embedding)
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((doc, similarity))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:k]

        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []