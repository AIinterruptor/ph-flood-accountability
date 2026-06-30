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

    # Write manifest files
    _write_json(
        os.path.join(DATA_DIR, "projects", "_manifest.json"),
        {"ids": [p["id"] for p in merged["projects"]]}
    )
    _write_json(
        os.path.join(DATA_DIR, "persons", "_manifest.json"),
        {"ids": [person["id"] for person in merged["persons"]]}
    )
    _write_json(
        os.path.join(DATA_DIR, "cases", "_manifest.json"),
        {"ids": [c["id"] for c in merged["cases"]]}
    )

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
