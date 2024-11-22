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


load_dotenv()

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
    ass_id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
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
    assistan_name = models.CharField(max_length=255, default="Assistant")
    subject = models.CharField(max_length=255, default="Default Subject")
    teacher_instructions = models.TextField(default="Default instructions")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name_plural = 'Assistants'

    
    def __str__(self) -> str:
        return self.assistan_name
    



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

    def process_pdf(self, chunk_size: int = 1000) -> List['PDFChunk']:
        """Process PDF file into chunks and create vector embeddings."""
        # Read PDF content
        pdf_file = default_storage.open(self.file.name)
        pdf_reader = PdfReader(io.BytesIO(pdf_file.read()))
        
        # Extract text from all pages
        full_text = ""
        for page in pdf_reader:
            full_text += page.extract_text() + " "
        
        # Create chunks - using words as delimiter
        words = full_text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            chunk = PDFChunk.objects.create(
                document=self,
                content=chunk_text,
                chunk_index=i // chunk_size
            )
            # Generate embedding immediately after creating chunk
            chunk.generate_embedding()
            chunks.append(chunk)
            
        return chunks
    

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