import re
import time
import feedparser

FEEDS = [
    ("https://newsinfo.inquirer.net/feed", "Inquirer"),
    ("https://rappler.com/nation/feed/", "Rappler"),
    ("https://www.philstar.com/rss/headlines", "PhilStar"),
    ("https://www.philstar.com/rss/nation", "PhilStar-Nation"),
    ("https://cnnphilippines.com/rss/latest.rss", "CNN Philippines"),
    ("https://mb.com.ph/feed/", "Manila Bulletin"),
    ("https://businessmirror.com.ph/feed/", "Business Mirror"),
    ("https://www.manilatimes.net/feed/", "Manila Times"),
]

# Broad keywords — capture anything flood/drainage/DPWH accountability-related
KEYWORDS = [
    "flood control", "floodway", "drainage project", "dpwh",
    "flood infrastructure", "flood mitigation", "anti-flood",
    "malversation", "sandiganbayan", "ombudsman",
    "plunder", "graft", "overpriced", "overpricing", "ghost project",
    "irregularities", "coa findings", "commission on audit",
    "estafa", "bid rigging", "anomalous", "behest",
    "bribe", "kickback", "corruption", "charged", "convicted",
    "mwss", "mmda flood", "pumping station",
]

# PH agency names that suggest infrastructure accountability
AGENCY_KEYWORDS = ["dpwh", "mmda", "mwss", "dilg", "nha", "neda"]

# Patterns to extract person names from article text
_NAME_RE = re.compile(
    r'\b(?:Secretary|Undersecretary|Director|Engineer|Mayor|Governor|'
    r'General Manager|Administrator|Head|Chief|Officer|former|ex-)\s+'
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
    re.MULTILINE
)

# Patterns to extract docket/case numbers
_DOCKET_RE = re.compile(
    r'\b(?:SB|OMB|RTC|MTC)-[\w-]+-\d{2,6}\b|\bCriminal Case No\.?\s*[\d-]+\b',
    re.IGNORECASE
)

# Patterns to extract peso amounts
_AMOUNT_RE = re.compile(
    r'(?:PHP|P|₱)\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|M|B)?|'
    r'([\d,]+(?:\.\d+)?)\s*(?:million|billion)\s*(?:peso)',
    re.IGNORECASE
)


def _matches(entry: dict) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    if any(kw in text for kw in KEYWORDS):
        return True
    # Also match if any agency keyword appears alongside financial/legal terms
    has_agency = any(ag in text for ag in AGENCY_KEYWORDS)
    has_legal = any(w in text for w in ["charged", "case", "plunder", "graft", "conviction"])
    return has_agency and has_legal


def _parse_amount(text: str) -> int:
    m = _AMOUNT_RE.search(text)
    if not m:
        return 0
    raw = m.group(1) or m.group(2)
    if not raw:
        return 0
    num = float(raw.replace(",", ""))
    full_text = m.group(0).lower()
    if "billion" in full_text or full_text.endswith("b"):
        num *= 1_000_000_000
    elif "million" in full_text or full_text.endswith("m"):
        num *= 1_000_000
    return int(num)


def _extract_records(entry: dict, outlet: str, url: str) -> list:
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    link = entry.get("link", url)
    published = entry.get("published", "")
    combined = title + " " + summary
    amount = _parse_amount(combined)

    # Try to extract docket number → emit as case
    docket_match = _DOCKET_RE.search(combined)
    if docket_match:
        docket = docket_match.group(0)
        charge = title[:200]
        return [{
            "_source_type": "news",
            "_source_url": link,
            "_entity_kind": "case",
            "docket": docket,
            "court": _infer_court(docket),
            "track": "criminal",
            "charge": charge,
            "amount_php": str(amount),
            "filed_date": "",
            "stage": "filed",
            "outlet": outlet,
            "published": published,
        }]

    # Try to extract named persons → emit as persons
    names = _NAME_RE.findall(combined)
    if names:
        records = []
        for name in names[:3]:  # cap at 3 per article
            records.append({
                "_source_type": "news",
                "_source_url": link,
                "_entity_kind": "person",
                "person_name": name.strip()[:80],
                "position": _infer_position(combined),
                "agency": _infer_agency(combined),
                "stage": "filed",
                "status": _infer_status(combined),
                "outlet": outlet,
                "published": published,
            })
        return records

    # Fallback: emit as a project if the article is about a DPWH/flood project
    text_lower = combined.lower()
    if any(kw in text_lower for kw in ["flood control project", "drainage project", "floodway project", "pumping station"]):
        return [{
            "_source_type": "news",
            "_source_url": link,
            "_entity_kind": "project",
            "project_name": title[:200],
            "implementing_agency": _infer_agency(combined),
            "region_code": _infer_region(combined),
            "total_contract_amount": str(amount) if amount else "PHP 0",
            "status_note": "under_investigation",
            "outlet": outlet,
            "published": published,
        }]

    # Last resort: emit as a generic person with headline as name placeholder
    return [{
        "_source_type": "news",
        "_source_url": link,
        "_entity_kind": "person",
        "person_name": title[:80],
        "position": "",
        "agency": _infer_agency(combined),
        "stage": "investigation",
        "status": "under_investigation",
        "outlet": outlet,
        "published": published,
    }]


def _infer_court(docket: str) -> str:
    d = docket.upper()
    if d.startswith("SB"):
        return "Sandiganbayan"
    if d.startswith("OMB"):
        return "Ombudsman"
    return "RTC"


def _infer_position(text: str) -> str:
    for title in ["Secretary", "Undersecretary", "Director", "Mayor", "Governor",
                  "General Manager", "Administrator", "Engineer"]:
        if title.lower() in text.lower():
            return title
    return ""


def _infer_agency(text: str) -> str:
    t = text.upper()
    for agency in ["DPWH", "MMDA", "MWSS", "DILG", "NEDA", "NHA"]:
        if agency in t:
            return agency
    return "Unknown"


def _infer_region(text: str) -> str:
    t = text.lower()
    if "metro manila" in t or "ncr" in t or "mmda" in t:
        return "NCR"
    if "cebu" in t:
        return "Region VII"
    if "davao" in t:
        return "Region XI"
    if "iloilo" in t:
        return "Region VI"
    return "Unknown"


def _infer_status(text: str) -> str:
    t = text.lower()
    if "convicted" in t or "guilty" in t:
        return "convicted"
    if "acquitted" in t:
        return "acquitted"
    if "suspended" in t:
        return "suspended"
    if "charged" in t or "filed" in t or "indicted" in t:
        return "charged"
    return "under_investigation"


def fetch() -> list:
    results = []
    seen_links = set()
    for url, outlet in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link in seen_links:
                    continue
                if _matches(entry):
                    seen_links.add(link)
                    results.extend(_extract_records(entry, outlet, url))
            time.sleep(1)
        except Exception:
            pass
    return results
