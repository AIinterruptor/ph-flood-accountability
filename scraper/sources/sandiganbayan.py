import time
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://elibrary.judiciary.gov.ph/search?q=flood+control+dpwh&court=sandiganbayan"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FloodWatchBot/1.0; +https://github.com/ph-flood-accountability)"}

def fetch() -> list:
    results = []
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        items = soup.find_all("div", class_="result-item") or soup.find_all("li", class_="result")
        for item in items[:20]:
            title = item.find("a")
            if title:
                link = title.get("href", SEARCH_URL)
                full_url = link if link.startswith("http") else "https://elibrary.judiciary.gov.ph" + link
                results.append({
                    "_source_type": "court_record",
                    "_source_url": full_url,
                    "docket": title.get_text(strip=True),
                    "court": "Sandiganbayan",
                    "charge": "Malversation of Public Funds",
                    "amount": "0",
                    "stage": "trial",
                    "filed_date": "",
                })
            time.sleep(2)
    except Exception:
        pass
    return results
