"""
Local Whisper Voice Transcription — fully offline, no API key needed.
Supports Urdu, English, and mixed input.
Model: 'small' (244MB) — best balance for Urdu accuracy.
"""

import os
import tempfile

# Dynamically add winget Gyan.FFmpeg path if present on Windows
ffmpeg_path = r"C:\Users\dell\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.path.pathsep + ffmpeg_path

# Model is loaded lazily on first call to avoid slow startup
_whisper_model = None


def _get_model():
    """Load whisper model once (downloads on first run, then cached)."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print("[Whisper] Loading 'small' model (best for Urdu)...")
        _whisper_model = whisper.load_model("small")
        print("[Whisper] Model ready.")
    return _whisper_model


def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe an audio file. Whisper auto-detects language (Urdu/English).
    Returns: {"text": ..., "language": "ur"|"en", "segments": [...]}
    """
    model = _get_model()
    result = model.transcribe(
        audio_path,
        language=None,       # auto-detect Urdu / English
        task="transcribe",   # use "translate" to force English output
        fp16=False           # set True if you have a GPU
    )
    return {
        "text": result["text"],
        "language": result["language"],
        "segments": [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in result["segments"]
        ]
    }


def transcribe_audio_bytes(audio_bytes: bytes, suffix: str = ".wav") -> dict:
    """Transcribe from raw audio bytes (e.g. from a file upload)."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        return transcribe_audio(tmp_path)
    finally:
        os.unlink(tmp_path)
