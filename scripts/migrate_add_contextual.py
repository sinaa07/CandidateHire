#!/usr/bin/env python3
"""Add contextual ranking columns to jobs and rankings tables (idempotent)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "storage" / "candidatehire.db"

JOB_COLUMNS: list[tuple[str, str]] = [
    ("ranking_mode", "VARCHAR(32) NOT NULL DEFAULT 'keyword'"),
    ("skill_implied_by_map_path", "VARCHAR(2048)"),
    ("skill_map_status", "VARCHAR(32) NOT NULL DEFAULT 'pending'"),
    ("skill_map_built_at", "DATETIME"),
    ("skill_map_error", "TEXT"),
]

RANKING_COLUMNS: list[tuple[str, str]] = [
    ("truly_missing_skills", "JSON"),
    ("likely_covered_skills", "JSON"),
    ("ranking_mode_used", "VARCHAR(32)"),
]


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    col_type: str,
    existing: set[str],
) -> bool:
    if column in existing:
        print(f"  skip {table}.{column} (already exists)")
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    print(f"  added {table}.{column}")
    existing.add(column)
    return True


def migrate() -> None:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}; nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys=ON")

        job_cols = _existing_columns(conn, "jobs")
        ranking_cols = _existing_columns(conn, "rankings")

        print("Adding columns to jobs...")
        for name, col_type in JOB_COLUMNS:
            _add_column_if_missing(conn, "jobs", name, col_type, job_cols)

        print("Adding columns to rankings...")
        for name, col_type in RANKING_COLUMNS:
            _add_column_if_missing(conn, "rankings", name, col_type, ranking_cols)

        jobs_updated = conn.execute(
            """
            UPDATE jobs
            SET ranking_mode = 'keyword',
                skill_map_status = 'pending'
            WHERE ranking_mode IS NULL
               OR ranking_mode = ''
               OR skill_map_status IS NULL
               OR skill_map_status = ''
            """
        ).rowcount

        rankings_updated = conn.execute(
            """
            UPDATE rankings
            SET ranking_mode_used = 'keyword'
            WHERE ranking_mode_used IS NULL
            """
        ).rowcount

        conn.commit()

        job_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        ranking_count = conn.execute("SELECT COUNT(*) FROM rankings").fetchone()[0]

        print()
        print(f"Jobs: {job_count} total, {jobs_updated} rows updated with defaults")
        print(f"Rankings: {ranking_count} total, {rankings_updated} rows updated with ranking_mode_used='keyword'")
        print("Migration complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
