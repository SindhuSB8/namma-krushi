"""Local speech-to-text using faster-whisper with Render-safe fallback."""
import logging
import os
import re
import tempfile
from functools import lru_cache

logger = logging.getLogger(__name__)

# Initial prompt in Kannada script to force Whisper to output Kannada script (\u0C80-\u0CFF)
# instead of hallucinating Devanagari/Hindi script (\u0900-\u097F).
KAN_INITIAL_PROMPT = "ಕನ್ನಡ ಕೃಷಿ ಟೊಮ್ಯಾಟೊ ರೋಗ ಹಸಿರುಮನೆ ನೀರಾವರಿ ಕ್ರಿಮಿನಾಶಕ ಸಲಹೆ"
ENG_INITIAL_PROMPT = "Tomato greenhouse cultivation disease pest advisory"


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load and cache the WhisperModel. Auto-detect CUDA vs CPU."""
    from faster_whisper import WhisperModel
    from config import WHISPER_MODEL

    device, compute = "cpu", "int8"
    try:
        import torch
        if torch.cuda.is_available():
            device, compute = "cuda", "float16"
    except Exception:
        pass
    logger.info("Loading faster-whisper model=%s device=%s compute=%s", WHISPER_MODEL, device, compute)
    return WhisperModel(WHISPER_MODEL, device=device, compute_type=compute)


def _clean_devanagari(text):
    """Remove stray Devanagari script characters (\u0900-\u097F) if Whisper hallucinated Hindi."""
    return re.sub(r'[\u0900-\u097F]+', '', text).strip()


def transcribe(audio_bytes, language="English"):
    """Transcribe recorded audio bytes to text.

    Returns (transcript, error_message).
    - On success: ("transcribed text", None)
    - On failure: ("", "user-facing error message")
    """
    from config import ENABLE_WHISPER

    if not ENABLE_WHISPER:
        error_key = "voice_unavailable_render"
        return "", error_key

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = _load_model()
        is_kan = (language == "Kannada")
        lang_code = "kn" if is_kan else "en"
        prompt = KAN_INITIAL_PROMPT if is_kan else ENG_INITIAL_PROMPT

        # vad_filter=True prevents noise/silence hallucination
        # initial_prompt locks the output script into Kannada
        segments, _ = model.transcribe(
            tmp_path,
            language=lang_code,
            task="transcribe",
            initial_prompt=prompt,
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False
        )

        transcript = " ".join(seg.text for seg in segments).strip()

        if is_kan:
            transcript = _clean_devanagari(transcript)

        return transcript, None

    except Exception as exc:
        logger.exception("Voice transcription failed")
        error_key = "voice_unavailable"
        return "", error_key

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
