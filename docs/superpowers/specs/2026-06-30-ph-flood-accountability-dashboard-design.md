# PH Flood Control Accountability Monitor — Design Spec
**Date:** 2026-06-30
**Status:** Approved

---

## Overview

A public-facing, researcher-friendly accountability dashboard tracking Philippine flood control infrastructure projects, the officials charged in connection with them, and their legal case statuses. Updated daily via automated GitHub Actions scraping. Fully self-contained in a single GitHub repository — no external hosting, no paid services, no manual intervention required.

**Primary audiences:** General public, journalists, watchdog NGOs, researchers.

---

## Repository Structure

```
ph-flood-accountability/
├── .github/
│   └── workflows/
│       ├── daily-scrape.yml        # cron: 0 18 * * * (2AM PHT)
│       └── deploy-pages.yml        # triggers on data/ or docs/ changes
├── scraper/
│   ├── sources/
│   │   ├── coa.py                  # COA reports (PDF scrape via pdfplumber)
│   │   ├── ombudsman.py            # Ombudsman public case search portal
│   │   ├── sandiganbayan.py        # SC e-library court records
│   │   ├── news.py                 # RSS feeds: Inquirer, Rappler, PhilStar, CNN PH
│   │   └── dilg.py                 # DILG press releases / advisories
│   ├── normalizer.py               # Maps raw source output → canonical schema
│   ├── merger.py                   # Cross-references entities, deduplicates, flags conflicts
│   ├── validator.py                # Schema validation before commit
│   ├── run.py                      # Orchestrator: sources → normalize → merge → validate → write
│   └── requirements.txt
├── data/
│   ├── index.json                  # Master index: counts, stats, last_updated, source health
│   ├── scrape_log.json             # Per-run log: source status, errors, record counts
│   ├── projects/                   # One JSON file per flood control project
│   ├── persons/                    # One JSON file per official/suspect
│   ├── cases/                      # One JSON file per legal case
│   └── timeline.json               # Chronological event feed across all entities
├── docs/                           # GitHub Pages root
│   ├── index.html                  # Main dashboard (single-page app)
│   ├── assets/
│   │   ├── app.js                  # Alpine.js app logic + hash routing
│   │   ├── charts.js               # Chart.js visualizations
│   │   └── style.css               # Tailwind CSS overrides / custom styles
│   └── superpowers/specs/          # Design docs
└── README.md
```

---

## Data Schema

### Entity: Project

```json
{
  "id": "proj-mmda-pasig-floodway-2019",
  "name": "Pasig River Floodway Improvement",
  "agency": "DPWH",
  "region": "NCR",
  "budget_php": 2400000000,
  "status": "completed|ongoing|suspended|under_investigation",
  "coa_findings": ["coa-2021-ncr-042"],
  "cases": ["case-sb-2023-001"],
  "persons": ["person-santos-juan"],
  "coordinates": [14.5995, 120.9842],
  "sources": [{"type": "coa|news|court", "url": "...", "date": "..."}],
  "last_updated": "2026-06-30"
}
```

### Entity: Person

```json
{
  "id": "person-santos-juan",
  "name": "Juan Santos",
  "position": "DPWH Undersecretary",
  "agency": "DPWH",
  "region": "NCR",
  "status": "charged|convicted|acquitted|pending|under_investigation|suspended",
  "admin_track": {
    "stage": "ombudsman_filed|arraignment|decision",
    "status": "pending|dismissed|suspended|dismissed_from_service",
    "case_ids": ["case-ombudsman-2022-015"]
  },
  "criminal_track": {
    "stage": "investigation|filed|arraignment|trial|decision|appeal",
    "status": "pending|convicted|acquitted",
    "case_ids": ["case-sb-2023-001"]
  },
  "projects": ["proj-mmda-pasig-floodway-2019"],
  "sources": [{"type": "coa|news|court", "url": "...", "date": "..."}],
  "last_updated": "2026-06-30"
}
```

### Entity: Case

```json
{
  "id": "case-sb-2023-001",
  "docket": "SB-23-CRM-0042",
  "court": "Sandiganbayan|RTC|Ombudsman",
  "track": "criminal|administrative",
  "charge": "Malversation of Public Funds",
  "amount_php": 450000000,
  "persons": ["person-santos-juan"],
  "projects": ["proj-mmda-pasig-floodway-2019"],
  "filed_date": "2023-03-15",
  "stage": "investigation|filed|arraignment|trial|decision|appeal",
  "decision": null,
  "discrepancy": false,
  "sources": [
    {"type": "news", "url": "...", "date": "2023-03-16"},
    {"type": "court_record", "url": "...", "date": "2023-03-15"}
  ],
  "timeline": [
    {"date": "2021-08-01", "event": "COA flags irregular disbursements", "source_type": "coa"},
    {"date": "2022-05-10", "event": "Ombudsman complaint filed", "source_type": "ombudsman"},
    {"date": "2023-03-15", "event": "Sandiganbayan case docketed", "source_type": "court"}
  ],
  "last_updated": "2026-06-30"
}
```

### Index (`data/index.json`)

```json
{
  "last_updated": "2026-06-30T18:00:00Z",
  "totals": {
    "projects": 142,
    "persons": 89,
    "cases": 63,
    "convicted": 12,
    "funds_at_risk_php": 48200000000
  },
  "source_health": {
    "coa": {"status": "ok", "last_success": "2026-06-30"},
    "ombudsman": {"status": "ok", "last_success": "2026-06-30"},
    "sandiganbayan": {"status": "stale", "last_success": "2026-06-28"},
    "news": {"status": "ok", "last_success": "2026-06-30"},
    "dilg": {"status": "ok", "last_success": "2026-06-30"}
  },
  "data_quality": {
    "discrepancies_flagged": 4,
    "records_with_missing_coordinates": 11
  }
}
```

---

## Scraper Architecture

### Pipeline Flow

```
sources/*.py  →  normalizer.py  →  merger.py  →  validator.py  →  data/**/*.json  →  git commit
```

Each source module is isolated — one failure does not block others. `run.py` orchestrates in sequence, catches per-source exceptions, and logs to `data/scrape_log.json`.

### Source Strategies

| Source | Method | Notes |
|---|---|---|
| COA | `pdfplumber` PDF parse + regex | Inconsistent PDF formats; extract finding number, agency, amount |
| Ombudsman | HTML scrape of public case search | Filter by "flood control", "DPWH", "MMDA" keywords |
| Sandiganbayan / SC e-library | HTML scrape + keyword search | Keyword filter: "flood control", "DPWH", "malversation" |
| News RSS | `feedparser` on Inquirer/Rappler/PhilStar/CNN PH RSS | Keyword filter on title + summary |
| DILG | HTML scrape of dilg.gov.ph press releases | Filter by flood/infrastructure keywords |

### Normalization

`normalizer.py` maps raw source fields to canonical schema. Uses `rapidfuzz` for fuzzy person name deduplication across sources (e.g., "Juan C. Santos" == "Santos, Juan").

### Conflict Detection

`merger.py` cross-references the same entity across sources. Where sources disagree on a status field (e.g., news says "convicted", court record says "on appeal"), the record is flagged with `"discrepancy": true` and both source citations are preserved. Discrepancies surface as a visible `⚠ Sources conflict` badge on the dashboard.

### Commit Strategy

- Scraper writes to `data/` directory
- `validator.py` runs JSON schema validation — malformed output blocks the commit, previous data stays live
- If `git diff data/` produces changes → commit with message `data: auto-update YYYY-MM-DD` and push
- If no changes → no commit (keeps history clean)

### Rate Limiting

- `time.sleep(2)` between requests per domain
- Respects `robots.txt`
- Rotates User-Agent strings

---

## Dashboard UI

### Technology

- **Vanilla JS + Alpine.js** (CDN) — reactivity, no build step
- **Chart.js** (CDN) — bar/pie charts for case stage distribution
- **Leaflet.js** (CDN) — interactive project map
- **Tailwind CSS** (CDN) — utility styling
- **Hash routing** — `#/projects`, `#/persons`, `#/cases`, `#/timeline`, `#/map`, `#/persons/person-santos-juan`

### Layout

Single `index.html`. Top bar with global filters (Region, Agency, Status) and search. Summary stat cards. Five-tab navigation. Detail panel opens on entity click (same page, hash-updated).

**Five tabs:**
1. **Projects** — cards: name, agency, region, budget, case/person count, status badge
2. **Persons** — table: name, position, agency, admin track stage, criminal track stage, status pill
3. **Cases** — table: docket, court, charge, amount, stage, last activity date
4. **Timeline** — chronological event feed, all entities, filterable by entity type and date range
5. **Map** — Leaflet.js, markers at project coordinates, color-coded by status (green=clean, yellow=COA finding, orange=charged, red=convicted)

**Detail view:** Clicking any card/row loads a detail panel showing full entity data, linked entities (projects ↔ persons ↔ cases), full COA→Ombudsman→Court timeline with source citations, and discrepancy flags.

**Source health bar:** Footer shows per-source last-updated timestamp and status indicator.

**Geographic scope:** National view by default. Region filter narrows to Metro Manila drill-down (MMDA/DPWH NCR projects) or any other region.

---

## GitHub Actions Workflows

### `daily-scrape.yml`

```yaml
name: Daily Scrape
on:
  schedule:
    - cron: '0 18 * * *'   # 2:00 AM PHT (PHT = UTC+8)
  workflow_dispatch:         # manual trigger for testing
permissions:
  contents: write
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r scraper/requirements.txt
      - run: python scraper/run.py
      - run: |
          git config user.name "flood-bot"
          git config user.email "flood-bot@users.noreply.github.com"
          git diff --quiet data/ || (git add data/ && git commit -m "data: auto-update $(date +%Y-%m-%d)" && git push)
```

### `deploy-pages.yml`

```yaml
name: Deploy Pages
on:
  push:
    branches: [main]
    paths: ['data/**', 'docs/**']
permissions:
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: docs/ }
      - uses: actions/deploy-pages@v4
```

### Secrets

None required — all data sources are public.

### Failure Handling

- Per-source failures are caught, logged to `data/scrape_log.json`, and do not abort the pipeline
- Schema validation failure before commit → commit blocked, previous live data preserved
- GitHub sends failure notification to repo owner on Actions failure
- Dashboard renders source health from `index.json` — stale sources shown with warning badge

---

## Scope Boundaries

**In scope:**
- Flood control projects, persons, and cases only (not general DPWH or infrastructure)
- Public sources only (no login-walled government portals)
- Philippines national + Metro Manila drill-down
- Read-only dashboard (no user submissions)

**Out of scope:**
- Authentication or user accounts
- Real-time updates (daily is sufficient)
- Asset recovery / AMLC tracking (future enhancement)
- Non-flood infrastructure projects
