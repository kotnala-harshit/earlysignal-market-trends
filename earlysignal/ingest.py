import csv
import json
import os
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FIELDS = ["observed_at", "country", "source", "product", "category", "value",
          "sentiment", "purchase_intent", "seller_count", "ad_intensity", "incumbent_share", "is_demo"]


def read_csv(path: str) -> list[dict]:
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = set(FIELDS[:7])
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
    return [{field: row.get(field, 0) for field in FIELDS} for row in rows]


def youtube(keyword: str, country: str, category: str) -> list[dict]:
    """Fetch aggregate keyword video statistics via the official YouTube API."""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY is required")
    query = urlencode({"part": "snippet", "q": keyword, "type": "video", "regionCode": country,
                       "publishedAfter": "2020-01-01T00:00:00Z", "maxResults": 25, "key": key})
    with urlopen(f"https://www.googleapis.com/youtube/v3/search?{query}", timeout=20) as response:
        payload = json.load(response)
    ids = ",".join(item["id"]["videoId"] for item in payload.get("items", []))
    if not ids:
        return []
    stats_query = urlencode({"part": "statistics", "id": ids, "key": key})
    with urlopen(f"https://www.googleapis.com/youtube/v3/videos?{stats_query}", timeout=20) as response:
        stats = json.load(response)
    views = sum(int(item["statistics"].get("viewCount", 0)) for item in stats.get("items", []))
    return [{"observed_at": date.today().isoformat(), "country": country, "source": "youtube",
             "product": keyword, "category": category, "value": views, "sentiment": 0,
             "purchase_intent": 0, "seller_count": 0, "ad_intensity": 0,
             "incumbent_share": 0, "is_demo": 0}]


def google_trends(keyword: str, country: str, category: str) -> list[dict]:
    """Call an approved official Google Trends alpha endpoint configured by the user."""
    endpoint, key = os.getenv("GOOGLE_TRENDS_API_URL"), os.getenv("GOOGLE_TRENDS_API_KEY")
    if not endpoint or not key:
        raise RuntimeError("Approved GOOGLE_TRENDS_API_URL and GOOGLE_TRENDS_API_KEY are required")
    request = Request(endpoint, data=json.dumps({"terms": [keyword], "geo": country}).encode(),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return [{"observed_at": point["date"], "country": country, "source": "search",
             "product": keyword, "category": category, "value": point["value"], "sentiment": 0,
             "purchase_intent": 0, "seller_count": 0, "ad_intensity": 0,
             "incumbent_share": 0, "is_demo": 0} for point in payload["timeline"]]


def upsert(connection, rows: list[dict]) -> int:
    sql = f"INSERT OR REPLACE INTO observations ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})"
    values = [[row.get(field, 0) for field in FIELDS] for row in rows]
    connection.executemany(sql, values)
    connection.commit()
    return len(values)
