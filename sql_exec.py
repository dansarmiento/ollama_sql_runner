import os
import io
import psycopg2
import pandas as pd
from typing import Tuple

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

def run_select(sql: str) -> Tuple[pd.DataFrame, bytes]:
    """Execute a SELECT and return (DataFrame, CSV-bytes)."""
    with get_conn() as conn:
        df = pd.read_sql_query(sql, conn)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return df, buf.getvalue().encode("utf-8")
