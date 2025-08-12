import os
import json
import requests
import re
from typing import Dict, Any
from urllib.parse import urlparse
from prompts import SYSTEM_INSTRUCTIONS, ANALYZE_TEMPLATE

# --- Security Mitigations ---
# These mitigations are for CVE-2024-37032 and CVE-2024-45436.
# It is strongly recommended to update the Ollama server to version 0.1.47 or later.

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

# Validate OLLAMA_BASE_URL to prevent SSRF-like attacks
parsed_url = urlparse(OLLAMA_BASE)
if parsed_url.scheme not in ["http", "https"]:
    raise ValueError("Invalid OLLAMA_BASE_URL scheme. Only 'http' and 'https' are allowed.")
if not parsed_url.hostname or re.match(r"^[a-zA-Z0-9.-]+$", parsed_url.hostname) is None:
    raise ValueError("Invalid OLLAMA_BASE_URL hostname.")

# Validate MODEL to prevent path traversal (CVE-2024-37032)
if ".." in MODEL or "/" in MODEL:
    raise ValueError("Invalid characters in OLLAMA_MODEL. Path traversal is not allowed.")

def _chat(messages):
    url = f"{OLLAMA_BASE}/api/chat"
    resp = requests.post(url, json={"model": MODEL, "messages": messages, "stream": False}, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Ollama returns a final message at data["message"]["content"]
    return data["message"]["content"]

def analyze_request(user_request: str, schema_text: str) -> Dict[str, Any]:
    content = ANALYZE_TEMPLATE.format(user_request=user_request, schema_text=schema_text)
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": content},
    ]
    raw = _chat(messages)
    # Try to extract JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to find JSON block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
        raise
