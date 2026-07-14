"""
Groq Whisper STT — Cloud-based Speech-to-Text via Groq API
Model  : whisper-large-v3 (highest accuracy, supports Urdu + English)
Key    : GROQ_API_KEY3 (dedicated STT key to avoid rate-limit conflicts with chat)
Latency: ~1-3s for a 30s clip (much faster than local Whisper)

Falls back to local Whisper if Groq key is missing or API fails.
"""

import os
import io
import tempfile

# ─── Groq Whisper (primary) ───────────────────────────────────────────────────

def transcribe_with_groq(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """
    Transcribe audio using Groq whisper-large-v3 API.
    Returns {"text": str, "language": str, "segments": list}
    Raises on failure so caller can fall back.
    """
    api_key = os.environ.get("GROQ_API_KEY3", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY3 not set in environment")

    from groq import Groq

    client = Groq(api_key=api_key)

    # Groq accepts a (filename, bytes, mime_type) tuple
    # Clean suffix so it's a valid extension like ".wav" or ".webm"
    clean_suffix = suffix.lstrip(".").lower() or "wav"
    filename = f"audio.{clean_suffix}"

    # Map browser recording formats to MIME types Groq accepts
    mime_map = {
        "wav":  "audio/wav",
        "webm": "audio/webm",
        "mp4":  "audio/mp4",
        "m4a":  "audio/mp4",
        "ogg":  "audio/ogg",
        "flac": "audio/flac",
        "mp3":  "audio/mpeg",
    }
    mime_type = mime_map.get(clean_suffix, "audio/wav")

    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes, mime_type),
        model="whisper-large-v3",
        response_format="verbose_json",   # gives language + segments
        temperature=0.0,                  # deterministic
    )

    # verbose_json returns an object with .text, .language, .segments
    segments = []
    if hasattr(transcription, "segments") and transcription.segments:
        for s in transcription.segments:
            segments.append({
                "start": getattr(s, "start", 0),
                "end":   getattr(s, "end", 0),
                "text":  getattr(s, "text", ""),
            })

    return {
        "text":     transcription.text.strip(),
        "language": getattr(transcription, "language", "en"),
        "segments": segments,
        "provider": "groq-whisper-large-v3",
    }


# ─── Local Whisper (fallback) ─────────────────────────────────────────────────

# Dynamically add winget Gyan.FFmpeg path if present on Windows
_ffmpeg_path = r"C:\Users\dell\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
if os.path.exists(_ffmpeg_path) and _ffmpeg_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] += os.pathsep + _ffmpeg_path

_whisper_model = None


def _get_local_model():
    """Load local whisper 'small' model once (lazy, cached)."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print("[Whisper Local] Loading 'small' model (fallback)...")
        _whisper_model = whisper.load_model("small")
        print("[Whisper Local] Model ready.")
    return _whisper_model


def transcribe_with_local_whisper(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """Fallback: transcribe using local whisper model."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        model = _get_local_model()
        result = model.transcribe(tmp_path, language=None, task="transcribe", fp16=False)
        return {
            "text":     result["text"],
            "language": result["language"],
            "segments": [
                {"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result["segments"]
            ],
            "provider": "local-whisper-small",
        }
    finally:
        os.unlink(tmp_path)


# ─── Public API ───────────────────────────────────────────────────────────────

def transcribe_audio_bytes(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """
    Main entry point for STT transcription.
    1. Tries Groq whisper-large-v3 (fast, cloud, uses GROQ_API_KEY3)
    2. Falls back to local whisper 'small' model if Groq fails
    """
    try:
        result = transcribe_with_groq(audio_bytes, suffix)
        print(f"[STT] Groq transcription OK | lang={result['language']} | chars={len(result['text'])}")
        return result
    except Exception as groq_err:
        print(f"[STT] Groq failed ({groq_err}), falling back to local Whisper...")
        try:
            result = transcribe_with_local_whisper(audio_bytes, suffix)
            print(f"[STT] Local Whisper OK | lang={result['language']}")
            return result
        except Exception as local_err:
            print(f"[STT] Local Whisper also failed: {local_err}")
            return {"text": "", "language": "en", "segments": [], "provider": "failed"}


# Legacy compat — some parts of main.py call transcribe_audio(path)
def transcribe_audio(audio_path: str) -> dict:
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    suffix = "." + audio_path.rsplit(".", 1)[-1] if "." in audio_path else ".wav"
    return transcribe_audio_bytes(audio_bytes, suffix)
