import http.client
import json
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *

with open("cache.json") as json_file:
    cache = json.load(json_file)


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality == "Registered Nurse - Oncology":
        return [
            {"keywords": ["Registered Nurse", "Oncology"], "operator": "AND"},
            {"keywords": ["Nurse", "Oncology", "RN", "Cancer"], "operator": "OR"},
        ]
    if speciality == "Pharmacist - Oncology":
        ...
    # todo: add rest of keyword phases

    raise ValueError("Invalid Speciality")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return f'(intitle:"{doc_name}") site:{site} ' + '"' + f"\" {keyword['operator']} \"".join(keyword["keywords"]) + '"'


def google_search(search_term) -> List[GoogleResults]:
    if search_term in cache:
        return cache[search_term]
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

    final_search_results: List[GoogleResults] = [
        {"title": result["title"], "link": result["link"], "description": result["description"]}
        for result in json_data["results"]
    ]
    cache[search_term] = final_search_results
    with open("cache.json", "w") as json_file:
        json.dump(cache, json_file)
    return final_search_results
