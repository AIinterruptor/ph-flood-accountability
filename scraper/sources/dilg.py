import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dilg.gov.ph"
NEWS_URL = f"{BASE_URL}/news-room/official-statements"
KEYWORDS = ["flood", "drainage", "dpwh", "floodway", "infrastructure"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def _matches(text: str) -> bool:
    return any(kw in text.lower() for kw in KEYWORDS)

def fetch() -> list:
    results = []
    try:
        resp = requests.get(NEWS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.find_all("article") or soup.find_all("div", class_="news-item")
        for article in articles[:20]:
            text = article.get_text(" ", strip=True)
            if _matches(text):
                link_tag = article.find("a")
                url = BASE_URL + link_tag.get("href", "") if link_tag else NEWS_URL
                results.append({
                    "_source_type": "dilg",
                    "_source_url": url,
                    "title": text[:200],
                    "summary": text[:500],
                })
            time.sleep(2)
    except Exception:
        pass
    return results
