# Data-LLM (Ollama SQL Interface)

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
