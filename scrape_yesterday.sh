#!/bin/bash
set -u

cd /opt/weather || exit 1

YESTERDAY=$(date -d "yesterday" +%F)
FROM=$(date -d "3 days ago" +%F)
TO=$(date -d "2 days ago" +%F)

echo "=== scrape-today for $YESTERDAY ==="
python weather.py scrape-today --location-id 1 --date "$YESTERDAY"
scrape_rc=$?

echo "=== patch-fields from $FROM to $TO ==="
python weather.py patch-fields --location-id 1 --from "$FROM" --to "$TO"
patch_rc=$?

if [ "$scrape_rc" -ne 0 ]; then
  echo "scrape-today failed with exit code $scrape_rc"
  exit "$scrape_rc"
fi

if [ "$patch_rc" -ne 0 ]; then
  echo "patch-fields failed with exit code $patch_rc"
  exit "$patch_rc"
fi

echo "Done."
