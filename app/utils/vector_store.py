import os
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from app.configs.supabase_config import SUPABASE_CLIENT
# from langchain_community.document_loaders import TextLoader
from langchain.docstore.document import Document
from langchain_community.document_loaders import PyPDFLoader
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
# class Document:
#     def __init__(self, page_content, metadata=None):
#         self.id = str(uuid.uuid4())  # Generate a unique ID for each document
#         self.page_content = page_content
#         self.metadata = metadata or {}

def get_split_documents(file_path, user_id, ass_id):
    # Extract just the filename from the full path
    filename = os.path.basename(file_path)
    # Use PyPDFLoader to extract text from the PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    
    # Wrap each page in a Document object with metadata
    docs = [Document(page_content=page.page_content, metadata={
        "source": filename,
        "id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "ass_id": str(ass_id),
        "page_number": i + 1
    }) for i, page in enumerate(pages)]
    
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
    

def store_embedding_vectors_in_supabase(file, user_id, ass_id):
    docs = get_split_documents(file, user_id, ass_id)

    index = 1
    # Store each document chunk in the vector store
    for doc in docs:
        result = vector_store.add_documents([doc])
        response = supabase_methods['fetch']('documents', {'id': result[0]})

        # Access metadata as a dictionary key
        result_data = response.data[0].get('metadata', {})
        index += 1
    print(f"Document chunks stored in supabase: {index}")
    return [doc.metadata for doc in docs]


def get_answer(query, ass_id):
    llm = get_llm()

    # Get similar text from the vector store
    results = vector_store.similarity_search(query, k=3, filter={"ass_id": ass_id})

    # Check if multiple records are returned
    if not results:
        print("No records found.")
        return "No relevant context found."
    
    # Join the page content of all results
    source_knowledge = "\n".join([x.page_content for x in results])
    
    # Print the length of the result
    print(f"Number of records found: {len(results)}")

    # Construct the augmented prompt
    augmented_prompt = f"""Using the contexts below, answer the query.
    Don't use any other information than the contexts provided.
    If you don't know the answer, just say that you don't know. Don't make up an answer.
    If the question is not related to the contexts, say that you don't know.
    If the question is unclear, say that you don't know.

    Contexts:
    {source_knowledge}

    Query: {query}"""

    # Invoke the language model with the augmented prompt
    response = llm.invoke(augmented_prompt)
    print(response.content)
    return response.content

def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
