# db.py

import sqlite3
from models import TABLES

DB_PATH = "weather_data.db"

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = connect()
    cur = conn.cursor()
    for table_sql in TABLES:
        cur.execute(table_sql)
    conn.commit()
    conn.close()
    print("✅ Database initialized.")

