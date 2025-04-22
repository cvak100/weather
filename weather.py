# weather.py

import argparse
from logic import add, scrape, export
from db import init_db

def main():
    parser = argparse.ArgumentParser(description="🌦 Weather CLI")
    subparsers = parser.add_subparsers(dest="command")

    # init-db
    subparsers.add_parser("init-db", help="Initialize the weather database")

    # add-location
    parser_add_loc = subparsers.add_parser("add-location", help="Add a new location")
    parser_add_loc.add_argument("name")
    parser_add_loc.add_argument("lat", type=float)
    parser_add_loc.add_argument("lon", type=float)
    parser_add_loc.add_argument("elevation", type=float)
    parser_add_loc.add_argument("--info", default="")

    # add-provider
    parser_add_prov = subparsers.add_parser("add-provider", help="Add a new weather provider")
    parser_add_prov.add_argument("name")
    parser_add_prov.add_argument("base_url")
    parser_add_prov.add_argument("--location-id", type=int, required=True)
    parser_add_prov.add_argument("--notes", default="")

    # scrape-today
    parser_scrape_today = subparsers.add_parser("scrape-today", help="Scrape today's weather data")
    parser_scrape_today.add_argument("--location-id", type=int)
    parser_scrape_today.add_argument("--date")

    # scrape-history
    parser_scrape_hist = subparsers.add_parser("scrape-history", help="Scrape historical weather")
    parser_scrape_hist.add_argument("--location-id", type=int, required=True)
    parser_scrape_hist.add_argument("--from", dest="date_from", required=True)
    parser_scrape_hist.add_argument("--to", dest="date_to", required=True)
    parser_scrape_hist.add_argument("--provider-id", type=int)

    # export
    parser_export = subparsers.add_parser("export", help="Export data to JSON")
    parser_export.add_argument("--location-id", type=int, required=True)
    parser_export.add_argument("--date")
    parser_export.add_argument("--from", dest="date_from")
    parser_export.add_argument("--to", dest="date_to")
    parser_export.add_argument("--output")

    # help
    subparsers.add_parser("help", help="Show usage examples")

    args = parser.parse_args()

    # Routing
    if args.command == "init-db":
        init_db()

    elif args.command == "add-location":
        add.add_location(args)

    elif args.command == "add-provider":
        add.add_provider(args)

    elif args.command == "scrape-today":
        scrape.scrape_today(args)

    elif args.command == "scrape-history":
        from logic.scrape import scrape_history
        scrape_history(args)

    elif args.command == "export":
        export.export_data(args)

    elif args.command == "help" or args.command is None:
        show_help()

def show_help():
    print("""
Weather CLI - Usage Examples

Initialize Database:
  python weather.py init-db

Add Location:
  python weather.py add-location Breginj 46.2630 13.4263 576 --info "Alpine"

Add Providers:
  python weather.py add-provider TimeAndDate https://www.timeanddate.com/astronomy/@3203471 --location-id 1 --notes "astronomy"
  python weather.py add-provider TimeAndDate https://www.timeanddate.com/weather/@3203471/historic --location-id 1 --notes "history"
  python weather.py add-provider Arso https://meteo.arso.gov.si/uploads/probase/www/observ/surface/text/sl/observationAms_BREGINJ_history.html --location-id 1 --notes "arso"
  python weather.py add-provider TimeAndDate https://www.timeanddate.com/sun/@3203471 --location-id 1 --notes "history"

Scrape Today's Weather:
  python weather.py scrape-today
  python weather.py scrape-today --location-id 1
  python weather.py scrape-today --location-id 1 --date 2025-03-01

Scrape Historical Weather:
  python weather.py scrape-history --location-id 1 --from 2025-01-01 --to 2025-03-30

Export Weather Data:
  python weather.py export --location-id 1 --date 2025-03-02
  python weather.py export --location-id 1 --from 2025-03-01 --to 2025-03-07
""")


if __name__ == "__main__":
    main()
