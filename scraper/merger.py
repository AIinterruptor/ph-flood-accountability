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
