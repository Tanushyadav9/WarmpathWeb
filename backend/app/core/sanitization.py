"""
Input sanitization utilities for XSS and injection prevention.
"""
import html
import re
from typing import Optional


DANGEROUS_PATTERNS = [
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*object[^>]*>.*?<\s*/\s*object\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*embed[^>]*>.*?<\s*/\s*embed\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:\s*", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"data:\s*text/html", re.IGNORECASE),
]


def sanitize_text(text: Optional[str], escape_html: bool = False) -> Optional[str]:
    """
    Sanitizes string inputs against Cross-Site Scripting (XSS) and dangerous payloads.
    - Removes null bytes
    - Strips script and iframe blocks
    - Disarms javascript: URIs and DOM event handlers
    - Optionally escapes HTML entities
    """
    if text is None:
        return None

    # Strip null bytes
    cleaned = text.replace("\0", "").strip()

    # Disarm dangerous script & DOM event handlers
    for pattern in DANGEROUS_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    if escape_html:
        cleaned = html.escape(cleaned)

    return cleaned


def is_safe_identifier(value: str) -> bool:
    """Checks if an alphanumeric identifier or code is safe from SQL/path injection."""
    if not value or len(value) > 100:
        return False
    # Allow alphanumeric, dashes, underscores, and dots
    return bool(re.match(r"^[a-zA-Z0-9_\-\.]+$", value))
