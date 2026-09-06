# Grocery Price Tracker

A self-contained dashboard tracking U.S. average prices for eight staple
groceries — eggs, milk, bread, ground beef, chicken breast, bananas, coffee,
and rice — month over month. **It updates itself**: a GitHub Action pulls
fresh numbers from FRED on a schedule and commits them, so once this is
pushed and Pages is turned on, nothing here needs manual editing.

**[Open `index.html`](./index.html)** in a browser, or serve the folder (e.g.
with GitHub Pages) to view it live.

## What it shows

- **Indexed trend chart** — all eight items rebased to 100 in the first tracked
  month, so a $9/lb coffee and a $0.65/lb banana can be compared on one chart.
- **Stat tiles** — current basket cost (one unit of each item), overall change
  since the start of the series, and the biggest riser/faller.
- **Per-item cards** — current price, a price sparkline, and % change since the
  start of the series.
- **Full data table** — every price, every month, expandable at the bottom.

## Data

Source: **U.S. Bureau of Labor Statistics, Average Price Data** (the same
series that feeds the CPI), via [FRED](https://fred.stlouisfed.org/release/tables?rid=10).
These are U.S. city-average retail prices — not any single store, chain, or
region.

| Item | Detail | FRED series |
|---|---|---|
| Eggs | Grade A, large, per dozen | [APU0000708111](https://fred.stlouisfed.org/series/APU0000708111) |
| Milk | Whole, fortified, per gallon | [APU0000709112](https://fred.stlouisfed.org/series/APU0000709112) |
| Bread | White, pan, per lb | [APU0000702111](https://fred.stlouisfed.org/series/APU0000702111) |
| Ground beef | 100% beef, per lb | [APU0000703112](https://fred.stlouisfed.org/series/APU0000703112) |
| Chicken breast | Boneless, per lb | [APU0000FF1101](https://fred.stlouisfed.org/series/APU0000FF1101) |
| Bananas | Per lb | [APU0000711211](https://fred.stlouisfed.org/series/APU0000711211) |
| Coffee | 100% ground roast, per lb | [APU0000717311](https://fred.stlouisfed.org/series/APU0000717311) |
| Rice | White, long grain, per lb | [APU0000701312](https://fred.stlouisfed.org/series/APU0000701312) |

All data lives in [`data/prices.json`](./data/prices.json) and is regenerated
by `scripts/fetch_prices.py` — don't hand-edit it, your edits will be
overwritten on the next scheduled run.

## How the auto-update works

`.github/workflows/update.yml` runs on the 1st and 15th of every month (and
on demand from the **Actions** tab → *Update grocery prices* → **Run
workflow**). Each run:

1. Pulls the last 24 months of each series straight from FRED's public CSV
   export — **no API key required**.
2. Linearly interpolates any single-month gaps in the source data (this
   happened in October 2025, when BLS paused data collection during the
   federal government shutdown).
3. Rewrites `data/prices.json`.
4. Commits the change only if the numbers actually moved — no-op runs don't
   create empty commits.

Since GitHub Pages redeploys automatically on every push to `main`, the live
site reflects the new numbers within a minute or two of the workflow running.
No secrets, no manual copy-pasting.

To change the schedule, edit the `cron` line in `.github/workflows/update.yml`
([crontab.guru](https://crontab.guru/) helps with the syntax). To add or
remove a tracked item, edit the `ITEMS` list at the top of
`scripts/fetch_prices.py` (any FRED series ID works) — the dashboard picks up
new items automatically since `index.html` reads directly from
`data/prices.json`.

### If you ever need to update it by hand

Run `python scripts/fetch_prices.py` locally, or edit `data/prices.json`
directly (append a month to `months` and a price to every item's `prices`
array, then update `meta.lastUpdated`). `index.html` also embeds a fallback
copy of the data (the `FALLBACK_DATA` constant near the top of the `<script>`
block) so the page still works when opened directly as a local file, where
browsers block `fetch()` of local JSON — keep that in sync too if you rely on
double-click/`file://` viewing, or just always view it through a server.

## Publishing on GitHub

This folder is ready to push as-is:

```bash
git init
git add .
git commit -m "Add grocery price tracker"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

Then enable **GitHub Pages** (Settings → Pages → Deploy from branch → `main`,
root) to get a live URL, and confirm the **Update grocery prices** workflow
is enabled under the **Actions** tab (scheduled workflows sometimes need a
first manual run to activate).

## Stack

Plain HTML/CSS/JS + [Chart.js](https://www.chartjs.org/) (loaded from cdnjs)
for the dashboard, plus a small stdlib-only Python script for the data
refresh. No build step, no dependencies to install, no API key.
