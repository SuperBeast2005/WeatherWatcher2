import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db.db")

conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = lambda cursor, row: {
    col[0]: row[i] for i, col in enumerate(cursor.description)
}
cursor = conn.cursor()