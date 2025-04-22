# logic/export.py

import json
from db import connect

def export_data(args):
    conn = connect()
    cur = conn.cursor()

    # Required
    location_id = args.location_id

    if args.date:
        cur.execute("""
            SELECT * FROM weather_observed
            WHERE location_id = ? AND date = ?
            ORDER BY date
        """, (location_id, args.date))
    elif args.date_from and args.date_to:
        cur.execute("""
            SELECT * FROM weather_observed
            WHERE location_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (location_id, args.date_from, args.date_to))
    else:
        print("You must provide either --date or --from and --to.")
        return

    rows = cur.fetchall()
    column_names = [description[0] for description in cur.description]

    data = [dict(zip(column_names, row)) for row in rows]

    print(json.dumps(data, indent=2, ensure_ascii=False))

    conn.close()
