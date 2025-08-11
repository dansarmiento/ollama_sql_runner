import os
import json
import requests
from typing import Dict, Any
from prompts import SYSTEM_INSTRUCTIONS, ANALYZE_TEMPLATE

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

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
