import re
import sqlparse
from typing import Tuple

BLOCKED = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|MERGE)\b", re.IGNORECASE)

def is_safe_select(sql: str) -> Tuple[bool, str]:
    """Allow only a single SELECT statement. Block DML/DDL and multi-statement."""
    parsed = sqlparse.parse(sql or "")
    if len(parsed) != 1:
        return False, "Only a single statement is allowed."
    stmt = parsed[0]
    first_token = next((t for t in stmt.tokens if not t.is_whitespace), None)
    if not first_token or first_token.normalized.upper() != "SELECT":
        return False, "Only SELECT statements are allowed."
    if BLOCKED.search(sql):
        return False, "Statement contains blocked keywords."
    return True, ""

def enforce_limit(sql: str, default_limit: int) -> str:
    """If no LIMIT exists, add one at the end."""
    tokens = [t.value.upper() for t in sqlparse.parse(sql)[0].tokens if not t.is_whitespace]
    has_limit = any(tok == "LIMIT" for tok in tokens)
    if has_limit:
        return sql
    return sql.rstrip().rstrip(";") + f" LIMIT {int(default_limit)};"
