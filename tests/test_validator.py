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
