"""
Chat History - conversations + messages stored in Supabase PostgreSQL.
"""

from datetime import datetime
from supabase_client import get_supabase_admin as get_supabase


def _title_from_message(first_message: str) -> str:
    title = " ".join((first_message or "New chat").strip().split())
    if not title:
        title = "New chat"
    return title[:40] + ("..." if len(title) > 40 else "")


def create_conversation(student_id: str, first_message: str) -> str:
    """Create a new conversation row every time and return its ID."""
    sb = get_supabase()
    if not sb:
        print("[DEBUG ChatDB] No Supabase client returned by get_supabase()")
        return ""
    try:
        data = {
            "student_id": student_id,
            "title": _title_from_message(first_message),
            "is_active": True,
            "last_message_at": datetime.utcnow().isoformat(),
        }
        print(f"[DEBUG ChatDB] Creating new conversation: {data}")
        result = sb.table("conversations").insert(data).execute()
        print(f"[DEBUG ChatDB] Insert conversations result data: {result.data}")
        return result.data[0]["id"] if result.data else ""
    except Exception as e:
        print(f"[ChatDB] Create conversation failed: {e}")
        import traceback
        traceback.print_exc()
        return ""


def get_conversation_for_student(conversation_id: str, student_id: str) -> dict:
    """Return a conversation only if it belongs to the student."""
    sb = get_supabase()
    if not sb or not conversation_id or not student_id:
        return {}
    try:
        result = sb.table("conversations") \
            .select("*") \
            .eq("id", conversation_id) \
            .eq("student_id", student_id) \
            .limit(1) \
            .execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        print(f"[ChatDB] Get conversation failed: {e}")
        return {}


def save_message(
    conversation_id: str,
    student_id: str,
    role: str,
    content: str,
    language: str = "en",
    is_voice: bool = False,
    audio_url: str = None,
    search_used: bool = False,
) -> dict:
    """Save a single message to Supabase."""
    sb = get_supabase()
    if not sb:
        print("[DEBUG ChatDB] No Supabase client returned by get_supabase()")
        return {}
    try:
        data = {
            "conversation_id": conversation_id,
            "student_id": student_id,
            "role": role,
            "content": content,
            "language": language,
            "is_voice": is_voice,
            "audio_url": audio_url,
            "search_used": search_used,
        }
        print(f"[DEBUG ChatDB] Inserting into messages: {data}")
        result = sb.table("messages").insert(data).execute()
        print(f"[DEBUG ChatDB] Insert messages result data: {result.data}")

        update_result = sb.table("conversations") \
            .update({"last_message_at": datetime.utcnow().isoformat()}) \
            .eq("id", conversation_id) \
            .eq("student_id", student_id) \
            .execute()
        print(f"[DEBUG ChatDB] Update conversations last_message_at result data: {update_result.data}")

        return result.data[0] if result.data else {}
    except Exception as e:
        print(f"[ChatDB] Save message failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_conversation_history(conversation_id: str, student_id: str = None, limit: int = 20, for_llm: bool = False) -> list:
    """Get messages for a conversation, optionally formatted for LLM context."""
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table("messages") \
            .select("*") \
            .eq("conversation_id", conversation_id)
        if student_id:
            query = query.eq("student_id", student_id)
        result = query.order("created_at", desc=False).limit(limit).execute()
        rows = result.data or []
        if for_llm:
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in rows
                if msg.get("role") in {"user", "assistant"}
            ]
        return rows
    except Exception as e:
        print(f"[ChatDB] Get history failed: {e}")
        return []


def get_student_conversations(student_id: str) -> list:
    """List all conversations for a student, most recent first."""
    sb = get_supabase()
    if not sb:
        return []
    try:
        result = sb.table("conversations") \
            .select("id, title, last_message_at, created_at, is_active") \
            .eq("student_id", student_id) \
            .order("last_message_at", desc=True) \
            .execute()
        return result.data or []
    except Exception as e:
        print(f"[ChatDB] Get conversations failed: {e}")
        return []


def save_resource(student_id: str, resource: dict):
    """Save a bookmarked resource for a student."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("saved_resources").insert({
            "student_id": student_id,
            "title": resource.get("title", ""),
            "url": resource.get("url", ""),
            "resource_type": resource.get("type", "other"),
            "notes": resource.get("notes", ""),
        }).execute()
    except Exception as e:
        print(f"[ChatDB] Save resource failed: {e}")