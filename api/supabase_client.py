"""
Supabase Client — connects to your Supabase project.
Uses anon key for frontend-facing operations and service role key for backend-only ops.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".env"))

_supabase = None
_supabase_admin = None


def get_supabase():
    """Get the public (anon key) Supabase client."""
    global _supabase
    if _supabase is not None:
        return _supabase

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("[Supabase] SUPABASE_URL or SUPABASE_ANON_KEY not set — Supabase disabled.")
        return None

    try:
        from supabase import create_client
        _supabase = create_client(url, key)
        print("[Supabase] Public client connected.")
        return _supabase
    except Exception as e:
        print(f"[Supabase] Connection failed: {e}")
        return None


def get_supabase_admin():
    """Get the service-role Supabase client (backend-only, never expose to frontend)."""
    global _supabase_admin
    if _supabase_admin is not None:
        return _supabase_admin

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None

    try:
        from supabase import create_client
        _supabase_admin = create_client(url, key)
        print("[Supabase] Admin client connected.")
        return _supabase_admin
    except Exception as e:
        print(f"[Supabase] Admin connection failed: {e}")
        return None
