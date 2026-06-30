import time
import requests
from bs4 import BeautifulSoup

# Ombudsman press releases — their public case search portal is offline.
# Use their news/press release archive instead which lists filed cases.
BASE_URL = "https://ombudsman.gov.ph"
URLS = [
    f"{BASE_URL}/news/",
    f"{BASE_URL}/press-releases/",
]
KEYWORDS = ["flood", "drainage", "dpwh", "floodway", "mmda", "malversation",
            "graft", "plunder", "infrastructure", "mwss"]
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
            # Try common CMS patterns for article links
            links = []
            for tag in soup.find_all(["article", "div"], class_=lambda c: c and any(
                    x in c for x in ["post", "news", "item", "entry", "release"])):
                a = tag.find("a", href=True)
                if a:
                    links.append((a.get("href", ""), tag.get_text(" ", strip=True)))
            # Fallback: all internal links in main content
            if not links:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if BASE_URL in href or href.startswith("/"):
                        links.append((href, a.get_text(strip=True)))

            for href, text in links[:40]:
                if not _matches(text):
                    continue
                full_url = href if href.startswith("http") else BASE_URL + href
                results.append({
                    "_source_type": "ombudsman",
                    "_source_url": full_url,
                    "_entity_kind": "person",
                    "person_name": text[:80],
                    "position": "",
                    "agency": "DPWH",
                    "charge": text[:200],
                    "stage": "ombudsman_filed",
                    "status": "charged",
                })
            time.sleep(2)
        except Exception:
            pass
    return results
