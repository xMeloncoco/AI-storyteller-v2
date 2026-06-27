"""
Lightweight startup migrations.

This module exists because the project doesn't yet use Alembic and the
test database file is reused across runs. Each migration here is small,
idempotent, and safe to run on every startup — they check whether the
schema work has already been done before touching anything.

Add a new migration as a function and call it from `apply_startup_migrations()`.
Keep them small. Anything bigger than a few ALTER TABLEs belongs in a
real migration tool.
"""
from __future__ import annotations

import json
from typing import List, Set

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .utils.logger import log_notification


# Tables that gained witness-tracking columns in R6. CRUD reads ignore the
# columns until M2.3; we add them now so writes can start populating them.
_WITNESS_TABLES = ("memory_flags", "character_memories", "character_knowledge")
_WITNESS_COLUMNS = ("witnesses", "told_to")


def apply_startup_migrations(engine: Engine) -> None:
    """Run every startup migration. Safe to call repeatedly."""
    _ensure_witness_columns(engine)
    _backfill_witness_columns(engine)


# ---------------------------------------------------------------------------
# Witness column migration (R6)
# ---------------------------------------------------------------------------


def _ensure_witness_columns(engine: Engine) -> None:
    """ADD COLUMN for witnesses / told_to on any of the three tables that
    don't already have them. Idempotent."""
    with engine.begin() as conn:
        for table in _WITNESS_TABLES:
            existing = _existing_columns(conn, table)
            for col in _WITNESS_COLUMNS:
                if col in existing:
                    continue
                # SQLite supports a subset of ALTER TABLE; ADD COLUMN with
                # no default is supported in every version we care about.
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} TEXT"))
                print(f"[migration] added {table}.{col}")


def _backfill_witness_columns(engine: Engine) -> None:
    """Set witnesses = best-effort list and told_to = [] on rows missing them.

    Best-effort per table:
    - memory_flags: characters present in the row's session (via the
      latest scene_state for that session), else [].
    - character_memories: union of related_characters + the owning
      character_id (they witnessed their own memory), else just owner.
    - character_knowledge: just the owning character_id (knowing it
      implies they witnessed or were told, and we have no session link
      here to disambiguate further).

    The spec only requires "best effort, or empty list". Empty lists are
    fine; M2.3 will treat them as "no one filtered in", which is the
    correct cautious behavior for old data.
    """
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        touched = 0
        touched += _backfill_memory_flags(db)
        touched += _backfill_character_memories(db)
        touched += _backfill_character_knowledge(db)

        if touched == 0:
            return

        # One summary line in addition to the per-row notices below, so
        # someone scrolling the tester panel sees the migration ran.
        log_notification(
            db,
            f"Witness column backfill complete ({touched} rows)",
            "database",
            {"tables": list(_WITNESS_TABLES), "rows_touched": touched},
        )
    finally:
        db.close()


def _backfill_memory_flags(db) -> int:
    rows = db.execute(
        text("SELECT id, session_id, playthrough_id FROM memory_flags WHERE witnesses IS NULL")
    ).fetchall()
    if not rows:
        return 0

    touched = 0
    for row_id, session_id, playthrough_id in rows:
        witnesses = sorted(_characters_in_session(db, session_id))
        _write_witness_backfill(
            db,
            table="memory_flags",
            row_id=row_id,
            witnesses=witnesses,
            extra={"playthrough_id": playthrough_id, "session_id": session_id},
        )
        touched += 1
    return touched


def _backfill_character_memories(db) -> int:
    rows = db.execute(
        text(
            "SELECT id, character_id, related_characters "
            "FROM character_memories WHERE witnesses IS NULL"
        )
    ).fetchall()
    if not rows:
        return 0

    touched = 0
    for row_id, owner_id, related_raw in rows:
        witnesses: Set[int] = set()
        if owner_id is not None:
            witnesses.add(int(owner_id))
        for cid in _safe_load_int_list(related_raw):
            witnesses.add(cid)
        _write_witness_backfill(
            db,
            table="character_memories",
            row_id=row_id,
            witnesses=sorted(witnesses),
            extra={"owner_character_id": owner_id},
        )
        touched += 1
    return touched


def _backfill_character_knowledge(db) -> int:
    rows = db.execute(
        text("SELECT id, character_id FROM character_knowledge WHERE witnesses IS NULL")
    ).fetchall()
    if not rows:
        return 0

    touched = 0
    for row_id, owner_id in rows:
        witnesses = [int(owner_id)] if owner_id is not None else []
        _write_witness_backfill(
            db,
            table="character_knowledge",
            row_id=row_id,
            witnesses=witnesses,
            extra={"owner_character_id": owner_id},
        )
        touched += 1
    return touched


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _existing_columns(conn, table: str) -> Set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    # PRAGMA table_info row layout: (cid, name, type, notnull, dflt_value, pk)
    return {row[1] for row in rows}


def _characters_in_session(db, session_id) -> Set[int]:
    """Character ids appearing in any scene_state for the given session.

    We don't try to reconstruct who was present at the exact moment the
    flag was created; that data isn't stored. Using everyone who appeared
    in the session is the closest "best effort" the schema allows.
    """
    if session_id is None:
        return set()
    rows = db.execute(
        text(
            """
            SELECT DISTINCT sc.character_id
            FROM scene_characters sc
            JOIN scene_state ss ON ss.id = sc.scene_state_id
            WHERE ss.session_id = :sid AND sc.character_id IS NOT NULL
            """
        ),
        {"sid": session_id},
    ).fetchall()
    return {int(r[0]) for r in rows}


def _safe_load_int_list(raw) -> List[int]:
    """Decode a JSON list of ints from a Text column; tolerate malformed data."""
    if not raw:
        return []
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        return []
    out: List[int] = []
    if isinstance(decoded, list):
        for x in decoded:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
    return out


def _write_witness_backfill(
    db,
    *,
    table: str,
    row_id: int,
    witnesses: List[int],
    extra: dict,
) -> None:
    """Persist the backfill values and log a per-row notice."""
    db.execute(
        text(
            f"UPDATE {table} "
            "SET witnesses = :w, told_to = :t WHERE id = :id"
        ),
        {"w": json.dumps(witnesses), "t": json.dumps([]), "id": row_id},
    )
    db.commit()

    log_notification(
        db,
        f"database.backfill: {table} row {row_id} witnesses set",
        "database",
        {
            "migration": "witness_columns",
            "table": table,
            "row_id": row_id,
            "witnesses": witnesses,
            "told_to": [],
            **extra,
        },
    )
