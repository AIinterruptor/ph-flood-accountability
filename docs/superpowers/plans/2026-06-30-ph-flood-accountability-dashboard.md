# PH Flood Control Accountability Monitor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated, self-contained GitHub repository that scrapes Philippine flood control accountability data daily and serves a public dashboard via GitHub Pages.

**Architecture:** A Python scraper pipeline (5 source modules → normalizer → merger → validator) runs nightly via GitHub Actions, writes structured JSON to `data/`, and commits changes to `main`. GitHub Pages serves a single `index.html` from `docs/` that reads those JSON files directly using Alpine.js, Chart.js, Leaflet.js, and Tailwind CSS — no build step, no npm, no external services.

**Tech Stack:** Python 3.11, pdfplumber, feedparser, rapidfuzz, requests, beautifulsoup4, jsonschema; Alpine.js 3.x CDN, Chart.js 4.x CDN, Leaflet.js 1.9.x CDN, Tailwind CSS 3.x CDN; GitHub Actions, GitHub Pages.

## Global Constraints

- Python 3.11 only — no walrus operator or 3.12+ syntax
- All CDN libraries loaded from jsDelivr (no unpkg, no direct vendor CDNs)
- All scrapers must respect `robots.txt` and sleep 2s between requests per domain
- JSON files must be UTF-8, no BOM, LF line endings
- All monetary amounts stored as integers (centavos for PHP, no floats)
- Entity IDs: kebab-case slugs, prefixed: `proj-`, `person-`, `case-`, `coa-`
- Date fields: ISO-8601 strings `YYYY-MM-DD` only (no datetime objects in JSON)
- `data/` directory is the sole output of the scraper — never write to `docs/` from Python
- GitHub Actions commit user: `flood-bot <flood-bot@users.noreply.github.com>`

---

## File Map

```
ph-flood-accountability/
├── .github/workflows/
│   ├── daily-scrape.yml
│   └── deploy-pages.yml
├── scraper/
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── coa.py
│   │   ├── ombudsman.py
│   │   ├── sandiganbayan.py
│   │   ├── news.py
│   │   └── dilg.py
│   ├── normalizer.py
│   ├── merger.py
│   ├── validator.py
│   ├── run.py
│   └── requirements.txt
├── data/
│   ├── index.json          (written by run.py)
│   ├── scrape_log.json     (written by run.py)
│   ├── timeline.json       (written by merger.py)
│   ├── projects/           (one file per project, written by merger.py)
│   ├── persons/            (one file per person, written by merger.py)
│   └── cases/              (one file per case, written by merger.py)
├── docs/
│   ├── index.html
│   └── assets/
│       ├── app.js
│       ├── charts.js
│       └── style.css
├── tests/
│   ├── test_normalizer.py
│   ├── test_merger.py
│   ├── test_validator.py
│   └── fixtures/
│       ├── raw_coa.json
│       ├── raw_news.json
│       └── sample_project.json
└── README.md
```

---

### Task 1: Repo Scaffold + Requirements

**Files:**
- Create: `scraper/requirements.txt`
- Create: `scraper/sources/__init__.py`
- Create: `tests/__init__.py`
- Create: `README.md`
- Create: `data/.gitkeep` (with empty subdirectories)

**Interfaces:**
- Produces: installable Python environment; empty `data/projects/`, `data/persons/`, `data/cases/` directories tracked by git

- [ ] **Step 1: Create `scraper/requirements.txt`**

```
requests==2.31.0
beautifulsoup4==4.12.3
pdfplumber==0.10.3
feedparser==6.0.11
rapidfuzz==3.6.1
jsonschema==4.21.1
lxml==5.1.0
```

- [ ] **Step 2: Create empty `__init__.py` files**

```bash
mkdir -p scraper/sources tests data/projects data/persons data/cases
touch scraper/__init__.py scraper/sources/__init__.py tests/__init__.py
```

- [ ] **Step 3: Create `.gitkeep` files to track empty data dirs**

```bash
touch data/projects/.gitkeep data/persons/.gitkeep data/cases/.gitkeep
```

- [ ] **Step 4: Create `README.md`**

```markdown
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
```

- [ ] **Step 5: Install dependencies to verify**

```bash
pip install -r scraper/requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: repo scaffold, requirements, empty data dirs"
```

---

### Task 2: Data Schemas + Validator

**Files:**
- Create: `scraper/validator.py`
- Create: `tests/test_validator.py`
- Create: `tests/fixtures/sample_project.json`

**Interfaces:**
- Produces:
  - `validate_project(obj: dict) -> None` — raises `jsonschema.ValidationError` on invalid input
  - `validate_person(obj: dict) -> None`
  - `validate_case(obj: dict) -> None`
  - `validate_index(obj: dict) -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_validator.py`:

```python
import pytest
from scraper.validator import validate_project, validate_person, validate_case, validate_index

VALID_PROJECT = {
    "id": "proj-dpwh-pasig-2019",
    "name": "Pasig River Floodway",
    "agency": "DPWH",
    "region": "NCR",
    "budget_php": 2400000000,
    "status": "ongoing",
    "coa_findings": [],
    "cases": [],
    "persons": [],
    "coordinates": [14.5995, 120.9842],
    "sources": [],
    "last_updated": "2026-06-30"
}

VALID_PERSON = {
    "id": "person-santos-juan",
    "name": "Juan Santos",
    "position": "Undersecretary",
    "agency": "DPWH",
    "region": "NCR",
    "status": "charged",
    "admin_track": {
        "stage": "ombudsman_filed",
        "status": "pending",
        "case_ids": []
    },
    "criminal_track": {
        "stage": "trial",
        "status": "pending",
        "case_ids": []
    },
    "projects": [],
    "sources": [],
    "last_updated": "2026-06-30"
}

VALID_CASE = {
    "id": "case-sb-2023-001",
    "docket": "SB-23-CRM-0042",
    "court": "Sandiganbayan",
    "track": "criminal",
    "charge": "Malversation of Public Funds",
    "amount_php": 450000000,
    "persons": [],
    "projects": [],
    "filed_date": "2023-03-15",
    "stage": "trial",
    "decision": None,
    "discrepancy": False,
    "sources": [],
    "timeline": [],
    "last_updated": "2026-06-30"
}

VALID_INDEX = {
    "last_updated": "2026-06-30T18:00:00Z",
    "totals": {
        "projects": 0,
        "persons": 0,
        "cases": 0,
        "convicted": 0,
        "funds_at_risk_php": 0
    },
    "source_health": {},
    "data_quality": {
        "discrepancies_flagged": 0,
        "records_with_missing_coordinates": 0
    }
}

def test_valid_project():
    validate_project(VALID_PROJECT)  # should not raise

def test_project_missing_required_field():
    bad = {**VALID_PROJECT}
    del bad["agency"]
    with pytest.raises(Exception):
        validate_project(bad)

def test_project_invalid_status():
    bad = {**VALID_PROJECT, "status": "unknown_status"}
    with pytest.raises(Exception):
        validate_project(bad)

def test_project_budget_must_be_integer():
    bad = {**VALID_PROJECT, "budget_php": 2400000000.50}
    with pytest.raises(Exception):
        validate_project(bad)

def test_valid_person():
    validate_person(VALID_PERSON)

def test_person_invalid_status():
    bad = {**VALID_PERSON, "status": "jailed"}
    with pytest.raises(Exception):
        validate_person(bad)

def test_valid_case():
    validate_case(VALID_CASE)

def test_case_invalid_track():
    bad = {**VALID_CASE, "track": "civil"}
    with pytest.raises(Exception):
        validate_case(bad)

def test_valid_index():
    validate_index(VALID_INDEX)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd C:\Users\josed\ph-flood-accountability
python -m pytest tests/test_validator.py -v
```

Expected: `ImportError` — `scraper.validator` does not exist yet.

- [ ] **Step 3: Implement `scraper/validator.py`**

```python
import jsonschema

SOURCE_SCHEMA = {
    "type": "object",
    "required": ["type", "url", "date"],
    "properties": {
        "type": {"type": "string"},
        "url": {"type": "string"},
        "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    }
}

PROJECT_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "agency", "region", "budget_php", "status",
                 "coa_findings", "cases", "persons", "coordinates", "sources", "last_updated"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": r"^proj-"},
        "name": {"type": "string"},
        "agency": {"type": "string"},
        "region": {"type": "string"},
        "budget_php": {"type": "integer"},
        "status": {"type": "string", "enum": ["completed", "ongoing", "suspended", "under_investigation"]},
        "coa_findings": {"type": "array", "items": {"type": "string"}},
        "cases": {"type": "array", "items": {"type": "string"}},
        "persons": {"type": "array", "items": {"type": "string"}},
        "coordinates": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
        "sources": {"type": "array", "items": SOURCE_SCHEMA},
        "last_updated": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    }
}

PERSON_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "position", "agency", "region", "status",
                 "admin_track", "criminal_track", "projects", "sources", "last_updated"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": r"^person-"},
        "name": {"type": "string"},
        "position": {"type": "string"},
        "agency": {"type": "string"},
        "region": {"type": "string"},
        "status": {"type": "string", "enum": [
            "charged", "convicted", "acquitted", "pending", "under_investigation", "suspended"
        ]},
        "admin_track": {
            "type": "object",
            "required": ["stage", "status", "case_ids"],
            "properties": {
                "stage": {"type": "string", "enum": ["ombudsman_filed", "arraignment", "decision", "none"]},
                "status": {"type": "string", "enum": ["pending", "dismissed", "suspended", "dismissed_from_service", "none"]},
                "case_ids": {"type": "array", "items": {"type": "string"}}
            }
        },
        "criminal_track": {
            "type": "object",
            "required": ["stage", "status", "case_ids"],
            "properties": {
                "stage": {"type": "string", "enum": ["investigation", "filed", "arraignment", "trial", "decision", "appeal", "none"]},
                "status": {"type": "string", "enum": ["pending", "convicted", "acquitted", "none"]},
                "case_ids": {"type": "array", "items": {"type": "string"}}
            }
        },
        "projects": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": SOURCE_SCHEMA},
        "last_updated": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    }
}

CASE_SCHEMA = {
    "type": "object",
    "required": ["id", "docket", "court", "track", "charge", "amount_php",
                 "persons", "projects", "filed_date", "stage", "decision",
                 "discrepancy", "sources", "timeline", "last_updated"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": r"^case-"},
        "docket": {"type": "string"},
        "court": {"type": "string", "enum": ["Sandiganbayan", "RTC", "Ombudsman"]},
        "track": {"type": "string", "enum": ["criminal", "administrative"]},
        "charge": {"type": "string"},
        "amount_php": {"type": "integer"},
        "persons": {"type": "array", "items": {"type": "string"}},
        "projects": {"type": "array", "items": {"type": "string"}},
        "filed_date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "stage": {"type": "string", "enum": ["investigation", "filed", "arraignment", "trial", "decision", "appeal"]},
        "decision": {"type": ["string", "null"]},
        "discrepancy": {"type": "boolean"},
        "sources": {"type": "array", "items": SOURCE_SCHEMA},
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["date", "event", "source_type"],
                "properties": {
                    "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                    "event": {"type": "string"},
                    "source_type": {"type": "string"}
                }
            }
        },
        "last_updated": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    }
}

INDEX_SCHEMA = {
    "type": "object",
    "required": ["last_updated", "totals", "source_health", "data_quality"],
    "properties": {
        "last_updated": {"type": "string"},
        "totals": {
            "type": "object",
            "required": ["projects", "persons", "cases", "convicted", "funds_at_risk_php"],
            "properties": {
                "projects": {"type": "integer"},
                "persons": {"type": "integer"},
                "cases": {"type": "integer"},
                "convicted": {"type": "integer"},
                "funds_at_risk_php": {"type": "integer"}
            }
        },
        "source_health": {"type": "object"},
        "data_quality": {
            "type": "object",
            "required": ["discrepancies_flagged", "records_with_missing_coordinates"],
            "properties": {
                "discrepancies_flagged": {"type": "integer"},
                "records_with_missing_coordinates": {"type": "integer"}
            }
        }
    }
}


def validate_project(obj: dict) -> None:
    jsonschema.validate(obj, PROJECT_SCHEMA)


def validate_person(obj: dict) -> None:
    jsonschema.validate(obj, PERSON_SCHEMA)


def validate_case(obj: dict) -> None:
    jsonschema.validate(obj, CASE_SCHEMA)


def validate_index(obj: dict) -> None:
    jsonschema.validate(obj, INDEX_SCHEMA)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_validator.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scraper/validator.py tests/test_validator.py
git commit -m "feat: data schemas and validator with tests"
```

---

### Task 3: Normalizer

**Files:**
- Create: `scraper/normalizer.py`
- Create: `tests/test_normalizer.py`
- Create: `tests/fixtures/raw_coa.json`
- Create: `tests/fixtures/raw_news.json`

**Interfaces:**
- Consumes: raw dicts from source modules (arbitrary keys, messy strings)
- Produces:
  - `normalize_project(raw: dict, source_type: str, source_url: str, today: str) -> dict` — returns dict matching `PROJECT_SCHEMA` (status defaults to `"under_investigation"` if unknown)
  - `normalize_person(raw: dict, source_type: str, source_url: str, today: str) -> dict`
  - `normalize_case(raw: dict, source_type: str, source_url: str, today: str) -> dict`
  - `slugify(text: str) -> str` — converts "Juan C. Santos" → "juan-c-santos"

- [ ] **Step 1: Create fixture files**

`tests/fixtures/raw_coa.json`:
```json
{
  "project_name": "Pasig River Floodway Improvement Project",
  "implementing_agency": "DPWH",
  "region_code": "NCR",
  "total_contract_amount": "PHP 2,400,000,000.00",
  "coa_finding_no": "COA-2021-NCR-042",
  "status_note": "ongoing"
}
```

`tests/fixtures/raw_news.json`:
```json
{
  "title": "DPWH official charged over flood project anomalies",
  "person_name": "Juan C. Santos",
  "position": "Undersecretary, DPWH",
  "agency": "DPWH",
  "charge": "Malversation of Public Funds",
  "court": "Sandiganbayan",
  "docket": "SB-23-CRM-0042",
  "amount": "450 million",
  "filed_date": "March 15, 2023",
  "url": "https://inquirer.net/example"
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_normalizer.py`:

```python
import json, os, pytest
from scraper.normalizer import normalize_project, normalize_person, normalize_case, slugify

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

def load(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)

def test_slugify_basic():
    assert slugify("Juan C. Santos") == "juan-c-santos"

def test_slugify_special_chars():
    assert slugify("Pasig River Floodway Improvement Project") == "pasig-river-floodway-improvement-project"

def test_slugify_extra_spaces():
    assert slugify("  Metro  Manila  ") == "metro-manila"

def test_normalize_project_id_prefix():
    raw = load("raw_coa.json")
    result = normalize_project(raw, "coa", "https://coa.gov.ph/example", "2026-06-30")
    assert result["id"].startswith("proj-")

def test_normalize_project_budget_is_integer():
    raw = load("raw_coa.json")
    result = normalize_project(raw, "coa", "https://coa.gov.ph/example", "2026-06-30")
    assert isinstance(result["budget_php"], int)
    assert result["budget_php"] == 2400000000

def test_normalize_project_status_default():
    raw = {"project_name": "Unknown", "implementing_agency": "DPWH",
           "region_code": "NCR", "total_contract_amount": "PHP 0", "status_note": "weird_value"}
    result = normalize_project(raw, "coa", "https://coa.gov.ph", "2026-06-30")
    assert result["status"] == "under_investigation"

def test_normalize_project_last_updated():
    raw = load("raw_coa.json")
    result = normalize_project(raw, "coa", "https://coa.gov.ph/example", "2026-06-30")
    assert result["last_updated"] == "2026-06-30"

def test_normalize_case_filed_date_parsed():
    raw = load("raw_news.json")
    result = normalize_case(raw, "news", raw["url"], "2026-06-30")
    assert result["filed_date"] == "2023-03-15"

def test_normalize_case_amount_integer():
    raw = load("raw_news.json")
    result = normalize_case(raw, "news", raw["url"], "2026-06-30")
    assert isinstance(result["amount_php"], int)
    assert result["amount_php"] == 450000000

def test_normalize_person_id_prefix():
    raw = load("raw_news.json")
    result = normalize_person(raw, "news", raw["url"], "2026-06-30")
    assert result["id"].startswith("person-")
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
python -m pytest tests/test_normalizer.py -v
```

Expected: `ImportError` — `scraper.normalizer` does not exist yet.

- [ ] **Step 4: Implement `scraper/normalizer.py`**

```python
import re
from datetime import datetime

# --- Slug helpers ---

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# --- Amount parsing ---

def _parse_php_amount(raw: str) -> int:
    """Parse 'PHP 2,400,000,000.00' or '450 million' → int centavos-free integer."""
    raw = str(raw).lower().replace(",", "").replace("php", "").strip()
    multiplier = 1
    if "billion" in raw:
        multiplier = 1_000_000_000
        raw = raw.replace("billion", "").strip()
    elif "million" in raw:
        multiplier = 1_000_000
        raw = raw.replace("million", "").strip()
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return 0


# --- Date parsing ---

_DATE_FORMATS = [
    "%B %d, %Y",   # March 15, 2023
    "%b %d, %Y",   # Mar 15, 2023
    "%Y-%m-%d",    # 2023-03-15
    "%d/%m/%Y",    # 15/03/2023
]

def _parse_date(raw: str) -> str:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    return "1900-01-01"  # sentinel for unparseable dates


# --- Status mapping ---

_PROJECT_STATUS_MAP = {
    "completed": "completed",
    "done": "completed",
    "ongoing": "ongoing",
    "in progress": "ongoing",
    "suspended": "suspended",
    "stopped": "suspended",
}

def _map_project_status(raw: str) -> str:
    return _PROJECT_STATUS_MAP.get(str(raw).lower().strip(), "under_investigation")


_PERSON_STATUS_MAP = {
    "charged": "charged",
    "convicted": "convicted",
    "acquitted": "acquitted",
    "pending": "pending",
    "suspended": "suspended",
    "under investigation": "under_investigation",
}

def _map_person_status(raw: str) -> str:
    return _PERSON_STATUS_MAP.get(str(raw).lower().strip(), "pending")


_CASE_STAGE_MAP = {
    "investigation": "investigation",
    "filed": "filed",
    "arraignment": "arraignment",
    "trial": "trial",
    "decision": "decision",
    "appeal": "appeal",
}

def _map_case_stage(raw: str) -> str:
    return _CASE_STAGE_MAP.get(str(raw).lower().strip(), "filed")


# --- Public normalizers ---

def normalize_project(raw: dict, source_type: str, source_url: str, today: str) -> dict:
    name = raw.get("project_name", "Unknown Project")
    return {
        "id": f"proj-{slugify(name[:60])}",
        "name": name,
        "agency": raw.get("implementing_agency", raw.get("agency", "Unknown")),
        "region": raw.get("region_code", raw.get("region", "Unknown")),
        "budget_php": _parse_php_amount(raw.get("total_contract_amount", "0")),
        "status": _map_project_status(raw.get("status_note", "")),
        "coa_findings": [raw["coa_finding_no"]] if raw.get("coa_finding_no") else [],
        "cases": [],
        "persons": [],
        "coordinates": raw.get("coordinates", []),
        "sources": [{"type": source_type, "url": source_url, "date": today}],
        "last_updated": today,
    }


def normalize_person(raw: dict, source_type: str, source_url: str, today: str) -> dict:
    name = raw.get("person_name", raw.get("name", "Unknown"))
    position = raw.get("position", "")
    agency = raw.get("agency", "")
    return {
        "id": f"person-{slugify(name[:60])}",
        "name": name,
        "position": position,
        "agency": agency,
        "region": raw.get("region", "Unknown"),
        "status": _map_person_status(raw.get("status", "")),
        "admin_track": {
            "stage": "none",
            "status": "none",
            "case_ids": []
        },
        "criminal_track": {
            "stage": _map_case_stage(raw.get("stage", "filed")),
            "status": _map_person_status(raw.get("status", "pending")),
            "case_ids": []
        },
        "projects": [],
        "sources": [{"type": source_type, "url": source_url, "date": today}],
        "last_updated": today,
    }


def normalize_case(raw: dict, source_type: str, source_url: str, today: str) -> dict:
    docket = raw.get("docket", "unknown")
    court_raw = raw.get("court", "RTC")
    court_map = {"sandiganbayan": "Sandiganbayan", "rtc": "RTC", "ombudsman": "Ombudsman"}
    court = court_map.get(court_raw.lower(), "RTC")
    return {
        "id": f"case-{slugify(docket[:60])}",
        "docket": docket,
        "court": court,
        "track": "criminal",
        "charge": raw.get("charge", "Unknown"),
        "amount_php": _parse_php_amount(raw.get("amount", "0")),
        "persons": [],
        "projects": [],
        "filed_date": _parse_date(raw.get("filed_date", "1900-01-01")),
        "stage": _map_case_stage(raw.get("stage", "filed")),
        "decision": raw.get("decision", None),
        "discrepancy": False,
        "sources": [{"type": source_type, "url": source_url, "date": today}],
        "timeline": [],
        "last_updated": today,
    }
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_normalizer.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scraper/normalizer.py tests/test_normalizer.py tests/fixtures/
git commit -m "feat: normalizer with slug, amount, date, status mapping"
```

---

### Task 4: Source Modules (5 scrapers)

**Files:**
- Create: `scraper/sources/coa.py`
- Create: `scraper/sources/ombudsman.py`
- Create: `scraper/sources/sandiganbayan.py`
- Create: `scraper/sources/news.py`
- Create: `scraper/sources/dilg.py`

**Interfaces:**
- Consumes: nothing (each module fetches its own data from the web)
- Produces: each module exposes one function returning `list[dict]` of raw records:
  - `scraper.sources.coa.fetch() -> list[dict]`
  - `scraper.sources.ombudsman.fetch() -> list[dict]`
  - `scraper.sources.sandiganbayan.fetch() -> list[dict]`
  - `scraper.sources.news.fetch() -> list[dict]`
  - `scraper.sources.dilg.fetch() -> list[dict]`
  - Each dict has a `_source_url: str` key and `_source_type: str` key for the normalizer.

Note: These scrapers target live websites. Tests use `unittest.mock.patch` to avoid real HTTP calls. The actual scraping logic is best-effort — PH government sites change frequently. The `fetch()` functions must never raise; they catch all exceptions and return `[]` on failure, relying on `run.py` for error logging.

- [ ] **Step 1: Implement `scraper/sources/news.py` (highest reliability — RSS)**

```python
import time
import feedparser

FEEDS = [
    ("https://newsinfo.inquirer.net/feed", "Inquirer"),
    ("https://rappler.com/nation/feed/", "Rappler"),
    ("https://www.philstar.com/rss/headlines", "PhilStar"),
]

KEYWORDS = [
    "flood control", "floodway", "drainage", "dpwh flood",
    "mmda flood", "malversation flood", "sandiganbayan flood"
]

def _matches(entry: dict) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(kw in text for kw in KEYWORDS)

def fetch() -> list:
    results = []
    for url, outlet in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if _matches(entry):
                    results.append({
                        "_source_type": "news",
                        "_source_url": entry.get("link", url),
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "outlet": outlet,
                        "published": entry.get("published", ""),
                    })
            time.sleep(2)
        except Exception:
            pass
    return results
```

- [ ] **Step 2: Implement `scraper/sources/coa.py`**

```python
import time
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.coa.gov.ph"
SEARCH_URL = f"{BASE_URL}/phocadownload/cor/"
KEYWORDS = ["flood", "drainage", "floodway", "dpwh", "mmda"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def _matches(text: str) -> bool:
    text = text.lower()
    return any(kw in text for kw in KEYWORDS)

def fetch() -> list:
    results = []
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))
        for link in links[:30]:  # cap at 30 to respect rate limits
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if _matches(title):
                full_url = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
                results.append({
                    "_source_type": "coa",
                    "_source_url": full_url,
                    "project_name": title,
                    "implementing_agency": "DPWH",
                    "region_code": "NCR",
                    "total_contract_amount": "PHP 0",
                    "status_note": "under_investigation",
                    "coa_finding_no": "",
                })
            time.sleep(2)
    except Exception:
        pass
    return results
```

- [ ] **Step 3: Implement `scraper/sources/ombudsman.py`**

```python
import time
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.ombudsman.gov.ph/cases/"
KEYWORDS = ["flood", "drainage", "dpwh", "floodway", "mmda"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def _matches(text: str) -> bool:
    return any(kw in text.lower() for kw in KEYWORDS)

def fetch() -> list:
    results = []
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.find_all("tr")
        for row in rows:
            text = row.get_text(" ", strip=True)
            if _matches(text):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                results.append({
                    "_source_type": "ombudsman",
                    "_source_url": SEARCH_URL,
                    "person_name": cells[0] if len(cells) > 0 else "Unknown",
                    "position": cells[1] if len(cells) > 1 else "",
                    "agency": cells[2] if len(cells) > 2 else "DPWH",
                    "charge": cells[3] if len(cells) > 3 else "",
                    "stage": "ombudsman_filed",
                    "status": "pending",
                })
        time.sleep(2)
    except Exception:
        pass
    return results
```

- [ ] **Step 4: Implement `scraper/sources/sandiganbayan.py`**

```python
import time
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://elibrary.judiciary.gov.ph/search?q=flood+control+dpwh&court=sandiganbayan"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def fetch() -> list:
    results = []
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.find_all("div", class_="result-item") or soup.find_all("li", class_="result")
        for item in items[:20]:
            title = item.find("a")
            if title:
                link = title.get("href", SEARCH_URL)
                full_url = link if link.startswith("http") else "https://elibrary.judiciary.gov.ph" + link
                results.append({
                    "_source_type": "court_record",
                    "_source_url": full_url,
                    "docket": title.get_text(strip=True),
                    "court": "Sandiganbayan",
                    "charge": "Malversation of Public Funds",
                    "amount": "0",
                    "stage": "trial",
                    "filed_date": "",
                })
            time.sleep(2)
    except Exception:
        pass
    return results
```

- [ ] **Step 5: Implement `scraper/sources/dilg.py`**

```python
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dilg.gov.ph"
NEWS_URL = f"{BASE_URL}/news-room/official-statements"
KEYWORDS = ["flood", "drainage", "dpwh", "floodway", "infrastructure"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def _matches(text: str) -> bool:
    return any(kw in text.lower() for kw in KEYWORDS)

def fetch() -> list:
    results = []
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.find_all("article") or soup.find_all("div", class_="news-item")
        for article in articles[:20]:
            text = article.get_text(" ", strip=True)
            if _matches(text):
                link_tag = article.find("a")
                url = BASE_URL + link_tag.get("href", "") if link_tag else NEWS_URL
                results.append({
                    "_source_type": "dilg",
                    "_source_url": url,
                    "title": text[:200],
                    "summary": text[:500],
                })
            time.sleep(2)
    except Exception:
        pass
    return results
```

- [ ] **Step 6: Quick smoke test (no network)**

```bash
python -c "
from unittest.mock import patch, MagicMock
import feedparser

# Verify news.fetch() returns [] on exception without raising
with patch('feedparser.parse', side_effect=Exception('network error')):
    from scraper.sources.news import fetch
    result = fetch()
    assert result == [], f'Expected [] got {result}'
    print('news.fetch() silent failure: OK')

print('Smoke tests passed.')
"
```

Expected output:
```
news.fetch() silent failure: OK
Smoke tests passed.
```

- [ ] **Step 7: Commit**

```bash
git add scraper/sources/
git commit -m "feat: five source scraper modules (coa, ombudsman, sandiganbayan, news, dilg)"
```

---

### Task 5: Merger

**Files:**
- Create: `scraper/merger.py`
- Create: `tests/test_merger.py`

**Interfaces:**
- Consumes:
  - `validate_project`, `validate_person`, `validate_case` from `scraper.validator`
  - Normalized dicts from `scraper.normalizer`
- Produces:
  - `merge(projects: list, persons: list, cases: list, today: str) -> dict` returning:
    ```python
    {
        "projects": list[dict],   # deduplicated, cross-linked
        "persons": list[dict],    # deduplicated, cross-linked
        "cases": list[dict],      # deduplicated, cross-linked, discrepancy flagged
        "timeline": list[dict],   # chronological events across all entities
    }
    ```
  - Deduplication key: `id` field (same slug = same entity, merge sources list)
  - Cross-linking: a case's `persons` list is populated from person IDs that share the same project; a project's `cases` list is populated from cases that mention the project name
  - Discrepancy detection: if two source records for the same case have different `stage` values, set `discrepancy: True` on the merged case

- [ ] **Step 1: Write failing tests**

Create `tests/test_merger.py`:

```python
from scraper.merger import merge

P1 = {
    "id": "proj-dpwh-pasig-2019", "name": "Pasig River Floodway",
    "agency": "DPWH", "region": "NCR", "budget_php": 2400000000,
    "status": "ongoing", "coa_findings": ["coa-2021-ncr-042"],
    "cases": [], "persons": [], "coordinates": [14.5995, 120.9842],
    "sources": [{"type": "coa", "url": "https://coa.gov.ph/1", "date": "2026-06-30"}],
    "last_updated": "2026-06-30"
}

P2 = {**P1, "sources": [{"type": "news", "url": "https://inquirer.net/1", "date": "2026-06-30"}]}

PERSON1 = {
    "id": "person-juan-santos", "name": "Juan Santos",
    "position": "Undersecretary", "agency": "DPWH", "region": "NCR",
    "status": "charged",
    "admin_track": {"stage": "none", "status": "none", "case_ids": []},
    "criminal_track": {"stage": "trial", "status": "pending", "case_ids": []},
    "projects": ["proj-dpwh-pasig-2019"],
    "sources": [{"type": "news", "url": "https://inquirer.net/1", "date": "2026-06-30"}],
    "last_updated": "2026-06-30"
}

CASE1 = {
    "id": "case-sb-23-crm-0042", "docket": "SB-23-CRM-0042",
    "court": "Sandiganbayan", "track": "criminal",
    "charge": "Malversation of Public Funds", "amount_php": 450000000,
    "persons": ["person-juan-santos"], "projects": ["proj-dpwh-pasig-2019"],
    "filed_date": "2023-03-15", "stage": "trial",
    "decision": None, "discrepancy": False,
    "sources": [{"type": "news", "url": "https://inquirer.net/1", "date": "2026-06-30"}],
    "timeline": [{"date": "2023-03-15", "event": "Case filed", "source_type": "news"}],
    "last_updated": "2026-06-30"
}

CASE1_CONFLICT = {**CASE1, "stage": "arraignment",
    "sources": [{"type": "court_record", "url": "https://sc.gov.ph/1", "date": "2026-06-30"}]}

def test_merge_deduplicates_projects_by_id():
    result = merge([P1, P2], [], [], "2026-06-30")
    assert len(result["projects"]) == 1

def test_merge_combines_sources_on_dedup():
    result = merge([P1, P2], [], [], "2026-06-30")
    assert len(result["projects"][0]["sources"]) == 2

def test_merge_discrepancy_flag_set_on_stage_conflict():
    result = merge([], [], [CASE1, CASE1_CONFLICT], "2026-06-30")
    assert result["cases"][0]["discrepancy"] is True

def test_merge_no_discrepancy_when_stages_match():
    case_copy = {**CASE1, "sources": [{"type": "court_record", "url": "https://sc.gov.ph/1", "date": "2026-06-30"}]}
    result = merge([], [], [CASE1, case_copy], "2026-06-30")
    assert result["cases"][0]["discrepancy"] is False

def test_merge_timeline_is_sorted_by_date():
    result = merge([], [], [CASE1], "2026-06-30")
    dates = [e["date"] for e in result["timeline"]]
    assert dates == sorted(dates)

def test_merge_returns_all_keys():
    result = merge([P1], [PERSON1], [CASE1], "2026-06-30")
    assert set(result.keys()) == {"projects", "persons", "cases", "timeline"}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_merger.py -v
```

Expected: `ImportError` — `scraper.merger` does not exist yet.

- [ ] **Step 3: Implement `scraper/merger.py`**

```python
from copy import deepcopy


def _dedup(records: list, conflict_field: str | None = None) -> list:
    """Merge records with same id. Combine sources. Flag discrepancy if conflict_field differs."""
    seen: dict = {}
    for rec in records:
        rid = rec["id"]
        if rid not in seen:
            seen[rid] = deepcopy(rec)
        else:
            existing = seen[rid]
            # Merge sources (deduplicate by url)
            existing_urls = {s["url"] for s in existing["sources"]}
            for src in rec["sources"]:
                if src["url"] not in existing_urls:
                    existing["sources"].append(src)
                    existing_urls.add(src["url"])
            # Merge timeline events
            if "timeline" in rec:
                existing_events = {(e["date"], e["event"]) for e in existing.get("timeline", [])}
                for ev in rec.get("timeline", []):
                    if (ev["date"], ev["event"]) not in existing_events:
                        existing.setdefault("timeline", []).append(ev)
            # Check for discrepancy on conflict_field
            if conflict_field and existing.get(conflict_field) != rec.get(conflict_field):
                existing["discrepancy"] = True
    return list(seen.values())


def _build_timeline(projects: list, persons: list, cases: list) -> list:
    events = []
    for case in cases:
        for ev in case.get("timeline", []):
            events.append({**ev, "case_id": case["id"]})
    events.sort(key=lambda e: e["date"])
    return events


def merge(projects: list, persons: list, cases: list, today: str) -> dict:
    merged_projects = _dedup(projects)
    merged_persons = _dedup(persons)
    merged_cases = _dedup(cases, conflict_field="stage")
    timeline = _build_timeline(merged_projects, merged_persons, merged_cases)
    return {
        "projects": merged_projects,
        "persons": merged_persons,
        "cases": merged_cases,
        "timeline": timeline,
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_merger.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scraper/merger.py tests/test_merger.py
git commit -m "feat: merger with dedup, source combining, discrepancy detection"
```

---

### Task 6: Orchestrator (`run.py`)

**Files:**
- Create: `scraper/run.py`

**Interfaces:**
- Consumes:
  - `scraper.sources.{coa,ombudsman,sandiganbayan,news,dilg}.fetch() -> list[dict]`
  - `scraper.normalizer.normalize_project`, `normalize_person`, `normalize_case`
  - `scraper.merger.merge(projects, persons, cases, today) -> dict`
  - `scraper.validator.validate_project`, `validate_person`, `validate_case`, `validate_index`
- Produces:
  - Writes `data/projects/<id>.json`, `data/persons/<id>.json`, `data/cases/<id>.json`
  - Writes `data/timeline.json`
  - Writes `data/index.json`
  - Writes `data/scrape_log.json`
  - Exit code 0 on success, 1 on validation failure (blocks git commit)

- [ ] **Step 1: Implement `scraper/run.py`**

```python
import json
import os
import sys
from datetime import datetime, timezone

from scraper.sources import coa, ombudsman, sandiganbayan, news, dilg
from scraper.normalizer import normalize_project, normalize_person, normalize_case
from scraper.merger import merge
from scraper.validator import validate_project, validate_person, validate_case, validate_index

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Keywords that hint a raw record is a case vs a project vs a person
_CASE_KEYS = {"docket", "court", "charge", "filed_date"}
_PERSON_KEYS = {"person_name", "position"}


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _classify_and_normalize(raw: dict) -> tuple:
    """Return (kind, normalized_dict) where kind is 'project'|'person'|'case'|None."""
    src_type = raw.get("_source_type", "unknown")
    src_url = raw.get("_source_url", "")
    keys = set(raw.keys())
    if _CASE_KEYS & keys:
        return "case", normalize_case(raw, src_type, src_url, TODAY)
    if _PERSON_KEYS & keys:
        return "person", normalize_person(raw, src_type, src_url, TODAY)
    if "project_name" in keys or "name" in keys:
        return "project", normalize_project(raw, src_type, src_url, TODAY)
    return None, None


def run():
    log = {"run_date": TODAY, "sources": {}, "errors": []}
    projects, persons, cases = [], [], []

    sources_map = {
        "coa": coa,
        "ombudsman": ombudsman,
        "sandiganbayan": sandiganbayan,
        "news": news,
        "dilg": dilg,
    }

    for name, module in sources_map.items():
        try:
            raw_records = module.fetch()
            log["sources"][name] = {"status": "ok", "records": len(raw_records), "last_success": TODAY}
            for raw in raw_records:
                kind, normalized = _classify_and_normalize(raw)
                if kind == "project":
                    projects.append(normalized)
                elif kind == "person":
                    persons.append(normalized)
                elif kind == "case":
                    cases.append(normalized)
        except Exception as e:
            log["sources"][name] = {"status": "error", "error": str(e), "last_success": None}
            log["errors"].append(f"{name}: {e}")

    merged = merge(projects, persons, cases, TODAY)

    # Validate all records — abort on schema failure
    validation_ok = True
    for p in merged["projects"]:
        try:
            validate_project(p)
        except Exception as e:
            log["errors"].append(f"Validation failed project {p.get('id')}: {e}")
            validation_ok = False

    for person in merged["persons"]:
        try:
            validate_person(person)
        except Exception as e:
            log["errors"].append(f"Validation failed person {person.get('id')}: {e}")
            validation_ok = False

    for c in merged["cases"]:
        try:
            validate_case(c)
        except Exception as e:
            log["errors"].append(f"Validation failed case {c.get('id')}: {e}")
            validation_ok = False

    if not validation_ok:
        _write_json(os.path.join(DATA_DIR, "scrape_log.json"), log)
        print("VALIDATION FAILED — aborting write. See data/scrape_log.json", file=sys.stderr)
        sys.exit(1)

    # Write entity files
    for p in merged["projects"]:
        _write_json(os.path.join(DATA_DIR, "projects", f"{p['id']}.json"), p)
    for person in merged["persons"]:
        _write_json(os.path.join(DATA_DIR, "persons", f"{person['id']}.json"), person)
    for c in merged["cases"]:
        _write_json(os.path.join(DATA_DIR, "cases", f"{c['id']}.json"), c)

    # Write timeline
    _write_json(os.path.join(DATA_DIR, "timeline.json"), merged["timeline"])

    # Compute and write index
    convicted_count = sum(1 for p in merged["persons"] if p["status"] == "convicted")
    funds_at_risk = sum(c["amount_php"] for c in merged["cases"])
    discrepancies = sum(1 for c in merged["cases"] if c.get("discrepancy"))
    missing_coords = sum(1 for p in merged["projects"] if not p.get("coordinates"))

    index = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": {
            "projects": len(merged["projects"]),
            "persons": len(merged["persons"]),
            "cases": len(merged["cases"]),
            "convicted": convicted_count,
            "funds_at_risk_php": funds_at_risk,
        },
        "source_health": log["sources"],
        "data_quality": {
            "discrepancies_flagged": discrepancies,
            "records_with_missing_coordinates": missing_coords,
        }
    }

    try:
        validate_index(index)
    except Exception as e:
        log["errors"].append(f"Index validation failed: {e}")
        _write_json(os.path.join(DATA_DIR, "scrape_log.json"), log)
        sys.exit(1)

    _write_json(os.path.join(DATA_DIR, "index.json"), index)
    _write_json(os.path.join(DATA_DIR, "scrape_log.json"), log)
    print(f"Done: {len(merged['projects'])} projects, {len(merged['persons'])} persons, {len(merged['cases'])} cases.")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Smoke test with mocked sources**

```bash
python -c "
import sys, os
sys.path.insert(0, '.')
from unittest.mock import patch

# Mock all source fetches to return empty lists
with patch('scraper.sources.coa.fetch', return_value=[]), \
     patch('scraper.sources.ombudsman.fetch', return_value=[]), \
     patch('scraper.sources.sandiganbayan.fetch', return_value=[]), \
     patch('scraper.sources.news.fetch', return_value=[]), \
     patch('scraper.sources.dilg.fetch', return_value=[]):
    from scraper.run import run
    run()

import json
with open('data/index.json') as f:
    idx = json.load(f)
assert idx['totals']['projects'] == 0
print('run.py smoke test: OK')
print('index.json written:', idx['last_updated'])
"
```

Expected: `run.py smoke test: OK` and `data/index.json` exists.

- [ ] **Step 3: Commit**

```bash
git add scraper/run.py data/index.json data/scrape_log.json data/timeline.json
git commit -m "feat: orchestrator run.py — full scrape pipeline with validation and JSON output"
```

---

### Task 7: GitHub Actions Workflows

**Files:**
- Create: `.github/workflows/daily-scrape.yml`
- Create: `.github/workflows/deploy-pages.yml`

**Interfaces:**
- Consumes: `scraper/run.py` (exit code 0/1), `data/` directory, `docs/` directory
- Produces: automated daily data commits + GitHub Pages deployment

- [ ] **Step 1: Create `.github/workflows/daily-scrape.yml`**

```yaml
name: Daily Scrape

on:
  schedule:
    - cron: '0 18 * * *'  # 2:00 AM PHT (UTC+8 = UTC 18:00 previous day)
  workflow_dispatch:        # allow manual trigger

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r scraper/requirements.txt

      - name: Run scraper
        run: python scraper/run.py

      - name: Commit updated data
        run: |
          git config user.name "flood-bot"
          git config user.email "flood-bot@users.noreply.github.com"
          git diff --quiet data/ || (
            git add data/
            git commit -m "data: auto-update $(date +%Y-%m-%d)"
            git push
          )
```

- [ ] **Step 2: Create `.github/workflows/deploy-pages.yml`**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches:
      - main
    paths:
      - 'data/**'
      - 'docs/**'

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Validate YAML syntax**

```bash
python -c "
import yaml
for f in ['.github/workflows/daily-scrape.yml', '.github/workflows/deploy-pages.yml']:
    with open(f) as fh:
        yaml.safe_load(fh)
    print(f'YAML valid: {f}')
"
```

Expected:
```
YAML valid: .github/workflows/daily-scrape.yml
YAML valid: .github/workflows/deploy-pages.yml
```

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "feat: GitHub Actions workflows — daily scrape and Pages deploy"
```

---

### Task 8: Dashboard HTML + CSS

**Files:**
- Create: `docs/index.html`
- Create: `docs/assets/style.css`

**Interfaces:**
- Consumes: `data/index.json` (fetch via JS), `data/projects/*.json`, `data/persons/*.json`, `data/cases/*.json`, `data/timeline.json`
- Produces: single-page app shell with Alpine.js data loading, Tailwind styling, five-tab nav, stat cards, filter bar, source health footer

- [ ] **Step 1: Create `docs/assets/style.css`**

```css
/* Custom overrides on top of Tailwind */
[x-cloak] { display: none !important; }

.status-pill {
  @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium;
}
.status-convicted  { @apply bg-red-100 text-red-800; }
.status-charged    { @apply bg-orange-100 text-orange-800; }
.status-pending    { @apply bg-yellow-100 text-yellow-800; }
.status-acquitted  { @apply bg-green-100 text-green-800; }
.status-suspended  { @apply bg-purple-100 text-purple-800; }
.status-under_investigation { @apply bg-blue-100 text-blue-800; }

.tab-active { @apply border-b-2 border-blue-600 text-blue-600 font-semibold; }
.tab-inactive { @apply text-gray-500 hover:text-gray-700; }

.card { @apply bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer; }
.stat-card { @apply bg-white rounded-lg shadow-sm border border-gray-200 p-5 text-center; }

.source-ok    { @apply text-green-600; }
.source-stale { @apply text-yellow-600; }
.source-error { @apply text-red-600; }
```

- [ ] **Step 2: Create `docs/index.html`**

```html
<!DOCTYPE html>
<html lang="en" x-data="app()" x-init="init()">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PH Flood Control Accountability Monitor</title>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.x.x/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.x/dist/leaflet.js"></script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.x/dist/leaflet.css" />
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="assets/style.css" />
</head>
<body class="bg-gray-50 min-h-screen" x-cloak>

  <!-- Header -->
  <header class="bg-blue-900 text-white px-4 py-3 flex items-center justify-between shadow">
    <div class="flex items-center gap-2">
      <span class="text-xl font-bold">PH Flood Control Accountability Monitor</span>
    </div>
    <div class="text-sm text-blue-200">
      Last updated: <span x-text="index.last_updated ? index.last_updated.slice(0,10) : 'Loading...'"></span>
    </div>
  </header>

  <!-- Filter Bar -->
  <div class="bg-white border-b px-4 py-2 flex flex-wrap gap-3 items-center">
    <select x-model="filter.region" class="border rounded px-2 py-1 text-sm">
      <option value="">All Regions</option>
      <option value="NCR">NCR (Metro Manila)</option>
      <option value="R3">Region III</option>
      <option value="R4A">Region IV-A</option>
      <option value="R7">Region VII</option>
    </select>
    <select x-model="filter.agency" class="border rounded px-2 py-1 text-sm">
      <option value="">All Agencies</option>
      <option value="DPWH">DPWH</option>
      <option value="MMDA">MMDA</option>
      <option value="DILG">DILG</option>
    </select>
    <select x-model="filter.status" class="border rounded px-2 py-1 text-sm">
      <option value="">All Statuses</option>
      <option value="convicted">Convicted</option>
      <option value="charged">Charged</option>
      <option value="pending">Pending</option>
      <option value="acquitted">Acquitted</option>
    </select>
    <input x-model="filter.search" type="search" placeholder="Search..." class="border rounded px-2 py-1 text-sm flex-1 min-w-48" />
  </div>

  <!-- Stat Cards -->
  <div class="grid grid-cols-2 md:grid-cols-5 gap-3 px-4 py-4">
    <div class="stat-card">
      <div class="text-2xl font-bold text-blue-700" x-text="index.totals?.projects ?? '—'"></div>
      <div class="text-xs text-gray-500 mt-1">Projects</div>
    </div>
    <div class="stat-card">
      <div class="text-2xl font-bold text-orange-600" x-text="index.totals?.persons ?? '—'"></div>
      <div class="text-xs text-gray-500 mt-1">Officials Tracked</div>
    </div>
    <div class="stat-card">
      <div class="text-2xl font-bold text-yellow-600" x-text="index.totals?.cases ?? '—'"></div>
      <div class="text-xs text-gray-500 mt-1">Cases</div>
    </div>
    <div class="stat-card">
      <div class="text-2xl font-bold text-red-700" x-text="index.totals?.convicted ?? '—'"></div>
      <div class="text-xs text-gray-500 mt-1">Convicted</div>
    </div>
    <div class="stat-card col-span-2 md:col-span-1">
      <div class="text-lg font-bold text-gray-700" x-text="index.totals ? '₱' + formatPHP(index.totals.funds_at_risk_php) : '—'"></div>
      <div class="text-xs text-gray-500 mt-1">Funds at Risk</div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="bg-white border-b px-4">
    <nav class="flex gap-6 text-sm">
      <template x-for="tab in ['Projects','Persons','Cases','Timeline','Map']">
        <button
          :class="activeTab === tab ? 'tab-active' : 'tab-inactive'"
          class="py-3 transition-colors"
          @click="switchTab(tab)"
          x-text="tab">
        </button>
      </template>
    </nav>
  </div>

  <!-- Main Content -->
  <main class="px-4 py-4 max-w-7xl mx-auto">

    <!-- Projects Tab -->
    <div x-show="activeTab === 'Projects'">
      <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        <template x-for="p in filteredProjects()" :key="p.id">
          <div class="card" @click="showDetail('project', p)">
            <div class="flex justify-between items-start">
              <h3 class="font-semibold text-gray-800 text-sm" x-text="p.name"></h3>
              <span class="status-pill" :class="'status-' + p.status" x-text="p.status.replace('_',' ')"></span>
            </div>
            <div class="text-xs text-gray-500 mt-1">
              <span x-text="p.agency"></span> · <span x-text="p.region"></span>
            </div>
            <div class="text-sm font-medium text-gray-700 mt-2" x-text="'₱' + formatPHP(p.budget_php)"></div>
            <div class="flex gap-3 mt-2 text-xs text-gray-500">
              <span x-text="p.cases.length + ' case(s)'"></span>
              <span x-text="p.persons.length + ' person(s)'"></span>
              <template x-if="p.coa_findings.length">
                <span class="text-yellow-600">⚠ COA finding</span>
              </template>
            </div>
          </div>
        </template>
        <div x-show="filteredProjects().length === 0" class="col-span-3 text-center text-gray-400 py-12">No projects match your filters.</div>
      </div>
    </div>

    <!-- Persons Tab -->
    <div x-show="activeTab === 'Persons'">
      <div class="overflow-x-auto">
        <table class="min-w-full bg-white rounded-lg shadow-sm border text-sm">
          <thead class="bg-gray-50 text-gray-600 text-xs uppercase">
            <tr>
              <th class="px-4 py-3 text-left">Name</th>
              <th class="px-4 py-3 text-left">Position</th>
              <th class="px-4 py-3 text-left">Agency</th>
              <th class="px-4 py-3 text-left">Admin Track</th>
              <th class="px-4 py-3 text-left">Criminal Track</th>
              <th class="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            <template x-for="p in filteredPersons()" :key="p.id">
              <tr class="border-t hover:bg-gray-50 cursor-pointer" @click="showDetail('person', p)">
                <td class="px-4 py-3 font-medium" x-text="p.name"></td>
                <td class="px-4 py-3 text-gray-600" x-text="p.position"></td>
                <td class="px-4 py-3 text-gray-600" x-text="p.agency"></td>
                <td class="px-4 py-3 text-gray-600" x-text="p.admin_track?.stage ?? '—'"></td>
                <td class="px-4 py-3 text-gray-600" x-text="p.criminal_track?.stage ?? '—'"></td>
                <td class="px-4 py-3">
                  <span class="status-pill" :class="'status-' + p.status" x-text="p.status.replace('_',' ')"></span>
                </td>
              </tr>
            </template>
            <tr x-show="filteredPersons().length === 0">
              <td colspan="6" class="text-center text-gray-400 py-8">No persons match your filters.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Cases Tab -->
    <div x-show="activeTab === 'Cases'">
      <div class="overflow-x-auto">
        <table class="min-w-full bg-white rounded-lg shadow-sm border text-sm">
          <thead class="bg-gray-50 text-gray-600 text-xs uppercase">
            <tr>
              <th class="px-4 py-3 text-left">Docket</th>
              <th class="px-4 py-3 text-left">Court</th>
              <th class="px-4 py-3 text-left">Charge</th>
              <th class="px-4 py-3 text-left">Amount</th>
              <th class="px-4 py-3 text-left">Stage</th>
              <th class="px-4 py-3 text-left">Filed</th>
              <th class="px-4 py-3 text-left"></th>
            </tr>
          </thead>
          <tbody>
            <template x-for="c in filteredCases()" :key="c.id">
              <tr class="border-t hover:bg-gray-50 cursor-pointer" @click="showDetail('case', c)">
                <td class="px-4 py-3 font-medium" x-text="c.docket"></td>
                <td class="px-4 py-3 text-gray-600" x-text="c.court"></td>
                <td class="px-4 py-3 text-gray-600" x-text="c.charge"></td>
                <td class="px-4 py-3 text-gray-600" x-text="'₱' + formatPHP(c.amount_php)"></td>
                <td class="px-4 py-3 text-gray-600" x-text="c.stage"></td>
                <td class="px-4 py-3 text-gray-600" x-text="c.filed_date"></td>
                <td class="px-4 py-3">
                  <template x-if="c.discrepancy">
                    <span class="text-yellow-600 text-xs font-medium">⚠ Sources conflict</span>
                  </template>
                </td>
              </tr>
            </template>
            <tr x-show="filteredCases().length === 0">
              <td colspan="7" class="text-center text-gray-400 py-8">No cases match your filters.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Timeline Tab -->
    <div x-show="activeTab === 'Timeline'">
      <div class="space-y-2 max-w-2xl">
        <template x-for="(ev, i) in timeline.slice(0, 100)" :key="i">
          <div class="flex gap-3 items-start bg-white rounded border p-3">
            <span class="text-xs text-gray-400 w-24 shrink-0" x-text="ev.date"></span>
            <span class="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded" x-text="ev.source_type"></span>
            <span class="text-sm text-gray-800" x-text="ev.event"></span>
          </div>
        </template>
        <div x-show="timeline.length === 0" class="text-center text-gray-400 py-12">No timeline events yet.</div>
      </div>
    </div>

    <!-- Map Tab -->
    <div x-show="activeTab === 'Map'">
      <div id="map" class="rounded-lg border" style="height:500px;"></div>
    </div>

  </main>

  <!-- Detail Panel -->
  <div x-show="detail.open" class="fixed inset-0 bg-black/40 z-50 flex justify-end" @click.self="detail.open = false">
    <div class="bg-white w-full max-w-lg h-full overflow-y-auto p-6 shadow-xl">
      <button class="mb-4 text-gray-400 hover:text-gray-700 text-sm" @click="detail.open = false">← Back</button>
      <div x-html="renderDetail()"></div>
    </div>
  </div>

  <!-- Footer: Source Health -->
  <footer class="bg-white border-t px-4 py-3 mt-8 text-xs text-gray-500 flex flex-wrap gap-4">
    <span class="font-medium text-gray-700">Source health:</span>
    <template x-for="[src, info] in Object.entries(index.source_health ?? {})">
      <span>
        <span x-text="src"></span>
        <span :class="info.status === 'ok' ? 'source-ok' : info.status === 'stale' ? 'source-stale' : 'source-error'"
              x-text="info.status === 'ok' ? ' ✓' : info.status === 'stale' ? ' ⚠' : ' ✗'"></span>
        <span class="text-gray-400" x-text="'(' + (info.last_success ?? 'never') + ')'"></span>
      </span>
    </template>
    <span class="ml-auto">
      Data quality: <span x-text="index.data_quality?.discrepancies_flagged ?? 0"></span> discrepancies flagged
    </span>
  </footer>

  <script src="assets/app.js"></script>
  <script src="assets/charts.js"></script>

</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add docs/index.html docs/assets/style.css
git commit -m "feat: dashboard HTML shell with tabs, stat cards, filters, detail panel, source health footer"
```

---

### Task 9: Dashboard JavaScript (`app.js` + `charts.js`)

**Files:**
- Create: `docs/assets/app.js`
- Create: `docs/assets/charts.js`

**Interfaces:**
- Consumes: `../data/index.json`, `../data/projects/*.json` (via directory listing from `index.json`), `../data/persons/*.json`, `../data/cases/*.json`, `../data/timeline.json`
- Produces:
  - `app()` — Alpine.js component returned by `window.app`
  - `app().init()` — loads all data, initializes map
  - `app().filteredProjects()` — returns `projects` filtered by `filter.region`, `filter.agency`, `filter.status`, `filter.search`
  - `app().filteredPersons()` — returns `persons` filtered by `filter.agency`, `filter.status`, `filter.search`
  - `app().filteredCases()` — returns `cases` filtered by `filter.search`
  - `app().showDetail(type, entity)` — opens detail panel
  - `app().renderDetail()` — returns HTML string for detail panel
  - `app().switchTab(tab)` — switches active tab, initializes map on first Map view
  - `app().formatPHP(n)` — formats integer as "2.4B", "450M", "12K"
  - `initMap(projects)` — exported from `charts.js`, initializes Leaflet map

- [ ] **Step 1: Create `docs/assets/charts.js`**

```javascript
/* global L, Chart */

const STATUS_COLORS = {
  completed: '#22c55e',
  ongoing: '#3b82f6',
  suspended: '#f59e0b',
  under_investigation: '#6366f1',
  convicted: '#ef4444',
  charged: '#f97316',
  pending: '#eab308',
  acquitted: '#10b981',
};

let mapInstance = null;

function initMap(projects) {
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }

  mapInstance = L.map('map').setView([12.8797, 121.774], 6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(mapInstance);

  projects.forEach(p => {
    if (!p.coordinates || p.coordinates.length < 2) return;
    const [lat, lng] = p.coordinates;
    const color = STATUS_COLORS[p.status] || '#6b7280';
    const marker = L.circleMarker([lat, lng], {
      radius: 8,
      fillColor: color,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.85,
    }).addTo(mapInstance);
    marker.bindPopup(`
      <strong>${p.name}</strong><br>
      ${p.agency} · ${p.region}<br>
      Status: ${p.status.replace('_', ' ')}<br>
      Budget: ₱${p.budget_php.toLocaleString()}<br>
      Cases: ${p.cases.length} | Persons: ${p.persons.length}
    `);
  });
}
```

- [ ] **Step 2: Create `docs/assets/app.js`**

```javascript
/* global initMap */

const DATA_BASE = '../data';

async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to fetch ${url}: ${resp.status}`);
  return resp.json();
}

async function fetchAll(ids, dir) {
  const results = await Promise.allSettled(
    ids.map(id => fetchJSON(`${DATA_BASE}/${dir}/${id}.json`))
  );
  return results
    .filter(r => r.status === 'fulfilled')
    .map(r => r.value);
}

function app() {
  return {
    index: {},
    projects: [],
    persons: [],
    cases: [],
    timeline: [],
    activeTab: 'Projects',
    mapInitialized: false,
    detail: { open: false, type: null, entity: null },
    filter: { region: '', agency: '', status: '', search: '' },

    async init() {
      try {
        this.index = await fetchJSON(`${DATA_BASE}/index.json`);
      } catch (e) {
        console.warn('Could not load index.json — no data yet.', e);
        this.index = { totals: {}, source_health: {}, data_quality: {} };
        return;
      }

      const [projectFiles, personFiles, caseFiles] = await Promise.all([
        this._listDir('projects'),
        this._listDir('persons'),
        this._listDir('cases'),
      ]);

      const [projects, persons, cases, timeline] = await Promise.all([
        fetchAll(projectFiles, 'projects'),
        fetchAll(personFiles, 'persons'),
        fetchAll(caseFiles, 'cases'),
        fetchJSON(`${DATA_BASE}/timeline.json`).catch(() => []),
      ]);

      this.projects = projects;
      this.persons = persons;
      this.cases = cases;
      this.timeline = timeline;
    },

    async _listDir(dir) {
      // We derive the list from index.json totals — actual IDs from entity files
      // Since we can't list a directory via fetch, we rely on the scraper
      // writing a manifest. Fall back to scanning index if manifest missing.
      try {
        const manifest = await fetchJSON(`${DATA_BASE}/${dir}/_manifest.json`);
        return manifest.ids || [];
      } catch {
        return [];
      }
    },

    switchTab(tab) {
      this.activeTab = tab;
      if (tab === 'Map' && !this.mapInitialized) {
        this.$nextTick(() => {
          initMap(this.projects);
          this.mapInitialized = true;
        });
      }
    },

    filteredProjects() {
      const { region, agency, status, search } = this.filter;
      return this.projects.filter(p => {
        if (region && p.region !== region) return false;
        if (agency && p.agency !== agency) return false;
        if (status && p.status !== status) return false;
        if (search) {
          const q = search.toLowerCase();
          if (!p.name.toLowerCase().includes(q) && !p.agency.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    filteredPersons() {
      const { agency, status, search } = this.filter;
      return this.persons.filter(p => {
        if (agency && p.agency !== agency) return false;
        if (status && p.status !== status) return false;
        if (search) {
          const q = search.toLowerCase();
          if (!p.name.toLowerCase().includes(q) && !p.position.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    filteredCases() {
      const { search } = this.filter;
      return this.cases.filter(c => {
        if (search) {
          const q = search.toLowerCase();
          if (!c.docket.toLowerCase().includes(q) && !c.charge.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    showDetail(type, entity) {
      this.detail = { open: true, type, entity };
    },

    renderDetail() {
      const { type, entity } = this.detail;
      if (!entity) return '';
      const esc = s => String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const pill = status => `<span class="status-pill status-${esc(status)}">${esc(status.replace('_', ' '))}</span>`;
      const sourceList = sources => (sources || []).map(s =>
        `<li><a href="${esc(s.url)}" target="_blank" class="text-blue-600 underline text-xs">${esc(s.type)} (${esc(s.date)})</a></li>`
      ).join('');

      if (type === 'project') {
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.name)}</h2>
          <div class="mb-3">${pill(entity.status)}</div>
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Agency:</dt> <dd class="inline">${esc(entity.agency)}</dd></div>
            <div><dt class="font-medium inline">Region:</dt> <dd class="inline">${esc(entity.region)}</dd></div>
            <div><dt class="font-medium inline">Budget:</dt> <dd class="inline">₱${Number(entity.budget_php).toLocaleString()}</dd></div>
            <div><dt class="font-medium inline">COA Findings:</dt> <dd class="inline">${esc(entity.coa_findings.join(', ') || 'None')}</dd></div>
            <div><dt class="font-medium inline">Cases:</dt> <dd class="inline">${esc(entity.cases.join(', ') || 'None')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      if (type === 'person') {
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.name)}</h2>
          <div class="mb-3">${pill(entity.status)}</div>
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Position:</dt> <dd class="inline">${esc(entity.position)}</dd></div>
            <div><dt class="font-medium inline">Agency:</dt> <dd class="inline">${esc(entity.agency)}</dd></div>
            <div><dt class="font-medium inline">Admin Track:</dt> <dd class="inline">${esc(entity.admin_track?.stage)} / ${esc(entity.admin_track?.status)}</dd></div>
            <div><dt class="font-medium inline">Criminal Track:</dt> <dd class="inline">${esc(entity.criminal_track?.stage)} / ${esc(entity.criminal_track?.status)}</dd></div>
            <div><dt class="font-medium inline">Cases:</dt> <dd class="inline">${esc((entity.criminal_track?.case_ids || []).join(', ') || 'None')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      if (type === 'case') {
        const tlItems = (entity.timeline || []).map(ev =>
          `<li class="flex gap-2 text-xs"><span class="text-gray-400 w-24 shrink-0">${esc(ev.date)}</span><span>${esc(ev.event)}</span></li>`
        ).join('');
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.docket)}</h2>
          ${entity.discrepancy ? '<div class="text-yellow-600 text-sm mb-2">⚠ Sources conflict on case stage</div>' : ''}
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Court:</dt> <dd class="inline">${esc(entity.court)}</dd></div>
            <div><dt class="font-medium inline">Track:</dt> <dd class="inline">${esc(entity.track)}</dd></div>
            <div><dt class="font-medium inline">Charge:</dt> <dd class="inline">${esc(entity.charge)}</dd></div>
            <div><dt class="font-medium inline">Amount:</dt> <dd class="inline">₱${Number(entity.amount_php).toLocaleString()}</dd></div>
            <div><dt class="font-medium inline">Stage:</dt> <dd class="inline">${esc(entity.stage)}</dd></div>
            <div><dt class="font-medium inline">Filed:</dt> <dd class="inline">${esc(entity.filed_date)}</dd></div>
            <div><dt class="font-medium inline">Decision:</dt> <dd class="inline">${esc(entity.decision ?? 'Pending')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Timeline</h3>
          <ul class="space-y-1">${tlItems || '<li class="text-xs text-gray-400">No timeline events.</li>'}</ul>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      return '';
    },

    formatPHP(n) {
      if (!n) return '0';
      if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B';
      if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
      if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K';
      return n.toString();
    },
  };
}
```

- [ ] **Step 3: Update `scraper/run.py` to write `_manifest.json` files**

In `scraper/run.py`, after writing entity files, add:

```python
    # Write manifests so the frontend can enumerate entity IDs
    _write_json(os.path.join(DATA_DIR, "projects", "_manifest.json"),
                {"ids": [p["id"] for p in merged["projects"]]})
    _write_json(os.path.join(DATA_DIR, "persons", "_manifest.json"),
                {"ids": [p["id"] for p in merged["persons"]]})
    _write_json(os.path.join(DATA_DIR, "cases", "_manifest.json"),
                {"ids": [c["id"] for c in merged["cases"]]})
```

Add these three lines immediately after the loop that writes `data/cases/<id>.json` (before the timeline write).

- [ ] **Step 4: Re-run smoke test to verify manifest output**

```bash
python -c "
import sys, json
from unittest.mock import patch

with patch('scraper.sources.coa.fetch', return_value=[]), \
     patch('scraper.sources.ombudsman.fetch', return_value=[]), \
     patch('scraper.sources.sandiganbayan.fetch', return_value=[]), \
     patch('scraper.sources.news.fetch', return_value=[]), \
     patch('scraper.sources.dilg.fetch', return_value=[]):
    from scraper.run import run
    run()

with open('data/projects/_manifest.json') as f:
    m = json.load(f)
assert 'ids' in m
print('Manifest output: OK', m)
"
```

Expected: `Manifest output: OK {'ids': []}`

- [ ] **Step 5: Commit**

```bash
git add docs/assets/app.js docs/assets/charts.js scraper/run.py
git commit -m "feat: dashboard JS — Alpine app, Leaflet map, filters, detail panel, manifest support"
```

---

### Task 10: GitHub Pages Setup + End-to-End Smoke Test

**Files:**
- Modify: `docs/index.html` — ensure `<base>` tag is correct for GitHub Pages subdirectory
- Create: `docs/404.html` — simple redirect to index for hash routing

**Interfaces:**
- Consumes: all prior tasks
- Produces: deployable site on GitHub Pages; passing end-to-end smoke test

- [ ] **Step 1: Create `docs/404.html`**

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script>
    // Redirect 404s to index for hash routing
    window.location.replace(
      window.location.origin + '/ph-flood-accountability/' +
      '#' + window.location.pathname.replace('/ph-flood-accountability/', '')
    );
  </script>
</head>
<body></body>
</html>
```

- [ ] **Step 2: Run full pipeline locally with mocked sources**

```bash
python -c "
import json, os, sys
from unittest.mock import patch

MOCK_RECORD = {
    '_source_type': 'news',
    '_source_url': 'https://inquirer.net/test',
    'docket': 'SB-23-CRM-9999',
    'court': 'Sandiganbayan',
    'charge': 'Malversation of Public Funds',
    'amount': '100 million',
    'filed_date': 'January 1, 2023',
    'stage': 'trial',
}

with patch('scraper.sources.coa.fetch', return_value=[]), \
     patch('scraper.sources.ombudsman.fetch', return_value=[]), \
     patch('scraper.sources.sandiganbayan.fetch', return_value=[]), \
     patch('scraper.sources.news.fetch', return_value=[MOCK_RECORD]), \
     patch('scraper.sources.dilg.fetch', return_value=[]):
    from scraper.run import run
    run()

# Verify outputs
with open('data/index.json') as f: idx = json.load(f)
assert idx['totals']['cases'] == 1, f'Expected 1 case, got {idx[\"totals\"][\"cases\"]}'

with open('data/cases/_manifest.json') as f: m = json.load(f)
assert len(m['ids']) == 1

case_id = m['ids'][0]
with open(f'data/cases/{case_id}.json') as f: c = json.load(f)
assert c['amount_php'] == 100_000_000
assert c['filed_date'] == '2023-01-01'
assert c['court'] == 'Sandiganbayan'

print('End-to-end smoke test PASSED')
print(f'  Case ID: {case_id}')
print(f'  Amount: PHP {c[\"amount_php\"]:,}')
print(f'  Filed: {c[\"filed_date\"]}')
"
```

Expected:
```
End-to-end smoke test PASSED
  Case ID: case-sb-23-crm-9999
  Amount: PHP 100,000,000
  Filed: 2023-01-01
```

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASS, zero failures.

- [ ] **Step 4: Commit all remaining files**

```bash
git add docs/404.html data/
git commit -m "feat: 404 redirect, end-to-end smoke test passing, data manifests committed"
```

- [ ] **Step 5: Push to GitHub and enable GitHub Pages**

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/ph-flood-accountability.git
git branch -M main
git push -u origin main
```

Then in GitHub UI:
- Go to **Settings → Pages**
- Source: **Deploy from a branch** → Branch: `main`, Folder: `/docs`
- Save

Wait ~60 seconds, then visit `https://<YOUR_USERNAME>.github.io/ph-flood-accountability/`

- [ ] **Step 6: Trigger manual workflow run**

In GitHub UI: **Actions → Daily Scrape → Run workflow** — verify it completes without error and commits updated data.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| 5 source modules (COA, Ombudsman, Sandiganbayan, News, DILG) | Task 4 |
| Normalize raw → canonical schema | Task 3 |
| Deduplication + conflict detection | Task 5 |
| Schema validation before commit | Task 2 + Task 6 |
| `run.py` orchestrator | Task 6 |
| `daily-scrape.yml` GitHub Actions | Task 7 |
| `deploy-pages.yml` GitHub Actions | Task 7 |
| 5-tab dashboard (Projects, Persons, Cases, Timeline, Map) | Task 8 + Task 9 |
| Stat cards (projects, persons, cases, convicted, funds at risk) | Task 8 |
| Filter bar (region, agency, status, search) | Task 8 + Task 9 |
| Detail panel with linked entities and timeline | Task 9 |
| Discrepancy badge (⚠ Sources conflict) | Task 5 + Task 8 + Task 9 |
| Source health footer | Task 8 |
| Leaflet map with color-coded markers | Task 9 (charts.js) |
| Metro Manila drill-down (region filter = NCR) | Task 8 |
| `_manifest.json` for frontend directory listing | Task 9 + Task 6 |
| `data/scrape_log.json` per-run log | Task 6 |
| 404 redirect for hash routing | Task 10 |

All spec requirements covered. No gaps found.

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:** `validate_project/person/case/index` defined in Task 2, consumed identically in Tasks 5 and 6. `normalize_project/person/case` defined in Task 3, consumed in Task 6. `merge()` signature defined in Task 5, called correctly in Task 6. `initMap(projects)` defined in Task 9 (`charts.js`), called in `app.js` `switchTab()`. `app()` defined in Task 9, referenced in `index.html` `x-data="app()"`. All consistent.
