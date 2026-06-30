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
