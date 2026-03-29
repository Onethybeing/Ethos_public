"""
Pull the live schema from the Neon (Postgres) DB and write it to schema.sql.

Usage:
    uv run python scripts/pull_schema.py

Requires POSTGRES_URL in backend/.env (or environment).
The output is written to schema.sql at the repo root.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import asyncpg
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / "backend" / ".env")

# asyncpg needs postgresql:// not postgresql+asyncpg://
RAW_URL = os.getenv("POSTGRES_URL", "")
ASYNCPG_URL = RAW_URL.replace("postgresql+asyncpg://", "postgresql://")

if not ASYNCPG_URL:
    sys.exit("POSTGRES_URL not set in backend/.env")

OUTPUT = ROOT / "schema.sql"


COLUMN_QUERY = """
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default,
    c.udt_name
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
"""

INDEX_QUERY = """
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"""

CONSTRAINT_QUERY = """
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name  AS foreign_table,
    ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema    = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
   AND tc.table_schema    = ccu.table_schema
WHERE tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type, kcu.column_name;
"""


def pg_type(row) -> str:
    """Return a compact Postgres type string from an information_schema row."""
    dt = row["data_type"]
    udt = row["udt_name"]
    maxlen = row["character_maximum_length"]

    if dt == "character varying":
        return f"VARCHAR({maxlen})" if maxlen else "VARCHAR"
    if dt == "timestamp with time zone":
        return "TIMESTAMPTZ"
    if dt == "timestamp without time zone":
        return "TIMESTAMP"
    if dt in ("double precision", "real"):
        return "FLOAT"
    if dt == "USER-DEFINED":
        return udt.upper()
    return dt.upper()


async def pull() -> str:
    conn = await asyncpg.connect(ASYNCPG_URL, ssl="require")
    try:
        columns = await conn.fetch(COLUMN_QUERY)
        indexes = await conn.fetch(INDEX_QUERY)
        constraints = await conn.fetch(CONSTRAINT_QUERY)
    finally:
        await conn.close()

    # Group by table
    tables: dict[str, list] = {}
    for row in columns:
        tables.setdefault(row["table_name"], []).append(row)

    # Primary keys per table
    pks: dict[str, set[str]] = {}
    uniques: dict[str, set[str]] = {}
    for row in constraints:
        t = row["table_name"]
        if row["constraint_type"] == "PRIMARY KEY":
            pks.setdefault(t, set()).add(row["column_name"])
        if row["constraint_type"] == "UNIQUE":
            uniques.setdefault(t, set()).add(row["column_name"])

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"-- ============================================================",
        f"-- EthosNews — Postgres schema (pulled from live Neon DB)",
        f"-- Generated: {ts}",
        f"--",
        f"-- To refresh: uv run python scripts/pull_schema.py",
        f"-- ============================================================",
        "",
    ]

    for table, cols in tables.items():
        lines.append(f"-- ── {table} {'─' * max(1, 50 - len(table))}")
        lines.append(f"CREATE TABLE IF NOT EXISTS {table} (")
        col_lines = []
        for col in cols:
            col_name = col["column_name"]
            type_str = pg_type(col)
            nullable = col["is_nullable"] == "YES"
            default = col["column_default"]

            parts = [f"    {col_name:<24}{type_str}"]
            if col_name in pks.get(table, set()):
                parts.append("PRIMARY KEY")
            if col_name in uniques.get(table, set()):
                parts.append("UNIQUE")
            if not nullable and col_name not in pks.get(table, set()):
                parts.append("NOT NULL")
            if default and "nextval" not in default:
                parts.append(f"DEFAULT {default}")
            col_lines.append(" ".join(parts))

        lines.append(",\n".join(col_lines))
        lines.append(");\n")

    # Indexes (skip auto-generated PK/unique constraint indexes)
    constraint_names = {row["constraint_name"] for row in constraints}
    lines.append("-- ── indexes ──────────────────────────────────────────────")
    for idx in indexes:
        if idx["indexname"] in constraint_names:
            continue
        lines.append(f"{idx['indexdef']};")

    return "\n".join(lines) + "\n"


async def main():
    print(f"Connecting to Neon DB…")
    sql = await pull()
    OUTPUT.write_text(sql, encoding="utf-8")
    print(f"Written to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
