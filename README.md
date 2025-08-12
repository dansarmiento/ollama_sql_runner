# Data-LLM (Ollama SQL Interface)

## Security Notice
This application interacts with an Ollama server, which may be vulnerable to multiple attacks if not updated.
- **CVE-2024-39722 (File Disclosure):** Affects versions before 0.1.46.
- **CVE-2024-39719 (File Disclosure):** Affects versions before 0.1.46.
- **CVE-2024-37032 (Path Traversal):** Affects versions before 0.1.34.
- **CVE-2024-45436 (Zip Extraction):** Affects versions before 0.1.47.

**It is strongly recommended to update your Ollama server to version 0.1.47 or later.**

This application will check the Ollama server version on startup and refuse to run if the version is older than 0.1.46. Updating the Ollama server is the only way to fully resolve the underlying issues.

## Prereqs
- Python 3.10+
- PostgreSQL reachable from this machine
- Ollama installed and running locally
  - https://ollama.com/download
  - Start the server, then pull a model:
    - `ollama pull llama3.2:latest`

## Setup
```bash
git clone <your_repo_or_local_folder_prepared>
cd data-llm
python -m venv .venv
. .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your DB credentials and preferred model
```
Run
```bash
streamlit run app.py
```

Notes
The app only executes read-only SQL. It blocks INSERT/UPDATE/DELETE/ALTER/DROP/CREATE and multi-statement queries.

If the SQL lacks a LIMIT, the app enforces DEFAULT_ROW_LIMIT from .env.

The LLM gets a compact schema summary to improve SQL generation.


---

# prompts.py
```python
SYSTEM_INSTRUCTIONS = """You are a precise SQL copilot. You write correct, minimal SQL for PostgreSQL only.
You must:
- Use only tables and columns that exist in the provided schema.
- Prefer explicit column lists, avoid SELECT * when possible.
- Return **JSON only**, no prose.

Return one of these JSON shapes:

If you need clarification:
{
  "needs_clarification": true,
  "question": "one short clarifying question",
  "reason": "why you need it"
}

If you have enough info to propose SQL:
{
  "needs_clarification": false,
  "sql": "SELECT ...",
  "explanation": "short one-line reason",
  "assumptions": ["list of assumptions you made, if any"]
}
"""

ANALYZE_TEMPLATE = """User request:
{user_request}

Schema (PostgreSQL):
{schema_text}

If unclear, ask exactly one best clarifying question. Otherwise produce SQL.
Respond with valid JSON only."""
