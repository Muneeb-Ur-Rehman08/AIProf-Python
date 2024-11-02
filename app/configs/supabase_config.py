import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

SUPABASE_CLIENT = create_client(url, key)
