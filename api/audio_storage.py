"""
Audio Storage — upload voice clips and TTS audio to Supabase Storage.
Bucket: 'voice-clips' (create in Supabase dashboard → Storage → New bucket → Public)
"""

import uuid
from supabase_client import get_supabase_admin as get_supabase


def upload_voice_audio(audio_bytes: bytes, student_id: str) -> str:
    """Upload a student's voice clip, return public URL."""
    sb = get_supabase()
    if not sb:
        return ""
    try:
        filename = f"{student_id}/{uuid.uuid4()}.webm"
        sb.storage.from_("voice-clips").upload(
            path=filename,
            file=audio_bytes,
            file_options={"content-type": "audio/webm"}
        )
        return sb.storage.from_("voice-clips").get_public_url(filename)
    except Exception as e:
        print(f"[AudioStorage] Upload failed: {e}")
        return ""


def upload_tts_audio(audio_bytes: bytes, message_id: str) -> str:
    """Upload TTS response audio, return public URL."""
    sb = get_supabase()
    if not sb:
        return ""
    try:
        filename = f"tts/{message_id}.mp3"
        sb.storage.from_("voice-clips").upload(
            path=filename,
            file=audio_bytes,
            file_options={"content-type": "audio/mpeg"}
        )
        return sb.storage.from_("voice-clips").get_public_url(filename)
    except Exception as e:
        print(f"[AudioStorage] TTS upload failed: {e}")
        return ""
