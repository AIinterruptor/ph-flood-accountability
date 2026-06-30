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
    """Parse 'PHP 2,400,000,000.00' or '450 million' -> int centavos-free integer."""
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
            "status": {
                "charged": "pending",
                "pending": "pending",
                "convicted": "convicted",
                "acquitted": "acquitted",
                "suspended": "pending",
                "under_investigation": "pending",
            }.get(raw.get("status", "").lower().strip(), "pending"),
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
