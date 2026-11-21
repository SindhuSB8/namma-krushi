"""Input validation for profile and account fields.

Functions return ``(clean_value, error_key)``; ``error_key`` is a translation
key (None when the value is acceptable) so the page can show it in the
farmer's language.
"""
import re
import unicodedata

NAME_MIN, NAME_MAX = 2, 60
PASSWORD_MIN, PASSWORD_MAX = 6, 72   # 72 bytes is bcrypt's input limit
LANGUAGES = ("English", "Kannada")


def clean_name(raw):
    """Collapse whitespace; require 2-60 characters, at least one letter, no control characters."""
    name = re.sub(r"\s+", " ", unicodedata.normalize("NFC", raw or "")).strip()
    if not name:
        return "", "profile_name_empty"
    if any(unicodedata.category(c).startswith("C") for c in name):
        return name, "profile_name_invalid"
    if not (NAME_MIN <= len(name) <= NAME_MAX) or not any(c.isalpha() for c in name):
        return name, "profile_name_invalid"
    return name, None


def check_new_password(old, new):
    """Return an error key for an unacceptable new password, else None."""
    if len(new or "") < PASSWORD_MIN:
        return "password_too_short"
    if len((new or "").encode("utf-8")) > PASSWORD_MAX:
        return "password_too_long"
    if new == old:
        return "password_same"
    return None


def check_language(value):
    return value if value in LANGUAGES else None
