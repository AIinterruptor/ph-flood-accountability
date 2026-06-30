# PH Flood Control Accountability Monitor

Public dashboard tracking Philippine flood control projects, charged officials, and legal case statuses. Updated daily via GitHub Actions.

## Data

All data lives in `data/` as JSON files. Updated automatically each night at 2:00 AM PHT.

- `data/index.json` — summary stats and source health
- `data/projects/` — one file per flood control project
- `data/persons/` — one file per official/suspect
- `data/cases/` — one file per legal case
- `data/timeline.json` — chronological event feed

## Running the Scraper Locally

```bash
cd scraper
pip install -r requirements.txt
python run.py
```

## Dashboard

Live at: https://<your-github-username>.github.io/ph-flood-accountability/
