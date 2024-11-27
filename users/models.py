from django.db import models
import uuid
from django.core.files.storage import default_storage
from django.conf import settings
import numpy as np
from pypdf import PdfReader
import io
from typing import List
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
import logging
from PyPDF2 import PdfReader


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



class TestModels(models.Model):
    test_user = models.ForeignKey(
        SupabaseUser,
        on_delete=models.CASCADE,
        db_column='user_id',
        to_field='id',
        null=False,
        blank=False,
        default=uuid.uuid4,
        db_constraint=True
    )
    name = models.TextField()
    password = models.TextField()


class TestModels2(models.Model):
    text = models.CharField(max_length=100)
    description = models.CharField(max_length=100)


class Assistant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    user_id = models.ForeignKey(
        SupabaseUser,
        on_delete=models.CASCADE,
        db_column='user_id',
        to_field='id',
        null=False,
        blank=False,
        default=uuid.uuid4,
        db_constraint=True
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
    



class AnonConvo(models.Model):
    anonconvo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    user_id = models.ForeignKey(
        SupabaseUser,
        on_delete=models.CASCADE,
        db_column='user_id',
        to_field='id',
        null=False,
        blank=False,
        default=uuid.uuid4,
        db_constraint=True
        )
    content = models.JSONField(null=True)
    convo_id = models.UUIDField(default=uuid.uuid4)
    parent_msg_id = models.UUIDField(default=uuid.uuid4)
    role = models.CharField(max_length=255, default="User")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)


class PDFDocument(models.Model):
    doc_id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user_id = models.ForeignKey(
        SupabaseUser,
        on_delete=models.CASCADE,
        db_column="user_id",
        to_field="id",
        default=uuid.uuid4,
        db_constraint=True
    )
    ass_id = models.ForeignKey(Assistant, default=uuid.uuid4, on_delete=models.CASCADE)

    def _str_(self):
        return self.title

    def process_pdf(self):
        """
        Process PDF file into chunks with vector embeddings and advanced handling
        """
        try:
            self.status = 'processing'
            self.save()

            # Extract text from all pages
            with open(self.file.path, 'rb') as pdf_file:
                reader = PdfReader(pdf_file)
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + " "

            # Alternative approach to create chunks
            words = full_text.split()
            chunk_size = 1000  # Adjustable chunk size
            chunks = []

            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i + chunk_size])
                
                chunk = PDFChunk.objects.create(
                    document=self,
                    content=chunk_text,
                    chunk_index=i // chunk_size,
                    page_number=(i // chunk_size) + 1  # Approximate page number
                )
                
                # Generate embedding for each chunk
                chunk.generate_embedding()
                chunks.append(chunk)

            # Attempt to delete the original file
            try:
                original_path = self.file.path
                if os.path.exists(original_path):
                    os.remove(original_path)
                    # Clear the file field
                    self.file.delete(save=False)
            except Exception as file_deletion_error:
                logger.error(f"Error deleting file: {file_deletion_error}")

            self.status = 'completed'
            self.save()
            return chunks

        except Exception as e:
            # Attempt to delete file even if processing fails
            try:
                if os.path.exists(self.file.path):
                    os.remove(self.file.path)
            except Exception as file_deletion_error:
                logger.error(f"Error deleting file during error handling: {file_deletion_error}")

            self.status = 'failed'
            self.save()
            raise RuntimeError(f"PDF Processing Error: {str(e)}")
    

class PDFChunk(models.Model):
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    vector_embedding = models.JSONField(null=True)  # Store as JSON for better compatibility
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"

    def generate_embedding(self) -> None:
        """Generate and save vector embedding using OpenAI API."""
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Get embeddings from OpenAI
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=self.content
            )
            
            # Store embedding as JSON
            self.vector_embedding = response.data[0].embedding
            self.save()
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            raise

    def get_embedding_array(self) -> np.ndarray:
        """Retrieve the vector embedding as a numpy array."""
        if self.vector_embedding:
            return np.array(self.vector_embedding)
        return None

    @classmethod
    def similarity_search(cls, query: str, k: int = 5) -> List['PDFChunk']:
        """Find most similar chunks to the query using cosine similarity.
        
        Args:
            query (str): The search query text
            k (int): Number of results to return
            
        Returns:
            List[PDFChunk]: List of k most similar chunks
        """
        try:
            # Generate embedding for query
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            query_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = np.array(query_response.data[0].embedding)

            # Get all chunks with embeddings
            chunks = cls.objects.exclude(vector_embedding__isnull=True)
            
            # Calculate cosine similarity with each chunk
            similarities = []
            for chunk in chunks:
                chunk_embedding = chunk.get_embedding_array()
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )
                similarities.append((chunk, similarity))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [chunk for chunk, _ in similarities[:k]]

        except Exception as e:
            print(f"Error in similarity search: {str(e)}")
            return []