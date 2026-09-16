import os
import queue
import sqlite3
from threading import Lock

# PERF-003: mitigates per-request connection overhead with a bounded SQLite
# connection pool. The settings mirror what SQLAlchemy's QueuePool would use:
#   pool_size=5, max_overflow=10, connect timeout=15, check_same_thread=False.
DB_PATH = os.environ.get("DB_PATH", "/data/exams.db")

POOL_SIZE = 5
MAX_OVERFLOW = 10
CONNECT_TIMEOUT = 15
MAX_TOTAL = POOL_SIZE + MAX_OVERFLOW


class SQLitePool:
    """A tiny bounded pool of sqlite3 connections.

    `acquire()` returns an idle connection or creates a new one while the pool
    has capacity (up to pool_size + max_overflow). If exhausted it blocks up to
    `timeout` seconds waiting for a connection to be released. Connections are
    physically closed only via `discard()` (after IOError etc.) or `dispose()`.
    """

    def __init__(self, db_path, pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW,
                 timeout=CONNECT_TIMEOUT):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self._idle = queue.Queue()
        self._total = 0
        self._lock = Lock()

    def _create(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=self.timeout,
                               check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def acquire(self) -> sqlite3.Connection:
        try:
            return self._idle.get_nowait()
        except queue.Empty:
            pass
        with self._lock:
            if self._total < self.pool_size + self.max_overflow:
                self._total += 1
                return self._create()
        # Pool saturated: wait for a released connection (bounded by timeout).
        return self._idle.get(timeout=self.timeout)

    def release(self, conn: sqlite3.Connection) -> None:
        self._idle.put(conn)

    def discard(self, conn: sqlite3.Connection) -> None:
        try:
            conn.close()
        except Exception:
            pass
        with self._lock:
            if self._total > 0:
                self._total -= 1

    def dispose(self) -> None:
        while True:
            try:
                self._idle.get_nowait().close()
            except queue.Empty:
                break
        with self._lock:
            self._total = 0


_pool = SQLitePool(DB_PATH)


class _PooledConnection:
    """Proxy for a pooled sqlite3 connection.

    `close()` returns the physical connection to the pool instead of closing
    it, so existing call sites (`get_db()` -> `db.execute(...)` -> `db.close()`)
    keep working unchanged while reusing underlying connections (PERF-003).
    """

    __slots__ = ("_pool", "_conn")

    def __init__(self, pool: SQLitePool, conn: sqlite3.Connection):
        self._pool = pool
        self._conn = conn

    def execute(self, query, params=None):
        try:
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)
        except sqlite3.DatabaseError:
            # Connection is broken (e.g. disk I/O error): discard and retry once.
            self._pool.discard(self._conn)
            self._conn = self._pool._create()
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)

    def executescript(self, script):
        return self._conn.executescript(script)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        try:
            return self._conn.rollback()
        except sqlite3.OperationalError:
            return None

    def close(self):
        """Return the connection to the pool (never physically closes it)."""
        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            self._pool.release(conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = _pool.acquire()
    return _PooledConnection(_pool, conn)


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exam_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('word', 'excel', 'powerpoint')),
            exam_filename TEXT NOT NULL,
            exam_path TEXT NOT NULL,
            criteria_filename TEXT NOT NULL,
            criteria_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generated_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_name TEXT,
            exam_word_id INTEGER,
            exam_excel_id INTEGER,
            exam_powerpoint_id INTEGER,
            output_filename TEXT,
            output_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_word_id) REFERENCES exam_sets(id),
            FOREIGN KEY (exam_excel_id) REFERENCES exam_sets(id),
            FOREIGN KEY (exam_powerpoint_id) REFERENCES exam_sets(id)
        );

        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id TEXT UNIQUE NOT NULL,
            exam_pdf_path TEXT NOT NULL,
            answer_key_pdf_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")