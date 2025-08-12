import os
import json
import requests
import re
from typing import Dict, Any
from urllib.parse import urlparse
from packaging import version
from prompts import SYSTEM_INSTRUCTIONS, ANALYZE_TEMPLATE

# --- Security Mitigations ---
# This application requires an updated Ollama server to protect against several
# known vulnerabilities. The version check below is the primary mitigation.
#
# - CVE-2024-39721 (DoS): Fixed in 0.1.34
# - CVE-2024-39720 (DoS): Fixed in 0.1.46
# - CVE-2024-39722 (File Disclosure): Fixed in 0.1.46
# - CVE-2024-39719 (File Disclosure): Fixed in 0.1.46
# - CVE-2024-37032 (Path Traversal): Fixed in 0.1.34
# - CVE-2024-45436 (Zip Extraction): Fixed in 0.1.47
#
# It is strongly recommended to update the Ollama server to version 0.1.47 or later.

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MIN_OLLAMA_VERSION = "0.1.46"

def check_ollama_version():
    """Checks if the Ollama server version is sufficient."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/version", timeout=5)
        resp.raise_for_status()
        server_version_str = resp.json().get("version")
        if not server_version_str:
            raise ValueError("Could not determine Ollama server version from response.")

        server_version = version.parse(server_version_str)
        required_version = version.parse(MIN_OLLAMA_VERSION)

        if server_version < required_version:
            raise RuntimeError(
                f"Your Ollama server version ({server_version}) is outdated. "
                f"Please upgrade to version {MIN_OLLAMA_VERSION} or later to mitigate "
                f"known vulnerabilities (e.g., CVE-2024-39721, CVE-2024-39720)."
            )
    except requests.RequestException as e:
        raise RuntimeError(
            "Could not connect to Ollama server to verify its version. "
            "Please ensure the Ollama server is running and accessible."
        ) from e
    except ValueError as e:
        raise RuntimeError(f"Error checking Ollama version: {e}") from e

check_ollama_version()
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
