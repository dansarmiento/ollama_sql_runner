import os
import json
import requests
import re
import time
from typing import Dict, Any
from urllib.parse import urlparse
from packaging import version

from prompts import SYSTEM_INSTRUCTIONS, ANALYZE_TEMPLATE
from exceptions import (
    OllamaConnectionError,
    OllamaVersionError,
    OllamaRequestError,
    LLMResponseError,
)

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
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
MIN_OLLAMA_VERSION = "0.1.46"

def check_ollama_version():
    """Checks if the Ollama server version is sufficient."""
    try:
        data = _make_ollama_request("GET", "/api/version", timeout=5)
        server_version_str = data.get("version")
        if not server_version_str:
            raise OllamaVersionError("Could not determine Ollama server version from response.")

        server_version = version.parse(server_version_str)
        required_version = version.parse(MIN_OLLAMA_VERSION)

        if server_version < required_version:
            raise OllamaVersionError(
                f"Your Ollama server version ({server_version}) is outdated. "
                f"Please upgrade to version {MIN_OLLAMA_VERSION} or later to mitigate "
                f"known vulnerabilities (e.g., CVE-2024-39721, CVE-2024-39720)."
            )
    except OllamaRequestError as e:
        # Re-raise connection errors from the version check as a more specific type
        raise OllamaConnectionError(
            "Could not connect to Ollama server to verify its version. "
            "Please ensure the Ollama server is running and accessible."
        ) from e
    except (ValueError, OllamaVersionError) as e:
        # Re-raise other version-check errors
        raise OllamaVersionError(f"Error checking Ollama version: {e}") from e

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

# --- Model Allowlist ---
# To prevent loading of untrusted models, we can restrict which models the
# application is allowed to use. If the ALLOWED_OLLAMA_MODELS environment
# variable is set, we enforce that the requested model is in the list.
ALLOWED_MODELS_STR = os.getenv("ALLOWED_OLLAMA_MODELS")
if ALLOWED_MODELS_STR:
    allowed_models = [m.strip() for m in ALLOWED_MODELS_STR.split(",")]
    # The model name can be e.g., "llama3.2:latest". We check the base name.
    base_model_name = MODEL.split(":")[0]
    if base_model_name not in allowed_models:
        raise ValueError(
            f"Model '{MODEL}' is not in the list of allowed models. "
            f"Allowed models are: {', '.join(allowed_models)}"
        )

# --- Centralized Request Function with Endpoint Guardrails ---
# To prevent model exfiltration or other unauthorized actions, all requests to the
# Ollama server must go through this centralized function, which enforces that
# only safe, allowed endpoints and methods are used.
BLOCKED_OLLAMA_ENDPOINTS = ["push", "create", "delete", "copy", "blobs"]
ALLOWED_OLLAMA_METHODS = ["GET", "POST"]

def _make_ollama_request(method: str, endpoint: str, **kwargs):
    """A centralized and guarded function for making requests to Ollama."""
    if method.upper() not in ALLOWED_OLLAMA_METHODS:
        raise PermissionError(f"HTTP method '{method}' is not allowed.")

    # Prevent access to any sensitive or dangerous endpoints
    for blocked in BLOCKED_OLLAMA_ENDPOINTS:
        if f"/api/{blocked}" in endpoint:
            raise PermissionError(f"Access to the Ollama endpoint '{endpoint}' is forbidden.")

    url = f"{OLLAMA_BASE}{endpoint}"

    # Set default timeout if not provided. The timeout for the version check
    # is intentionally short (5s) and should not be overridden by the default.
    kwargs.setdefault("timeout", OLLAMA_TIMEOUT)

    t0 = time.time()
    try:
        resp = requests.request(method, url, **kwargs)
        resp.raise_for_status()
        dt = time.time() - t0
        print(f"Ollama request to {endpoint} took {dt:.2f}s (timeout={kwargs.get('timeout')}s)")
        return resp.json()
    except requests.exceptions.Timeout as e:
        dt = time.time() - t0
        print(f"Ollama request to {endpoint} timed out after {dt:.2f}s (timeout={kwargs.get('timeout')}s)")
        raise OllamaRequestError(f"Request to Ollama timed out: {e}") from e
    except requests.exceptions.RequestException as e:
        dt = time.time() - t0
        print(f"Ollama request to {endpoint} failed after {dt:.2f}s (timeout={kwargs.get('timeout')}s)")
        raise OllamaRequestError(f"Request to Ollama failed: {e}") from e


def _chat(messages):
    try:
        data = _make_ollama_request(
            "POST",
            "/api/chat",
            json={"model": MODEL, "messages": messages, "stream": False},
        )
        # Ollama returns a final message at data["message"]["content"]
        return data["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMResponseError(f"Received an unexpected response structure from Ollama: {e}") from e


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
    except json.JSONDecodeError as e:
        # Attempt to find JSON block
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except json.JSONDecodeError:
                pass # Fall through to raise
        raise LLMResponseError(f"The LLM returned a response that could not be parsed as JSON. Raw response:\n{raw}") from e
