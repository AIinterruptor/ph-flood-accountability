import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dilg.gov.ph"
# Correct DILG URLs discovered via browser inspection
URLS = [
    f"{BASE_URL}/news-archive/",
    f"{BASE_URL}/whatsnew-archive/",
]
KEYWORDS = ["flood", "drainage", "dpwh", "floodway", "infrastructure",
            "malversation", "graft", "charged", "sandiganbayan", "ombudsman"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}


def _matches(text: str) -> bool:
    return any(kw in text.lower() for kw in KEYWORDS)


def fetch() -> list:
    results = []
    for url in URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            # DILG uses h2/h3 inside article divs for post titles
            articles = soup.find_all(["article", "div"],
                                     class_=lambda c: c and any(
                                         x in c for x in ["post", "news", "item", "entry"]))
            if not articles:
                # Fallback: grab all links in main content area
                main = soup.find("main") or soup.find("div", id="content") or soup
                articles = main.find_all("a", href=True)

            for item in articles[:30]:
                if hasattr(item, "get_text"):
                    text = item.get_text(" ", strip=True)
                else:
                    text = item.string or ""
                if not _matches(text):
                    continue
                link_tag = item.find("a") if item.name != "a" else item
                href = link_tag.get("href", url) if link_tag else url
                full_url = href if href.startswith("http") else BASE_URL + href
                results.append({
                    "_source_type": "dilg",
                    "_source_url": full_url,
                    "_entity_kind": "project",
                    "project_name": text[:200],
                    "implementing_agency": "DILG",
                    "region_code": "Unknown",
                    "total_contract_amount": "PHP 0",
                    "status_note": "under_investigation",
                })
            time.sleep(2)
        except Exception:
            pass
    return results
