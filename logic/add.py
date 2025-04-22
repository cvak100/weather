# logic/add.py

import sqlite3
from db import connect

def add_location(args):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO locations (name, lat, lon, elevation, info)
        VALUES (?, ?, ?, ?, ?)
    """, (args.name, args.lat, args.lon, args.elevation, args.info))

    conn.commit()
    conn.close()
    print(f"✅ Added location: {args.name}")

def add_provider(args):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO weather_providers (name, base_url, notes, location_id)
        VALUES (?, ?, ?, ?)
    """, (args.name, args.base_url, args.notes, args.location_id))

    conn.commit()
    conn.close()
    print(f"✅ Added provider: {args.name} for location ID {args.location_id}")
