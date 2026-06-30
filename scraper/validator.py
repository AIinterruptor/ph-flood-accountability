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
