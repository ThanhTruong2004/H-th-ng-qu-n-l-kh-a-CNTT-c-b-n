import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "/data/exams.db")

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

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
