from django.db import models
import uuid
from typing import Optional

import numpy as np
from django.core.files.storage import default_storage

import os
from dotenv import load_dotenv
import logging
from django.contrib.auth.models import User 
from django.contrib.postgres.fields import ArrayField
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
import shutil
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Avg


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
        db_constraint=True,
        to_field='id',  # Explicitly use the primary key of User model
        db_column='user_id'  # This ensures the column name is 'user_id'
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    teacher_instructions = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'))


    class Meta:
        verbose_name_plural = 'Assistants'

    
    def __str__(self) -> str:
        return self.name
    

class AssistantRating(models.Model):
    """
    Model to store user ratings for each assistant.
    Each assistant can have multiple ratings from different users.
    The rating is an integer from 1 to 5.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True)
    assistant = models.ForeignKey(
        'Assistant',
        on_delete=models.CASCADE,
        
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        
    )
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ],
        null=True,
        blank=True
    )
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('assistant', 'user')  # Ensures a user can rate an assistant only once

    def save(self, *args, **kwargs):
        """
        Override the save method to update the average rating of the assistant
        when a new rating is created without modifying the existing entries.
        """
        super().save(*args, **kwargs)  # Save the new rating entry

        # Recalculate the average rating for the assistant after saving the new rating
        ratings = AssistantRating.objects.filter(assistant=self.assistant).aggregate(average=Avg('rating'))
        
        new_average = ratings['average'] or Decimal('0.0')  # Set default to 0.0 if no ratings
        self.assistant.average_rating = round(Decimal(new_average), 1)  # Round to 1 decimal place
        
        self.assistant.save()  # Update the assistant's average rating

    def __str__(self):
        return f"Rating {self.rating} for {self.assistant.name} by {self.user.username}"



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
        null=True,
        related_name='pdf_documents',
        to_field='id',
        db_column='user_id'
    )

    assistant_id = models.ForeignKey(
        Assistant, 
        on_delete=models.CASCADE, 
        null=True,
        related_name='pdf_documents',
        to_field='id',
        db_column='assistant_id'
    )

    title = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending')
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.title or str(self.doc_id)

    def process_pdf(self):
        temp_dir = tempfile.mkdtemp(prefix='pdf_processing_')
        original_file_path = self.file.path
        temp_file_path = os.path.join(temp_dir, os.path.basename(original_file_path))
        shutil.copy2(original_file_path, temp_file_path)

        try:
            # Save the uploaded file to a temporary location
            with open(temp_file_path, 'wb+') as destination:
                for chunk in self.file.chunks():
                    destination.write(chunk)

            self.status = 'processing'
            self.save()

            # Load PDF using PyPDFLoader
            loader = PyPDFLoader(temp_file_path)
            pages = loader.load_and_split()

            
            # Initialize Langchain OpenAIEmbeddings client
            embeddings_model = OpenAIEmbeddings()

            # Process each chunk and store it in DocumentChunk table
            for page_number, page in enumerate(pages, start=1):
                # Page-wise content (each page will be a chunk)
                page_content = page.page_content

                # Generate embedding for the page's content
                page_embedding = embeddings_model.embed_documents([page_content])[0]

                # Store the page content and its embedding in the DocumentChunk model
                DocumentChunk.objects.create(
                    document=self,
                    page_number=page_number,  # Keep track of page number
                    content=page_content,
                    vector_embedding=page_embedding  # Store embedding for the entire page
                )


            # Prepare metadata for the document
            self.metadata = {
                'filename': self.file.name,
                'user_id': str(self.user_id.id) if self.user_id else None,
                'assistant_id': str(self.assistant_id.id) if self.assistant_id else None,
                'total_chunks': len(pages)
            }

            self.status = 'completed'
            self.save()

        except Exception as e:
            self.status = 'failed'
            self.save()
            raise RuntimeError(f"PDF Processing Error: {str(e)}")

        finally:
            try:
                # Remove temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)  # Delete the temporary file

                # Remove temporary directory
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)  # Remove the temporary directory

                # Remove the original file from the 'pdfs/' directory
                if os.path.exists(self.file.path):
                    default_storage.delete(self.file.path)  # Delete the original file from storage after processing
                    print(f"Trying to delete file at path: {self.file.path}")

            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        PDFDocument,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    page_number = models.IntegerField(null=True, blank=True)
    content = models.TextField()
    vector_embedding = ArrayField(
        models.FloatField(), 
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"Chunk {self.page_number} of {self.document.title}"
    
    @classmethod
    def similarity_search(cls, query: str, k: int = 5, api_key: Optional[str] = None):
        """
        Find most similar document chunks to the query using cosine similarity.
        
        Args:
            query (str): Search query text
            k (int, optional): Number of top similar chunks. Defaults to 5.
            api_key (str, optional): OpenAI API key
        
        Returns:
            List of tuples with chunks and similarity scores
        """
        try:
            client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

            # Generate query embedding
            query_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = np.array(query_response.data[0].embedding)

            # Fetch document chunks with embeddings
            chunks = cls.objects.exclude(vector_embedding__isnull=True)

            # Calculate similarities
            similarities = [
                (chunk, np.dot(query_embedding, np.array(chunk.vector_embedding)) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk.vector_embedding)
                ))
                for chunk in chunks
            ]

            # Sort and return top k results
            return sorted(similarities, key=lambda x: x[1], reverse=True)[:k]

        except Exception as e:
            logger.error(f"Similarity search error: {str(e)}")
            return []