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
