from django.db import models, transaction
import uuid
from typing import Optional
import requests
from urllib.parse import urlparse

import numpy as np
from django.core.files.storage import default_storage

import os
from dotenv import load_dotenv
import logging
from django.contrib.auth.models import User 
from django.contrib.postgres.fields import ArrayField
import tempfile
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader, YoutubeLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
import shutil
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Avg
from django.core.validators import URLValidator


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
    total_reviews = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0')) 
    interactions = models.IntegerField(blank=True, null=True, default=0)
    is_published = models.BooleanField(default=False)
    image = models.BinaryField(null=True, blank=True)


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
        Override the save method to update the average rating and total reviews 
        of the assistant when a new rating is created without modifying the existing entries.
        """
        # Use atomic transaction to ensure both rating and assistant update happen together
        with transaction.atomic():
            # Save the new rating entry
            super().save(*args, **kwargs)
            
            # Lock the assistant record to prevent race conditions
            assistant = Assistant.objects.select_for_update().get(id=self.assistant.id)
            
            # Recalculate the average rating for the assistant
            ratings = AssistantRating.objects.filter(assistant=self.assistant)
            average_rating = ratings.aggregate(average=Avg('rating'))['average'] or Decimal('0.0')
            
            # Calculate total number of reviews
            total_reviews = ratings.count()
            
            # Update the assistant with new average rating and total reviews
            assistant.average_rating = round(Decimal(average_rating), 1)  # Round to 1 decimal place
            assistant.total_reviews = Decimal(total_reviews)
            
            # Save the assistant with the updated average rating and total reviews
            assistant.save()


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
    urls = ArrayField(
        models.URLField(max_length=2000), 
        null=True, 
        blank=True, 
        default=list
    )
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
    

    def _validate_document_input(self):
        # Validate URLs if provided
        if self.urls:
            for url in self.urls:
                try:
                    # YouTube URL validation
                    def is_youtube_url(url):
                        parsed_url = urlparse(url)
                        youtube_domains = [
                            'youtube.com', 
                            'www.youtube.com', 
                            'youtu.be', 
                            'm.youtube.com'
                        ]
                        return (
                            parsed_url.netloc in youtube_domains or
                            'youtube.com/watch' in url or
                            'youtu.be/' in url
                        )

                    # Basic URL validation
                    result = urlparse(url)
                    if not all([result.scheme, result.netloc]):
                        raise ValidationError(f"Invalid URL format: {url}")
                    
                    # Optional: Check if URL is reachable
                    try:
                        response = requests.head(url, timeout=5)
                        if response.status_code != 200:
                            raise ValidationError(f"Unable to access URL: {url}")
                    except requests.RequestException:
                        # Allow URLs that might not respond to HEAD requests
                        pass
                    
                    # Log YouTube URL
                    if is_youtube_url(url):
                        logger.info(f"YouTube URL detected: {url}")
                    
                except Exception as e:
                    raise ValidationError(f"URL validation error for {url}: {str(e)}")

    def process_pdf(self):
        # Validate input
        self._validate_document_input()

        try:
            self.status = 'processing'
            self.save()

            # Initialize text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            # Check if the document already exists
            existing_document = PDFDocument.objects.filter(
                assistant_id=self.assistant_id,
                title=self.title,
                status='completed'
            ).first()

            # Process PDF file
            if self.file:
                
                
                if existing_document:
                    # Log that the document already exists
                    logger.info(f"Document '{self.title}' already processed. Skipping.")
                else:
                    temp_dir = tempfile.mkdtemp(prefix='pdf_processing_')
                    original_file_path = self.file.path
                    temp_file_path = os.path.join(temp_dir, os.path.basename(original_file_path))
                    logger.info(f"Processing file: {temp_file_path}")
                    shutil.copy2(original_file_path, temp_file_path)

                    try:
                        loader = PyPDFLoader(temp_file_path)
                        pages = loader.load_and_split()
                        text_chunks = [page.page_content for page in pages]
                    except Exception as e:
                        logger.error(f"Error processing PDF: {e}")
                        text_chunks = []
                    finally:
                        # Cleanup temp files
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)

            # Process URL content
            elif self.urls:
                text_chunks = []
                for url in self.urls:
                    if existing_document:
                        logger.info(f"URL '{self.title}' already processed. Skipping.")
                    else:
                        # Check if YouTube URL
                        if any(yt_domain in url for yt_domain in ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']):
                            try:
                                # Use YoutubeLoader to extract transcript
                                youtube_loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
                                youtube_docs = youtube_loader.load()
                                # logger.info(f"Youtube docs are: {youtube_docs}")
                                youtube_text = " ".join([doc.page_content for doc in youtube_docs])
                                youtube_chunks = text_splitter.split_text(youtube_text)
                                text_chunks.extend(youtube_chunks)
                            except Exception as e:
                                logger.error(f"Error processing YouTube URL {url}: {str(e)}")
                        else:
                            # Process regular web URLs
                            try:
                                loader = WebBaseLoader(url)
                                web_docs = loader.load()
                                # logger.info(f"Web docs are: {web_docs}")
                                web_text = " ".join([doc.page_content for doc in web_docs])
                                web_chunks = text_splitter.split_text(web_text)
                                text_chunks.extend(web_chunks)
                            except Exception as e:
                                logger.error(f"Error processing web URL {url}: {str(e)}")

            else:
                raise ValidationError("No valid document source found.")

            # Initialize Langchain OpenAIEmbeddings client
            embeddings_model = OpenAIEmbeddings()

            # Process each chunk and store it
            for chunk_number, chunk_content in enumerate(text_chunks, start=1):
                # Generate embedding for the chunk's content
                chunk_embedding = embeddings_model.embed_documents([chunk_content])[0]

                # Store the chunk content and its embedding in the DocumentChunk model
                DocumentChunk.objects.create(
                    document=self,
                    page_number=chunk_number,
                    content=chunk_content,
                    vector_embedding=chunk_embedding
                )

            # Prepare metadata for the document
            self.metadata = {
                'filename': self.title,
                'source': self.file.name if self.file else ", ".join(self.urls),
                'user_id': str(self.user_id.id) if self.user_id else None,
                'assistant_id': str(self.assistant_id.id) if self.assistant_id else None,
                'total_chunks': len(text_chunks),
                'document_type': 'pdf' if self.file else 'url'
            }

            self.status = 'completed'
            self.save()

        except Exception as e:
            self.status = 'failed'
            self.save()
            raise RuntimeError(f"Document Processing Error: {str(e)}")


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
    def similarity_search(cls, query: str, assistant_id: str, k: int = 5):
        """
        Find most similar document chunks to the query using cosine similarity.
        
        Args:
            query (str): Search query text
            k (int, optional): Number of top similar chunks. Defaults to 5.
            api_key (str): OpenAI API key
        
        Returns:
            List of tuples with chunks and similarity scores
        """
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            
            client = OpenAI(api_key=api_key)

            # Generate query embedding
            query_response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = np.array(query_response.data[0].embedding)

            # Fetch document chunks with embeddings only for the specified assistant
            chunks = cls.objects.filter(
                document__assistant_id=assistant_id,
                vector_embedding__isnull=False
            )

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



class Subject(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name=('Subject Name')
    )
    

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ('Subject')
        verbose_name_plural = ('Subjects')
        ordering = ['name']

class Topic(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(
        max_length=255, 
        verbose_name=('Topic Name')
    )
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='topics',
        null=True, 
        blank=True
    )
    
   
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ('Topic')
        verbose_name_plural = ('Topics')
        ordering = ['name']