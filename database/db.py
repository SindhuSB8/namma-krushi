"""Small SQLite data layer.

Connections are intentionally short-lived because Streamlit reruns the
application frequently. The database and tables are created automatically.
"""

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


_INITIALIZATION_LOCK = threading.Lock()
_WRITE_LOCK = threading.RLock()
# Chat history now lives in the SAME database file as everything else, so one
# write lock serialises every write (disease, greenhouse, chat, users).
_CHAT_WRITE_LOCK = _WRITE_LOCK
_INITIALIZED_DATABASES = set()
_INITIALIZED_CHAT_DATABASES = set()   # kept for backward compatibility
# A second submission of the same leaf result by the same farmer inside this
# many seconds is treated as a duplicate (double click / Streamlit rerun).
DISEASE_DUPLICATE_WINDOW_SECONDS = 15
# PRAGMA user_version value that marks "legacy chat file already imported".
_CHAT_MIGRATED_VERSION = 1
_LOCK_RETRY_ATTEMPTS = 3
_SQLITE_BUSY_TIMEOUT_MS = 2000


# ---------------------------------------------------------------------
# DATABASE SCHEMA
# ---------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    language TEXT DEFAULT 'English'
);

CREATE TABLE IF NOT EXISTS greenhouse_analyses (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    temperature REAL,
    humidity REAL,
    soil_moisture REAL,
    light_intensity REAL,
    co2 REAL,
    prediction TEXT,
    confidence REAL,
    xai_explanation TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS disease_predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    image_path TEXT,
    disease TEXT,
    confidence REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id)
        REFERENCES chat_sessions(session_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);


-- ------------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_disease_user_time
ON disease_predictions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_greenhouse_user_time
ON greenhouse_analyses(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_time
ON chat_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_time
ON chat_messages(session_id, created_at);
"""

# ---------------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------------

@contextmanager
def connection():
    """Create a short-lived SQLite connection."""

    # Automatically create the database directory if it does not exist.
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000,
    )

    # Return rows that can be accessed by column name.
    con.row_factory = sqlite3.Row

    # Enforce SQLite foreign-key relationships.
    con.execute("PRAGMA foreign_keys = ON")

    # Wait if another Streamlit request temporarily holds the DB lock.
    con.execute(f"PRAGMA busy_timeout = {_SQLITE_BUSY_TIMEOUT_MS}")

    try:
        yield con
        con.commit()

    except Exception:
        con.rollback()
        raise

    finally:
        con.close()


def _legacy_chat_database_path():
    """Old, separate chat file (``namma_krushi_chat.db``) used by earlier versions.

    It is only READ (once) to import old chat history into the main database.
    It is never written to and never deleted.
    """
    return DATABASE_PATH.with_name(f"{DATABASE_PATH.stem}_chat.db")


# Backward-compatible name used by older tests/tools.
_chat_database_path = _legacy_chat_database_path

# Chat history is stored in the main database, exactly like every other table.
chat_connection = connection


# ---------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------

def initialize_database():
    """Create all required tables and indexes if they do not exist.

    Also imports any history from the legacy ``*_chat.db`` file once.
    """
    database_key = str(DATABASE_PATH.resolve())
    with _INITIALIZATION_LOCK:
        if database_key in _INITIALIZED_DATABASES:
            return
        for attempt in range(_LOCK_RETRY_ATTEMPTS):
            try:
                with connection() as con:
                    existing = {
                        row["name"]
                        for row in con.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                    required = {
                        "users", "admins", "disease_predictions",
                        "greenhouse_analyses", "chat_sessions", "chat_messages",
                    }
                    # An existing database needs no startup write. This matters
                    # when an administrator has it open in an inspection tool.
                    if not required.issubset(existing):
                        if con.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
                            con.execute("PRAGMA journal_mode = WAL")
                        con.executescript(SCHEMA)
                _migrate_legacy_chat_store()
                _INITIALIZED_DATABASES.add(database_key)
                return
            except sqlite3.OperationalError as exc:
                if not _is_locked_error(exc) or attempt == _LOCK_RETRY_ATTEMPTS - 1:
                    raise
                time.sleep(0.05 * (2 ** attempt))


def initialize_chat_database():
    """Chat tables are part of the main database; kept for older callers."""
    initialize_database()


def _migrate_legacy_chat_store():
    """Copy history from the old ``namma_krushi_chat.db`` into the main DB once.

    * Existing rows are never overwritten (``INSERT OR IGNORE``) or deleted.
    * The legacy file is only read, never modified.
    * Sessions that belong to a farmer who no longer exists in ``users`` are
      skipped: the main schema has a foreign key to ``users`` and importing
      them would let a newly registered farmer inherit a stranger's chats.
    * ``PRAGMA user_version`` records completion so a chat the farmer later
      deletes is never re-imported.
    """
    legacy_path = _legacy_chat_database_path()
    if not legacy_path.exists():
        return
    with connection() as con:
        if con.execute("PRAGMA user_version").fetchone()[0] >= _CHAT_MIGRATED_VERSION:
            return
    try:
        legacy = sqlite3.connect(str(legacy_path), timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000)
        try:
            sessions = legacy.execute(
                "SELECT session_id,user_id,title,created_at FROM chat_sessions"
            ).fetchall()
            messages = legacy.execute(
                "SELECT message_id,session_id,role,message,created_at FROM chat_messages"
            ).fetchall()
        finally:
            legacy.close()
    except sqlite3.Error:
        logger.exception("Legacy chat file could not be read; it will be retried next start")
        return

    with _WRITE_LOCK, connection() as con:
        valid_users = {row[0] for row in con.execute("SELECT user_id FROM users")}
        keep_sessions = [tuple(r) for r in sessions if r[1] in valid_users]
        con.executemany(
            "INSERT OR IGNORE INTO chat_sessions(session_id,user_id,title,created_at) VALUES(?,?,?,?)",
            keep_sessions,
        )
        valid_sessions = {row[0] for row in con.execute("SELECT session_id FROM chat_sessions")}
        keep_messages = [tuple(r) for r in messages if r[1] in valid_sessions]
        con.executemany(
            "INSERT OR IGNORE INTO chat_messages(message_id,session_id,role,message,created_at) VALUES(?,?,?,?,?)",
            keep_messages,
        )
        con.execute(f"PRAGMA user_version = {int(_CHAT_MIGRATED_VERSION)}")
    logger.info(
        "Imported %d chat sessions / %d messages from %s (skipped %d sessions of unknown farmers)",
        len(keep_sessions), len(keep_messages), legacy_path.name, len(sessions) - len(keep_sessions),
    )


# ---------------------------------------------------------------------
# QUERY HELPERS
# ---------------------------------------------------------------------

def fetch_all(sql, params=()):
    """Execute a SELECT query and return all rows as dictionaries."""

    def operation():
        with connection() as con:
            rows = con.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    return _with_lock_retry(operation)


def fetch_one(sql, params=()):
    """Execute a SELECT query and return one row as a dictionary."""

    def operation():
        with connection() as con:
            row = con.execute(sql, params).fetchone()
            return dict(row) if row else None

    return _with_lock_retry(operation)


def execute(sql, params=()):
    """Execute INSERT, UPDATE or DELETE and return last inserted row ID."""

    def operation():
        with connection() as con:
            cursor = con.execute(sql, params)
            return cursor.lastrowid

    # Streamlit can run several sessions in separate threads. Serializing the
    # short write transactions prevents those reruns from competing inside
    # this process while WAL still permits concurrent reads.
    with _WRITE_LOCK:
        return _with_lock_retry(operation)


def save_chat_exchange(user_id, session_id, title, user_message, assistant_message):
    """Atomically persist one complete farmer/assistant exchange.

    The selected session is validated against the authenticated farmer. A
    stale, deleted, or cross-user session ID creates a fresh session instead.
    Both messages commit together or neither is written.
    """
    initialize_chat_database()

    def operation():
        with chat_connection() as con:
            con.execute("BEGIN IMMEDIATE")
            valid_session_id = None
            if session_id:
                row = con.execute(
                    "SELECT session_id FROM chat_sessions WHERE session_id=? AND user_id=?",
                    (session_id, user_id),
                ).fetchone()
                if row:
                    valid_session_id = row["session_id"]

            if valid_session_id is None:
                cursor = con.execute(
                    "INSERT INTO chat_sessions(user_id,title) VALUES(?,?)",
                    (user_id, title),
                )
                valid_session_id = cursor.lastrowid

            con.executemany(
                "INSERT INTO chat_messages(session_id,role,message) VALUES(?,?,?)",
                (
                    (valid_session_id, "user", user_message),
                    (valid_session_id, "assistant", assistant_message),
                ),
            )
            return valid_session_id

    with _CHAT_WRITE_LOCK:
        return _with_lock_retry(operation)


def fetch_chat_sessions(user_id):
    initialize_chat_database()

    def operation():
        with chat_connection() as con:
            rows = con.execute(
                "SELECT session_id,user_id,title,created_at FROM chat_sessions "
                "WHERE user_id=? ORDER BY created_at DESC,session_id DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    return _with_lock_retry(operation)


def rename_chat_session(user_id, session_id, title):
    """Rename one of the authenticated farmer's saved chat sessions."""
    initialize_chat_database()
    title = (title or "").strip()
    if not title:
        return False

    def operation():
        with chat_connection() as con:
            cursor = con.execute(
                "UPDATE chat_sessions SET title=? WHERE session_id=? AND user_id=?",
                (title[:120], session_id, user_id),
            )
            return cursor.rowcount == 1

    with _CHAT_WRITE_LOCK:
        return _with_lock_retry(operation)


def delete_chat_session(user_id, session_id):
    """Delete one owned session; foreign keys remove its messages as well."""
    initialize_chat_database()

    def operation():
        with chat_connection() as con:
            cursor = con.execute(
                "DELETE FROM chat_sessions WHERE session_id=? AND user_id=?",
                (session_id, user_id),
            )
            return cursor.rowcount == 1

    with _CHAT_WRITE_LOCK:
        return _with_lock_retry(operation)


def fetch_chat_messages(session_id, newest_first=False, limit=None):
    initialize_chat_database()
    order = "DESC" if newest_first else "ASC"
    limit_sql = " LIMIT ?" if limit is not None else ""
    params = (session_id, limit) if limit is not None else (session_id,)

    def operation():
        with chat_connection() as con:
            rows = con.execute(
                "SELECT role,message,created_at FROM chat_messages "
                f"WHERE session_id=? ORDER BY message_id {order}{limit_sql}",
                params,
            ).fetchall()
            return [dict(row) for row in rows]

    return _with_lock_retry(operation)


def count_chat_sessions():
    initialize_chat_database()
    with chat_connection() as con:
        return con.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]


def count_chat_interactions():
    """Number of farmer questions asked in AI Advisory (one per saved exchange)."""
    initialize_database()
    with connection() as con:
        return con.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE role = ?", ("user",)
        ).fetchone()[0]


# ---------------------------------------------------------------------
# DISEASE PREDICTION HISTORY
# ---------------------------------------------------------------------

def save_disease_prediction(
    user_id,
    image_path,
    disease,
    confidence,
    duplicate_window_seconds=None,
):
    """Store ONE successful disease prediction and return ``(prediction_id, created)``.

    * ``created`` is ``False`` when the same farmer already saved the same
      result (same class and confidence) within the duplicate window, which
      is what a double click or an interrupted Streamlit rerun produces. The
      existing row's id is returned and nothing new is written.
    * Raises ``ValueError`` for an unknown ``user_id`` (for example a browser
      session that outlived a database reset) instead of failing deep inside
      SQLite with a bare foreign-key error.
    * The check and the insert run in a single ``BEGIN IMMEDIATE`` transaction,
      so two overlapping requests cannot both insert.
    """
    if duplicate_window_seconds is None:
        duplicate_window_seconds = DISEASE_DUPLICATE_WINDOW_SECONDS
    confidence = float(confidence)
    initialize_database()

    def operation():
        with connection() as con:
            con.execute("BEGIN IMMEDIATE")
            if con.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
            ).fetchone() is None:
                raise ValueError(f"Unknown farmer user_id={user_id!r}; prediction not saved")
            duplicate = con.execute(
                "SELECT prediction_id FROM disease_predictions "
                "WHERE user_id = ? AND disease = ? AND ABS(confidence - ?) < 1e-9 "
                "AND created_at >= datetime('now', ?) "
                "ORDER BY prediction_id DESC LIMIT 1",
                (user_id, disease, confidence, f"-{int(duplicate_window_seconds)} seconds"),
            ).fetchone()
            if duplicate is not None:
                return duplicate["prediction_id"], False
            cursor = con.execute(
                "INSERT INTO disease_predictions(user_id,image_path,disease,confidence) "
                "VALUES(?,?,?,?)",
                (user_id, image_path, disease, confidence),
            )
            return cursor.lastrowid, True

    with _WRITE_LOCK:
        return _with_lock_retry(operation)


# ---------------------------------------------------------------------
# ADMIN DASHBOARD COUNTS
# ---------------------------------------------------------------------

def get_admin_counts():
    """Live totals for the Admin Dashboard, read from the one application database.

    Every call queries SQLite again; nothing is cached or hard-coded.
    Returns a dict with: ``farmers``, ``disease_predictions``,
    ``greenhouse_analyses``, ``advisory_interactions`` (farmer questions asked
    in AI Advisory) and ``chat_sessions``.
    """
    initialize_database()

    def operation():
        with connection() as con:
            def one(sql, params=()):
                return con.execute(sql, params).fetchone()[0]

            return {
                "farmers": one("SELECT COUNT(*) FROM users"),
                "disease_predictions": one("SELECT COUNT(*) FROM disease_predictions"),
                "greenhouse_analyses": one("SELECT COUNT(*) FROM greenhouse_analyses"),
                "advisory_interactions": one(
                    "SELECT COUNT(*) FROM chat_messages WHERE role = ?", ("user",)
                ),
                "chat_sessions": one("SELECT COUNT(*) FROM chat_sessions"),
            }

    return _with_lock_retry(operation)


def _is_locked_error(exc):
    return "locked" in str(exc).lower() or "busy" in str(exc).lower()


def _with_lock_retry(operation):
    """Retry transient SQLite locks caused by overlapping Streamlit reruns."""
    for attempt in range(_LOCK_RETRY_ATTEMPTS):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if not _is_locked_error(exc) or attempt == _LOCK_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (2 ** attempt))
