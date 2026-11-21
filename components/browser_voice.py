"""Browser speech-recognition component with no server-side audio dependency."""
from pathlib import Path

import streamlit.components.v1 as components


_voice_input = components.declare_component(
    "browser_voice_input", path=str(Path(__file__).with_name("browser_voice_frontend"))
)


def voice_input(
    language,
    start_label,
    stop_label,
    unsupported_label,
    listening_label,
    error_label,
    key,
    kannada_voice_unavailable_label="",
    conversation_mode=False,
    assistant_text="",
    assistant_audio_base64="",
    speak_response=False,
):
    """Return a browser dictation event, or ``None`` until the farmer speaks.

    Chrome and Edge provide the Web Speech API directly in the browser. This
    keeps Kannada/English dictation available when a hosted server cannot load
    a Whisper model or native audio libraries.
    """
    return _voice_input(
        language="kn-IN" if language == "Kannada" else "en-IN",
        start_label=start_label,
        stop_label=stop_label,
        unsupported_label=unsupported_label,
        listening_label=listening_label,
        error_label=error_label,
        kannada_voice_unavailable_label=kannada_voice_unavailable_label,
        conversation_mode=conversation_mode,
        assistant_text=assistant_text,
        assistant_audio_base64=assistant_audio_base64,
        speak_response=speak_response,
        key=key,
        default=None,
    )
