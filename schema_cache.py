import os
import psycopg2
import pandas as pd
from typing import Dict, List

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

def summarize_schema(max_columns_per_table: int = 25, include_row_counts: bool = False) -> str:
    """
    Return a compact, plain-text schema summary suitable for prompts.
    Lists schema.table, top columns, and optional approximate row counts.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')
            ORDER BY table_schema, table_name
        """)
        tables = cur.fetchall()

        lines: List[str] = []
        for sch, tbl in tables:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                ORDER BY ordinal_position
                LIMIT %s
            """, (sch, tbl, max_columns_per_table))
            cols = cur.fetchall()
            coltxt = ", ".join([f"{c}:{t}" for c, t in cols]) if cols else "(no columns?)"

            if include_row_counts:
                try:
                    cur.execute(f'SELECT reltuples::bigint FROM pg_class WHERE oid = %s::regclass;', (f'{sch}.{tbl}',))
                    approx = cur.fetchone()[0]
                    lines.append(f"{sch}.{tbl} [~{approx} rows]: {coltxt}")
                except Exception:
                    lines.append(f"{sch}.{tbl}: {coltxt}")
            else:
                lines.append(f"{sch}.{tbl}: {coltxt}")

        return "\n".join(lines)
