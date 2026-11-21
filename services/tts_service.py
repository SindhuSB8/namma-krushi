"""High-quality native neural text-to-speech engine for advisory answers."""
import asyncio
import base64
import io
import json
import logging
import re
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)

# Native Indian voices (Microsoft Azure Neural). Sapna is a native Kannada
# voice; it is used for farmer-facing responses rather than browser defaults.
KAN_VOICE = "kn-IN-SapnaNeural"
ENG_VOICE = "en-IN-NeerjaNeural"

# Only successful audio is retained.  A failed remote request must never be
# cached: otherwise a short network outage leaves a long-running Streamlit
# session permanently stuck on the low-quality browser fallback.
_AUDIO_CACHE = OrderedDict()
_AUDIO_CACHE_LOCK = Lock()
_AUDIO_CACHE_SIZE = 32


def _plain_speech_text(text):
    """Remove Markdown syntax so the text reads naturally."""
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text or "")
    text = re.sub(r"[*_`#>]", "", text)
    text = re.sub(r"\n{2,}", ". ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


async def _edge_tts_generate_async(plain_text, voice):
    """Generate audio bytes using edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(plain_text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


def _gtts_generate(plain_text, language):
    """Fallback generator using Google Translate TTS (gTTS)."""
    import gtts

    lang_code = "kn" if language == "Kannada" else "en"
    tts = gtts.gTTS(plain_text, lang=lang_code)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


def synthesize_audio_bytes(plain_text, language="English"):
    """Synthesize authentic native speech bytes (MP3).

    Tries edge-tts (neural Kannada) first, then gTTS (Google Kannada).
    """
    if not plain_text or not plain_text.strip():
        return None

    cache_key = (plain_text, language)
    with _AUDIO_CACHE_LOCK:
        cached = _AUDIO_CACHE.get(cache_key)
        if cached:
            _AUDIO_CACHE.move_to_end(cache_key)
            return cached

    voice = KAN_VOICE if language == "Kannada" else ENG_VOICE

    # 1. Try Microsoft Edge Neural TTS
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    data = executor.submit(asyncio.run, _edge_tts_generate_async(plain_text, voice)).result()
            else:
                data = loop.run_until_complete(_edge_tts_generate_async(plain_text, voice))
        except RuntimeError:
            data = asyncio.run(_edge_tts_generate_async(plain_text, voice))

        if data and len(data) > 0:
            return _cache_audio(cache_key, data)
    except Exception as exc:
        logger.warning("edge-tts synthesis failed: %s", exc)

    # 2. Fallback to Google Translate Kannada TTS
    try:
        data = _gtts_generate(plain_text, language)
        if data and len(data) > 0:
            return _cache_audio(cache_key, data)
    except Exception as exc:
        logger.warning("gTTS synthesis failed: %s", exc)

    return None


def _cache_audio(cache_key, data):
    """Cache successful MP3 bytes without retaining provider failures."""
    with _AUDIO_CACHE_LOCK:
        _AUDIO_CACHE[cache_key] = data
        _AUDIO_CACHE.move_to_end(cache_key)
        while len(_AUDIO_CACHE) > _AUDIO_CACHE_SIZE:
            _AUDIO_CACHE.popitem(last=False)
    return data


def synthesize_audio_base64(plain_text, language="English"):
    """Return base64 encoded audio, retrying later if synthesis is unavailable."""
    data = synthesize_audio_bytes(plain_text, language)
    if data:
        return base64.b64encode(data).decode("ascii")
    return None


def _speech_controls_html(text, language, labels, autoplay=False):
    """Build a self-contained control bar with neural Indian speech."""
    plain_text = _plain_speech_text(text)
    # Always supply the verified Kannada neural MP3. Browser speech synthesis
    # has no Kannada voice on many Windows installs and otherwise falls back
    # to an English accent.
    browser_native = False
    audio_base64 = synthesize_audio_base64(plain_text, language)

    payload = json.dumps(
        {
            "text": plain_text,
            "language": "kn-IN" if language == "Kannada" else "en-IN",
            "labels": labels,
            "autoplay": bool(autoplay),
            "audio_base64": audio_base64 or "",
            "browser_native": browser_native,
            "unavailable": labels.get("unavailable", labels["unsupported"]),
        },
        ensure_ascii=False,
    )
    encoded_payload = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    html_language = "kn" if language == "Kannada" else "en"
    return f"""
<!doctype html>
<html lang="{html_language}">
<head>
<meta charset="utf-8">
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #fffaf0; color: #26301f; font-family: Inter, "Noto Sans Kannada", system-ui, sans-serif; }}
  .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; min-height: 48px; }}
  button {{
    border: 2px solid currentColor; border-radius: .7rem; padding: .55rem .8rem;
    background: #fffaf0; color: #26301f; font: inherit; font-weight: 650; cursor: pointer;
  }}
  button.primary {{ background: #16803c; border-color: #16803c; color: white; }}
  button:disabled {{ cursor: not-allowed; opacity: .45; }}
  button:focus-visible {{ outline: 3px solid #ff4b4b; outline-offset: 2px; }}
  #status {{ color: #5b6552; font-size: .86rem; opacity: .8; }}
</style>
</head>
<body>
  <div id="controls" class="controls" role="group">
    <button id="listen" class="primary" type="button">🔊 <span></span></button>
    <button id="pause" type="button" disabled>⏸ <span></span></button>
    <button id="resume" type="button" disabled>▶ <span></span></button>
    <button id="stop" type="button" disabled>⏹ <span></span></button>
    <span id="status" role="status" aria-live="polite"></span>
  </div>
  <audio id="player" preload="none"></audio>
<script>
(() => {{
  const bytes = Uint8Array.from(atob("{encoded_payload}"), character => character.charCodeAt(0));
  const config = JSON.parse(new TextDecoder().decode(bytes));
  const controls = document.getElementById("controls");
  const listen = document.getElementById("listen");
  const pause = document.getElementById("pause");
  const resume = document.getElementById("resume");
  const stop = document.getElementById("stop");
  const status = document.getElementById("status");
  const player = document.getElementById("player");
  const synth = window.speechSynthesis;

  controls.setAttribute("aria-label", config.labels.controls);
  listen.querySelector("span").textContent = config.labels.listen;
  pause.querySelector("span").textContent = config.labels.pause;
  resume.querySelector("span").textContent = config.labels.resume;
  stop.querySelector("span").textContent = config.labels.stop;

  let isNeural = !config.browser_native && Boolean(config.audio_base64 && config.audio_base64.length > 0);
  let utterance = null;

  if (isNeural) {{
    player.src = "data:audio/mp3;base64," + config.audio_base64;
  }}

  function setState(state) {{
    const active = state === "speaking" || state === "paused";
    pause.disabled = state !== "speaking";
    resume.disabled = state !== "paused";
    stop.disabled = !active;
    status.textContent = state === "paused" ? config.labels.paused : "";
  }}

  function start() {{
    if (isNeural) {{
      player.currentTime = 0;
      player.play().then(() => {{
        setState("speaking");
      }}).catch(() => {{
        startFallback();
      }});
      return;
    }}
    startFallback();
  }}

  function availableVoice() {{
    const voices = synth.getVoices();
    const exact = voices.find(v => v.lang.toLowerCase() === config.language.toLowerCase());
    return exact || voices.find(v => v.lang.toLowerCase().startsWith(config.language.slice(0, 2).toLowerCase()));
  }}

  function waitForVoice() {{
    const voice = availableVoice();
    if (voice || !config.language.toLowerCase().startsWith("kn")) return Promise.resolve(voice);
    return new Promise(resolve => {{
      const timeout = window.setTimeout(() => {{
        synth.removeEventListener("voiceschanged", onVoicesChanged);
        resolve(availableVoice());
      }}, 1200);
      const onVoicesChanged = () => {{
        const loaded = availableVoice();
        if (loaded) {{
          window.clearTimeout(timeout);
          synth.removeEventListener("voiceschanged", onVoicesChanged);
          resolve(loaded);
        }}
      }};
      synth.addEventListener("voiceschanged", onVoicesChanged);
    }});
  }}

  async function startFallback() {{
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {{
      status.textContent = config.labels.unsupported;
      return;
    }}
    synth.cancel();
    const selectedVoice = await waitForVoice();
    // A browser may populate its voices asynchronously.  Never choose the
    // English default if no Kannada voice is present after that wait.
    if (!selectedVoice && config.language.toLowerCase().startsWith("kn")) {{
      status.textContent = config.labels.unavailable;
      return;
    }}
    utterance = new SpeechSynthesisUtterance(config.text);
    utterance.lang = config.language;
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.onstart = () => setState("speaking");
    utterance.onpause = () => setState("paused");
    utterance.onresume = () => setState("speaking");
    utterance.onend = () => setState("idle");
    utterance.onerror = event => {{
      setState("idle");
      if (event.error !== "canceled" && event.error !== "interrupted") status.textContent = config.labels.unsupported;
    }};
    synth.speak(utterance);
  }}

  player.onplay = () => setState("speaking");
  player.onpause = () => {{
    if (!player.ended && player.currentTime > 0) {{
      setState("paused");
    }}
  }};
  player.onended = () => setState("idle");
  player.onerror = () => {{
    setState("idle");
    startFallback();
  }};

  listen.addEventListener("click", start);
  pause.addEventListener("click", () => {{
    if (isNeural && !player.paused) {{
      player.pause();
      setState("paused");
    }} else if (synth && synth.speaking && !synth.paused) {{
      synth.pause();
      setState("paused");
    }}
  }});
  resume.addEventListener("click", () => {{
    if (isNeural && player.paused) {{
      player.play();
      setState("speaking");
    }} else if (synth && synth.paused) {{
      synth.resume();
      setState("speaking");
    }}
  }});
  stop.addEventListener("click", () => {{
    if (isNeural) {{
      player.pause();
      player.currentTime = 0;
    }}
    if (synth) {{
      synth.cancel();
    }}
    setState("idle");
  }});

  window.addEventListener("beforeunload", () => {{
    if (isNeural) player.pause();
    if (synth) synth.cancel();
  }});

  setState("idle");
  if (config.autoplay) window.setTimeout(start, 150);
}})();
</script>
</body>
</html>
"""


def browser_speak_component(text, language, labels, autoplay=False):
    """Render voice controls without Streamlit's dark native audio player."""
    import streamlit as st

    st.iframe(
        _speech_controls_html(text, language, labels, autoplay),
        height=58,
        width="stretch",
    )
