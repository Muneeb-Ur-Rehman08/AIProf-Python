import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

SUPABASE_CLIENT = create_client(url, key)
