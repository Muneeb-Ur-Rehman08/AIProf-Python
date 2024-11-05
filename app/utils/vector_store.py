import os
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from app.configs.supabase_config import SUPABASE_CLIENT
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from app.utils.supabase_methods import supabase_methods
from app.modals.chat import get_llm
from langchain.chains import ConversationalRetrievalChain
import PyPDF2
import uuid

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables")

embeddings = OpenAIEmbeddings()
vector_store = SupabaseVectorStore(
    embedding=embeddings,
    client=SUPABASE_CLIENT,
    table_name="documents",
)


# Define a Document class with id, page_content, and metadata
class Document:
    def __init__(self, page_content, metadata=None):
        self.id = str(uuid.uuid4())  # Generate a unique ID for each document
        self.page_content = page_content
        self.metadata = metadata or {}

def get_split_documents(file_path):
    # Use load_pdf to extract text from the PDF
    text = load_pdf(file_path)
    
    # Initialize the text splitter
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    
    # Split the text into chunks
    text_chunks = text_splitter.split_text(text)
    
    # Wrap each chunk in a Document object with metadata
    docs = [Document(chunk, metadata={"source": file_path, "id": str(uuid.uuid4())}) for chunk in text_chunks]
    
    return docs


def load_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {file_path}")
    except PyPDF2.errors.PdfReadError:
        raise RuntimeError(f"Error reading PDF file: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error loading {file_path}") from e
    

def store_embedding_vectors_in_supabase(file):
    docs = get_split_documents(file)
    result = vector_store.add_documents(
        docs,
        chunk_size=1000,
        chunk_overlap=0
    )
    response = supabase_methods['fetch']('documents', {'id': result[0]})

     # Access metadata as a dictionary key
    result_data = response.data[0].get('metadata', {})
    print("Document stored in supabase ", result_data)
    return result_data


def get_answer(query, id):
    llm = get_llm()

    # get similar text from the vector store
    result = vector_store.similarity_search(query, k=1, filter={ "id": id})

    source_knowledge = "\n".join([x.page_content for x in result])

    augmented_prompt = f"""Using the contexts below, answer the query.
    dont use any other information than the contexts provided.
    if you dont know the answer, just say that you dont know. dont make up an answer.
    if the question is not related to the contexts, say that you dont know.
    if the question is unclear, say that you dont know.

    Contexts:
    {source_knowledge}

    Query: {query}"""

    response = llm.invoke(augmented_prompt)

    return response.content


def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
