import json
from db import connect

def export_data(args):
    conn = connect()
    cur = conn.cursor()

    location_id = args.location_id

    # Get location info
    cur.execute("SELECT name, notes FROM weather_providers WHERE id = ?", (location_id,))
    loc = cur.fetchone()
    if not loc:
        print(f"❌ Location with ID {location_id} not found.")
        return

    location_name, location_notes = loc

    # Fetch records
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
    column_names = [desc[0] for desc in cur.description]

    excluded = {"id", "location_id", "data_raw"}
    keep_columns = [col for col in column_names if col not in excluded]

    data = [
        {col: row[idx] for idx, col in enumerate(column_names) if col in keep_columns}
        for row in rows
    ]

    output = {
        "location_name": location_name,
        "location_notes": location_notes,
        "records": data
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    conn.close()
