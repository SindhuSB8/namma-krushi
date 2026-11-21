"""Resilient Kannada <-> English translation for farmer conversations."""
from functools import lru_cache
import html
import os
import re

import requests


_TRANSLATION_URL = os.getenv(
    "TRANSLATION_URL", "https://api.mymemory.translated.net/get"
)
_TIMEOUT_SECONDS = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "3"))
_LANGUAGE_CODES = {"Kannada": "kn", "English": "en", "kn": "kn", "en": "en"}
_MAX_CHARS = 450

# --- Kannada -> English retrieval-query lexicon -------------------------------
# Each entry is (kannada_root, english, kind).  Kinds:
#   n   noun / topic   - may be modified by "high" / "low"
#   hi  "high" modifier        lo  "low" modifier
#   neg negation ("do not")    q   question / action words
#   and list conjunction       brk clause boundary
# A root matches a word when the word equals it, or starts with it followed by
# a normal Kannada case/plural ending.  Roots of 4+ characters also match any
# longer inflected form, so short roots such as "ಹೂ" (flower) cannot fire
# inside unrelated words such as "ಹೂಡಿಕೆ" (investment).
_KANNADA_PHRASES = (
    ("ಬಿಳಿ ನೊಣ", "whitefly", "n"),
    ("ಬಿಳಿನೊಣ", "whitefly", "n"),
    ("ಏನು ಮಾಡ", "what should I do", "q"),
    ("ಏನು ಮಾಡಬೇಕು", "what should I do", "q"),
    ("ಕಪ್ಪು ಚುಕ್ಕೆ", "black spots disease", "n"),
    ("ಕಂದು ಚುಕ್ಕೆ", "brown spots disease", "n"),
    ("ಎಲೆ ಸುರುಳಿ", "leaf curl", "n"),
    ("ಹೇಗೆ ಅರ್ಜಿ", "how to apply application", "q"),
)

_KANNADA_WORDS = (
    ("ಟೊಮ್ಯಾಟೊ", "tomato", "n"), ("ಟೊಮ್ಯಾಟೋ", "tomato", "n"), ("ಟೊಮೇಟೊ", "tomato", "n"), ("ಟೊಮೆಟೊ", "tomato", "n"),
    ("ಹಸಿರುಮನೆ", "greenhouse", "n"), ("ಪಾಲಿಹೌಸ್", "polyhouse", "n"),
    ("ಸಬ್ಸಿಡಿ", "subsidy", "n"), ("ಸಹಾಯಧನ", "subsidy", "n"), ("ಯೋಜನೆ", "government scheme", "n"),
    ("ಅರ್ಹತೆ", "eligibility", "n"), ("ಅರ್ಹ", "eligibility", "n"), ("ಅರ್ಜಿ", "apply application", "n"),
    ("ದಾಖಲೆ", "documents", "n"), ("ಪ್ರಯೋಜನ", "benefits", "n"),
    ("ವಿಮೆ", "insurance", "n"), ("ಸಾಲ", "loan credit", "n"), ("ಕ್ರೆಡಿಟ್", "credit", "n"),
    ("ನೀರಾವರಿ", "irrigation", "n"), ("ನೀರು", "water irrigation", "n"),
    ("ತೇವಾಂಶ", "moisture humidity", "n"), ("ಆರ್ದ್ರತೆ", "humidity", "n"),
    ("ತಾಪಮಾನ", "temperature", "n"), ("ಉಷ್ಣತೆ", "temperature", "n"),
    ("ಗಾಳಿಯಾಡುವಿಕೆ", "ventilation", "n"), ("ಗಾಳಿಚಲನೆ", "air movement", "n"), ("ಗಾಳಿ", "air ventilation", "n"),
    ("ಬೆಳಕು", "light", "n"), ("ಒಳಚರಂಡಿ", "drainage", "n"),
    ("ಮಣ್ಣು", "soil root zone", "n"), ("ಬೇರು", "root zone", "n"),
    ("ಗೊಬ್ಬರ", "fertilizer nutrition", "n"), ("ಪೋಷಕಾಂಶ", "nutrition", "n"),
    ("ಗಿಡ", "plant", "n"), ("ಎಲೆ", "leaf", "n"), ("ರೋಗ", "disease", "n"),
    ("ಚುಕ್ಕೆ", "spot disease", "n"), ("ಬಾಡು", "wilt", "n"), ("ಒಣಗ", "wilt dry", "n"),
    ("ಹಳದಿ", "yellow", "n"), ("ಕಪ್ಪು", "black", "n"), ("ಕಂದು", "brown", "n"), ("ಬಿಳಿ", "white", "n"),
    ("ಸುರುಳಿ", "leaf curl", "n"), ("ಬೂಜು", "mold", "n"), ("ಅಚ್ಚು", "mold", "n"),
    ("ಕೀಟನಾಶಕ", "pesticide", "n"), ("ಶಿಲೀಂಧ್ರನಾಶಕ", "fungicide", "n"),
    ("ಕೀಟ", "pest", "n"), ("ಹುಳು", "pest borer", "n"),
    ("ಔಷಧ", "spray treatment", "n"), ("ಸಿಂಪಡ", "spray", "n"), ("ಚಿಕಿತ್ಸೆ", "treatment", "n"),
    ("ನಿಯಂತ್ರ", "control management", "n"), ("ತಡೆ", "prevent", "n"),
    ("ಹೂ", "flower pollination", "n"), ("ಹಣ್ಣು", "fruit", "n"), ("ಇಳುವರಿ", "yield", "n"),
    ("ಬೆಳೆ", "crop grow", "n"), ("ಕೊಯ್ಲು", "harvest", "n"),
    ("ಬೆಲೆ", "price", "n"), ("ಮಾರುಕಟ್ಟೆ", "market", "n"),
    ("ಹೆಚ್ಚು", "high", "hi"), ("ಹೆಚ್ಚಾ", "high", "hi"), ("ಅಧಿಕ", "high", "hi"), ("ಜಾಸ್ತಿ", "high", "hi"),
    ("ಕಡಿಮೆ", "low", "lo"), ("ಕಮ್ಮಿ", "low", "lo"), ("ಕೊರತೆ", "low", "lo"),
    ("ಎಷ್ಟು", "how much", "q"), ("ಹೇಗೆ", "how", "q"), ("ಯಾವಾಗ", "when", "q"),
    ("ಏಕೆ", "why", "q"), ("ಯಾಕೆ", "why", "q"), ("ಏನು", "what", "q"),
    ("ಮತ್ತು", "", "and"), ("ಹಾಗೂ", "", "and"), ("ಹಾಗು", "", "and"),
    ("ಆದರೆ", "", "brk"), ("ಆದ್ದರಿಂದ", "", "brk"), ("ಹಾಗಾದರೆ", "", "brk"),
)

_KANNADA_SUFFIXES = {
    "", "ಗಳು", "ಗಳ", "ಗಳನ್ನು", "ಗಳಲ್ಲಿ", "ಗಳಿಗೆ", "ಯ", "ಯು", "ಯಲ್ಲಿ", "ಯನ್ನು", "ಯೂ", "ವು", "ವನ್ನು",
    "ವಿನ", "ವಿಗೆ", "ದ", "ದಲ್ಲಿ", "ದಿಂದ", "ದ್ದು", "ಅನ್ನು", "ನ್ನು", "ಲ್ಲಿ", "ಕ್ಕೆ", "ಕ್ಕೂ", "ಗೆ", "ಇಂದ",
    "ದೆ", "ವೂ", "ಕ್ಕಿ", "ತೆ",
}
_NEGATION_RE = re.compile(r"ಬೇಡ(?!ಿಕೆ)")
_CLAUSE_SPLIT_RE = re.compile(r"[,.;:!?।\n]+")


def _word_matches(word, root):
    if word == root:
        return True
    if not word.startswith(root):
        return False
    return len(root) >= 4 or word[len(root):] in _KANNADA_SUFFIXES


def _kannada_items(clause):
    """Turn one clause into ordered (kind, english) items."""
    words = [w for w in re.split(r"\s+", clause.strip()) if w]
    items, i = [], 0
    while i < len(words):
        word = words[i]
        matched = False
        # Two-word phrases first (e.g. "ಬಿಳಿ ನೊಣ", "ಏನು ಮಾಡಬೇಕು").
        if i + 1 < len(words):
            for root, english, kind in _KANNADA_PHRASES:
                parts = root.split(" ")
                if len(parts) == 2 and words[i].startswith(parts[0]) and words[i + 1].startswith(parts[1]):
                    items.append((kind, english))
                    i += 2
                    matched = True
                    break
        if matched:
            continue
        if _NEGATION_RE.search(word):
            items.append(("neg", "do not"))
        elif word in ("ಇಲ್ಲ", "ಇಲ್ಲದೆ"):
            items.append(("neg", "no"))
        else:
            for root, english, kind in _KANNADA_WORDS:
                if _word_matches(word, root):
                    items.append((kind, english))
                    break
            else:
                items.extend(("lat", token.lower()) for token in re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", word))
        i += 1
    return items


def _attach_modifiers(items):
    """Bind high/low to the noun(s) they describe, so meaning is not lost.

    Kannada puts the modifier after its noun ("ಆರ್ದ್ರತೆ ಹೆಚ್ಚು" = humidity
    high); a preceding modifier is also handled.  "A and B high" modifies both.
    """
    nouns = {"n", "lat"}
    prefix = {}   # item index -> "high" / "low"
    used = set()
    for idx, (kind, english) in enumerate(items):
        if kind not in ("hi", "lo"):
            continue
        used.add(idx)
        word = "high" if kind == "hi" else "low"
        targets, j = [], idx - 1
        while j >= 0:
            if items[j][0] in nouns and j not in prefix:
                targets.append(j)
                # continue only through an explicit list: "A and B high"
                if j >= 2 and items[j - 1][0] == "and" and items[j - 2][0] in nouns:
                    j -= 2
                    continue
                break
            if items[j][0] == "and":
                j -= 1
                continue
            break
        if not targets:  # leading modifier: "high humidity"
            j = idx + 1
            if j < len(items) and items[j][0] in nouns and j not in prefix:
                targets.append(j)
        for t in targets:
            prefix[t] = word
        if not targets:
            prefix[idx] = word  # keep a bare "high"/"low" rather than drop it
    out = [english for kind, english in items if kind == "neg"][:1]  # "do not ..." leads the clause
    for idx, (kind, english) in enumerate(items):
        if kind == "neg":
            continue
        if idx in used and idx not in prefix:
            continue
        if kind in ("and",):
            continue
        if idx in prefix and idx in used:
            out.append(prefix[idx])
        elif idx in prefix:
            out.append(f"{prefix[idx]} {english}")
        elif english:
            out.append(english)
    return out


def _code(language):
    try:
        return _LANGUAGE_CODES[language]
    except KeyError as exc:
        raise ValueError(f"Unsupported translation language: {language}") from exc


def _chunks(text):
    """Split long answers safely for the public translation endpoint."""
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        words = re.findall(r"\S+\s*", line) or [line]
        for word in words:
            if current and len(current) + len(word) > _MAX_CHARS:
                chunks.append(current)
                current = ""
            current += word
    if current:
        chunks.append(current)
    return chunks or [text]


@lru_cache(maxsize=512)
def _translate_piece(text, source_code, target_code):
    try:
        response = requests.get(
            _TRANSLATION_URL,
            params={"q": text, "langpair": f"{source_code}|{target_code}"},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("responseStatus") != 200:
            return text, False
        translated = html.unescape(payload.get("responseData", {}).get("translatedText", "")).strip()
        if not translated or translated.startswith("MYMEMORY WARNING"):
            return text, False
        return translated, True
    except (requests.RequestException, ValueError, TypeError):
        return text, False


def translate(text, source_language, target_language):
    """Translate text and return ``(translated_text, succeeded)``.

    A failed translation is deliberately non-fatal. The chatbot can still
    return the evidence-backed English answer instead of failing the farmer's
    whole request.
    """
    text = (text or "").strip()
    source_code, target_code = _code(source_language), _code(target_language)
    if not text or source_code == target_code:
        return text, True

    translated_chunks = []
    for chunk in _chunks(text):
        translated, succeeded = _translate_piece(chunk, source_code, target_code)
        if not succeeded:
            return text, False
        translated_chunks.append(translated)
    return "".join(translated_chunks), True


def translate_rag_query_to_english(text):
    """Translate a Kannada farm question into a fast English retrieval query.

    Domain terms are mapped locally (no network wait) while keeping the parts
    that change the advice: high/low direction, negation ("do not water"),
    symptoms and the requested action.  Questions with no recognised terms get
    one short provider attempt; if that also fails the caller is told
    (``False``) so it can say so honestly instead of guessing a topic.
    """
    text = (text or "").strip()
    phrases = []
    for clause in _CLAUSE_SPLIT_RE.split(text):
        if not clause.strip():
            continue
        # A clause boundary word splits the clause so "low temperature but
        # high humidity" does not bind both modifiers to one noun.
        pieces = re.split(r"\s+(?=ಆದರೆ|ಆದ್ದರಿಂದ|ಹಾಗಾದರೆ)", clause.strip())
        for piece in pieces:
            phrases.extend(_attach_modifiers(_kannada_items(piece)))
    if phrases:
        deduped = [p for k, p in enumerate(phrases) if k == 0 or p != phrases[k - 1]]
        return " ".join(deduped), True

    translated, succeeded = translate(text, "Kannada", "English")
    if succeeded:
        return translated, True
    return "", False
