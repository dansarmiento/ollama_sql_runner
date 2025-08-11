import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from schema_cache import summarize_schema
from llm import analyze_request
from sql_exec import run_select
from guardrails import is_safe_select, enforce_limit

load_dotenv()

st.set_page_config(page_title="Data-LLM", page_icon="🧠", layout="wide")
st.title("Data-LLM • Natural Language → PostgreSQL")
st.caption("Powered by Ollama and PostgreSQL")

with st.sidebar:
    st.header("Settings")
    if st.button("Refresh schema summary"):
        st.session_state.pop("schema_text", None)
    default_limit = int(os.getenv("DEFAULT_ROW_LIMIT", "500"))
    user_default_limit = st.number_input("Default LIMIT", min_value=10, max_value=100000, value=default_limit, step=10)

    st.divider()
    st.write("Model:", os.getenv("OLLAMA_MODEL", "llama3.2:latest"))
    st.write("Ollama:", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    st.write("DB:", f"{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}")

def get_schema_text():
    if "schema_text" not in st.session_state:
        with st.spinner("Loading schema summary..."):
            st.session_state["schema_text"] = summarize_schema(max_columns_per_table=30, include_row_counts=False)
    return st.session_state["schema_text"]

# Conversation state
if "clarification_needed" not in st.session_state:
    st.session_state["clarification_needed"] = False
if "pending_request" not in st.session_state:
    st.session_state["pending_request"] = ""
if "clarifying_question" not in st.session_state:
    st.session_state["clarifying_question"] = ""
if "conversation_notes" not in st.session_state:
    st.session_state["conversation_notes"] = []

st.subheader("Ask for data")
user_request = st.text_area("Type your request", placeholder="Example: Show me all new customers from last month", height=100)

col1, col2 = st.columns([1,1])
with col1:
    go_btn = st.button("Analyze with AI", type="primary")
with col2:
    clear_btn = st.button("Reset conversation")

if clear_btn:
    st.session_state["clarification_needed"] = False
    st.session_state["pending_request"] = ""
    st.session_state["clarifying_question"] = ""
    st.session_state["conversation_notes"] = []
    st.experimental_rerun()

schema_text = get_schema_text()

if go_btn and user_request.strip():
    st.session_state["pending_request"] = user_request.strip()
    with st.spinner("Thinking with Ollama..."):
        result = analyze_request(st.session_state["pending_request"], schema_text)
    if result.get("needs_clarification"):
        st.session_state["clarification_needed"] = True
        st.session_state["clarifying_question"] = result.get("question", "")
        st.session_state["conversation_notes"].append({"role": "assistant", "question": st.session_state["clarifying_question"]})
    else:
        st.session_state["clarification_needed"] = False
        st.session_state["clarifying_question"] = ""
        st.session_state["conversation_notes"].append({"role": "assistant", "sql": result.get("sql",""), "explanation": result.get("explanation",""), "assumptions": result.get("assumptions", [])})
    st.experimental_rerun()

if st.session_state["clarification_needed"]:
    st.info("Clarification needed")
    st.write(st.session_state["clarifying_question"])
    clarify = st.text_input("Your answer")
    c1, c2 = st.columns([1,3])
    with c1:
        submit_clarify = st.button("Submit clarification", use_container_width=True)
    if submit_clarify and clarify.strip():
        # Merge clarification into the original request
        merged = f"{st.session_state['pending_request']}\n\nUser clarification: {clarify.strip()}"
        with st.spinner("Updating with clarification..."):
            result = analyze_request(merged, schema_text)
        st.session_state["conversation_notes"].append({"role": "user", "answer": clarify.strip()})
        if result.get("needs_clarification"):
            # Still unclear, replace question and ask again
            st.session_state["clarifying_question"] = result.get("question", "")
        else:
            st.session_state["clarification_needed"] = False
            st.session_state["clarifying_question"] = ""
            st.session_state["conversation_notes"].append({"role": "assistant", "sql": result.get("sql",""), "explanation": result.get("explanation",""), "assumptions": result.get("assumptions", [])})
        st.experimental_rerun()

# Show the latest proposed SQL (if any)
latest_sql = None
for item in reversed(st.session_state["conversation_notes"]):
    if item.get("sql"):
        latest_sql = item["sql"]
        latest_expl = item.get("explanation","")
        latest_assumptions = item.get("assumptions", [])
        break

if latest_sql:
    st.subheader("Generated SQL")
    st.code(latest_sql, language="sql")
    if latest_expl:
        st.caption(f"Why: {latest_expl}")
    if latest_assumptions:
        with st.expander("Assumptions"):
            for a in latest_assumptions:
                st.write("- " + a)

    # Safety check and limit injection
    ok, msg = is_safe_select(latest_sql)
    if not ok:
        st.error(f"Blocked. {msg}")
    else:
        final_sql = enforce_limit(latest_sql, default_limit=user_default_limit)
        if final_sql.strip() != latest_sql.strip():
            st.info(f"LIMIT enforced. Final SQL will be:\n\n{final_sql}")

        run_it = st.button("Execute SQL", type="secondary")
        if run_it:
            with st.spinner("Running query..."):
                try:
                    t0 = time.time()
                    df, csv_bytes = run_select(final_sql)
                    dt = time.time() - t0
                    st.success(f"Query returned {len(df):,} rows in {dt:.2f}s")
                    st.dataframe(df.head(100))
                    st.download_button(
                        label="Download CSV",
                        data=csv_bytes,
                        file_name="result.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Execution failed: {e}")

# Developer pane
with st.expander("Schema summary (what the LLM sees)"):
    st.text(schema_text)

with st.expander("Conversation log"):
    for item in st.session_state["conversation_notes"]:
        st.write(item)
