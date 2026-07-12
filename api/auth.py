"""
Authentication — register, login, Google OAuth, Phone OTP, JWT verification.
All powered by Supabase Auth.
"""

from fastapi import HTTPException, Header
from supabase_client import get_supabase


async def register_student(email: str, password: str, full_name: str = ""):
    """Register a new student. Auto-creates a profile row via DB trigger."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    try:
        result = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"full_name": full_name}
            }
        })
        return {
            "user_id": result.user.id,
            "message": "Check your email to confirm account"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def login_student(email: str, password: str):
    """Login with email + password. Returns JWT tokens."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    try:
        result = sb.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "user_id": result.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


async def get_google_login_url(redirect_to: str = "http://localhost:5173/auth/callback"):
    """Get Google OAuth login URL."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    result = sb.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": redirect_to}
    })
    return {"url": result.url}


async def send_otp(phone: str):
    """Send OTP to phone number (format: +923001234567)."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    sb.auth.sign_in_with_otp({"phone": phone})
    return {"message": "OTP sent"}


async def verify_otp(phone: str, token: str):
    """Verify phone OTP and return session."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    result = sb.auth.verify_otp({
        "phone": phone,
        "token": token,
        "type": "sms"
    })
    return {
        "access_token": result.session.access_token,
        "user_id": result.user.id
    }


async def get_current_user(authorization: str = Header(default="")):
    """Middleware: verify JWT on protected requests. Returns user or None."""
    print(f"[DEBUG get_current_user] Authorization Header: '{authorization}'")
    if not authorization:
        print("[DEBUG get_current_user] No Authorization header passed.")
        return None
    sb = get_supabase()
    if not sb:
        print("[DEBUG get_current_user] No Supabase client.")
        return None
    try:
        token = authorization.replace("Bearer ", "")
        user = sb.auth.get_user(token)
        print(f"[DEBUG get_current_user] Token verified successfully. User: {user.user}")
        return user.user
    except Exception as e:
        print(f"[DEBUG get_current_user] Token verification failed: {e}")
        import traceback
        traceback.print_exc()
        return None
