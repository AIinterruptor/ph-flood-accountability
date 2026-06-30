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
