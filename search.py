import http.client
import json
from typing import List, Dict
from urllib.parse import quote_plus


def get_search_query(doc_name: str, site: str, keywords: List[str]) -> str:
    return f"{doc_name} site:{site} " + " ".join([f'"{word}"' for word in keywords])


def google_search(search_term) -> List[Dict]:
    conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
    conn.request(
        "GET",
        f"/api/v1/search/q={quote_plus(search_term)}&num=100",
        headers={
            "x-rapidapi-key": "FJviVQShGTmshjDIBZX74GdlFRkOp1eUIT0jsnL7BOQJL4fWV6",
            "x-rapidapi-host": "google-search3.p.rapidapi.com",
        },
    )
    try:
        data = conn.getresponse().read().decode("utf-8")
        json_data = json.loads(data)
    except Exception:
        print("Error scrapping Google")
        return []
    return [
        {"title": result["title"], "link": result["link"], "description": result["description"]}
        for result in json_data["results"]
    ]
