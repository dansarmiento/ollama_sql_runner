import os
import io
import psycopg2
import pandas as pd
from typing import Tuple

from exceptions import DatabaseQueryError

def get_conn():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT"),
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
        )
        return conn
    except psycopg2.OperationalError as e:
        raise DatabaseQueryError(f"Database connection failed: {e}") from e


def run_select(sql: str) -> Tuple[pd.DataFrame, bytes]:
    """Execute a SELECT and return (DataFrame, CSV-bytes)."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=cols)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return df, buf.getvalue().encode("utf-8")
    except psycopg2.Error as e:
        # Catch all other psycopg2 errors (e.g., syntax errors, etc.)
        # and wrap them in a custom exception.
        raise DatabaseQueryError(f"Database query failed: {e}") from e
