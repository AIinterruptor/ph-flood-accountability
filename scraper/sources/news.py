import time
import feedparser

FEEDS = [
    ("https://newsinfo.inquirer.net/feed", "Inquirer"),
    ("https://rappler.com/nation/feed/", "Rappler"),
    ("https://www.philstar.com/rss/headlines", "PhilStar"),
]

KEYWORDS = [
    "flood control", "floodway", "drainage", "dpwh flood",
    "mmda flood", "malversation flood", "sandiganbayan flood"
]

def _matches(entry: dict) -> bool:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(kw in text for kw in KEYWORDS)

def fetch() -> list:
    results = []
    for url, outlet in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if _matches(entry):
                    results.append({
                        "_source_type": "news",
                        "_source_url": entry.get("link", url),
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "outlet": outlet,
                        "published": entry.get("published", ""),
                    })
            time.sleep(2)
        except Exception:
            pass
    return results
