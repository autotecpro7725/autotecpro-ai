from supabase import create_client

SUPABASE_URL = "https://zqvznbfhzugigjffrwsy.supabase.co"

SUPABASE_KEY = "sb_publishable_mWQiw4ZxSdAPqvdOABdAxg_3uGBwOgH"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)