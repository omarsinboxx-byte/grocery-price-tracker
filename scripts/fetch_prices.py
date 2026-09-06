#!/usr/bin/env python3
"""
Pull the latest U.S. average grocery prices from FRED (BLS Average Price Data,
mirrored on FRED) and rewrite data/prices.json.

No API key needed — this uses FRED's public CSV export endpoint
(fredgraph.csv), which serves the same numbers as the FRED website itself
without authentication.

Run manually:  python scripts/fetch_prices.py
Run automatically: see .github/workflows/update.yml (monthly + manual dispatch)
"""
import csv
import io
import json
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "data" / "prices.json"

# Fixed item order = fixed chart color order. Keep this order stable.
ITEMS = [
    {"id": "eggs", "name": "Eggs", "detail": "Grade A, large, per dozen", "unit": "dozen", "seriesId": "APU0000708111"},
    {"id": "milk", "name": "Milk", "detail": "Whole, fortified, per gallon", "unit": "gallon", "seriesId": "APU0000709112"},
    {"id": "bread", "name": "Bread", "detail": "White, pan, per lb", "unit": "lb", "seriesId": "APU0000702111"},
    {"id": "ground_beef", "name": "Ground beef", "detail": "100% beef, per lb", "unit": "lb", "seriesId": "APU0000703112"},
    {"id": "chicken_breast", "name": "Chicken breast", "detail": "Boneless, per lb", "unit": "lb", "seriesId": "APU0000FF1101"},
    {"id": "bananas", "name": "Bananas", "detail": "Per lb", "unit": "lb", "seriesId": "APU0000711211"},
    {"id": "coffee", "name": "Coffee", "detail": "100% ground roast, per lb", "unit": "lb", "seriesId": "APU0000717311"},
    {"id": "rice", "name": "Rice", "detail": "White, long grain, per lb", "unit": "lb", "seriesId": "APU0000701312"},
]

MONTHS_WINDOW = 24  # how many trailing months to keep in the dashboard
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
USER_AGENT = "grocery-price-tracker/1.0 (+https://github.com/)"


def fetch_series(series_id: str) -> dict:
    """Return {'YYYY-MM': value_or_None} for one FRED series."""
    req = urllib.request.Request(FRED_CSV_URL.format(series_id=series_id), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(raw))
    header = next(reader)
    date_col, value_col = header[0], header[1]
    out = {}
    for row in reader:
        if len(row) < 2:
            continue
        ym = row[0][:7]  # "YYYY-MM-DD" -> "YYYY-MM"
        val = row[1].strip()
        out[ym] = None if val in ("", ".") else float(val)
    return out


def month_range(end_ym: str, n: int) -> list:
    y, m = (int(x) for x in end_ym.split("-"))
    months = []
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def fill_gaps(values_by_month: dict, months: list) -> list:
    """Return a list of floats aligned to `months`, linearly interpolating
    interior gaps and forward/back-filling edge gaps."""
    raw = [values_by_month.get(m) for m in months]
    # interior interpolation
    for i, v in enumerate(raw):
        if v is not None:
            continue
        prev_i = next((j for j in range(i - 1, -1, -1) if raw[j] is not None), None)
        next_i = next((j for j in range(i + 1, len(raw)) if raw[j] is not None), None)
        if prev_i is not None and next_i is not None:
            span = next_i - prev_i
            raw[i] = raw[prev_i] + (raw[next_i] - raw[prev_i]) * (i - prev_i) / span
        elif prev_i is not None:
            raw[i] = raw[prev_i]
        elif next_i is not None:
            raw[i] = raw[next_i]
        else:
            raw[i] = 0.0
    return [round(v, 3) for v in raw]


def main():
    print("Fetching series from FRED...")
    fetched = {}
    latest_dates = []
    for item in ITEMS:
        series_data = fetch_series(item["seriesId"])
        fetched[item["id"]] = series_data
        real_months = [m for m, v in series_data.items() if v is not None]
        if real_months:
            latest_dates.append(max(real_months))
        print(f"  {item['name']:16s} {item['seriesId']:14s} -> {len(real_months)} months, latest {max(real_months) if real_months else 'n/a'}")

    if not latest_dates:
        raise SystemExit("No data fetched from FRED — aborting without overwriting existing data.")

    # Use the month that MOST series have already reported (mode of latest dates),
    # so one late-reporting series doesn't drag the whole window back.
    end_ym = max(set(latest_dates), key=latest_dates.count)
    months = month_range(end_ym, MONTHS_WINDOW)

    items_out = []
    gap_notes = []
    for item in ITEMS:
        series_data = fetched[item["id"]]
        missing = [m for m in months if series_data.get(m) is None]
        if missing:
            gap_notes.append(f"{item['name']}: {', '.join(missing)}")
        prices = fill_gaps(series_data, months)
        items_out.append({**item, "prices": prices})

    notes = [
        "Prices are U.S. city averages, not any single retailer or region.",
        "Data source: U.S. Bureau of Labor Statistics, Average Price Data, via FRED — no manual editing.",
    ]
    if gap_notes:
        notes.append("Gaps in the source data were linearly interpolated for: " + "; ".join(gap_notes) + ".")

    out = {
        "meta": {
            "title": "U.S. Grocery Price Tracker",
            "unitBasis": "U.S. city average, monthly",
            "source": "U.S. Bureau of Labor Statistics — Average Price Data (via FRED)",
            "sourceUrl": "https://fred.stlouisfed.org/release/tables?rid=10",
            "lastUpdated": f"{end_ym}-01",
            "generatedAt": date.today().isoformat(),
            "notes": notes,
        },
        "items": items_out,
        "months": months,
    }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {DATA_PATH} through {end_ym}.")


if __name__ == "__main__":
    main()
