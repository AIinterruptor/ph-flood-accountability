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
