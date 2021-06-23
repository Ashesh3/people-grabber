import http.client, json
from typing import List
from urllib.parse import quote_plus
from utils.types import *
from utils.config import config
from utils.cache import Cache

google_cache = Cache("google")

rapid_api_keys = config["RAPIDAPI_KEYS"]
rapid_api_index = 0


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality in config["KEYWORDS"]:
        return config["KEYWORDS"][speciality]
    raise ValueError(f"Invalid Speciality: {speciality}")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return f'(intitle:"{doc_name}") site:{site} ' + '"' + f"\" {keyword['operator']} \"".join(keyword["keywords"]) + '"'


def google_search(search_term: str, seach_type, max_terms: int = 5) -> List[GoogleResults]:
    if seach_type not in ["search", "images"]:
        raise RuntimeError("Invalid Google Search")
    if f"{seach_type}:{search_term}" in google_cache:
        return google_cache[f"{seach_type}:{search_term}"][:max_terms]
    if config["DRY_RUN"]:
        return []
    global rapid_api_index
    err_count = 0
    json_data = {}
    while err_count < len(rapid_api_keys):
        try:
            conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
            conn.request(
                "GET",
                f"/api/v1/{seach_type}/q={quote_plus(search_term)}&num=100",
                headers={
                    "x-rapidapi-key": rapid_api_keys[rapid_api_index % len(rapid_api_keys)],
                    "x-rapidapi-host": "google-search3.p.rapidapi.com",
                },
            )
            data = conn.getresponse().read().decode("utf-8")
            json_data = json.loads(data)
            if "message" in json_data:
                raise ValueError("Error Scrapping Google.. ", json_data["message"])
            if seach_type == "search":
                final_search_results: List[GoogleResults] = [
                    {"title": result["title"], "link": result["link"], "description": result["description"]}
                    for result in json_data["results"]
                ]
                google_cache[f"{seach_type}:{search_term}"] = final_search_results
                return final_search_results[:max_terms]
            elif seach_type == "images":
                final_image_results: List[GoogleResults] = [
                    {"title": result["image"]["alt"], "link": result["image"]["src"], "description": result["link"]["href"]}
                    for result in json_data["image_results"]
                ]
                google_cache[f"{seach_type}:{search_term}"] = final_image_results
                return final_image_results[:max_terms]
        except Exception as e:
            rapid_api_index += 1
            print(f"RapidApi Switching key... {rapid_api_index % len(rapid_api_keys)} [{e.__class__}: {e}] [{json_data}]")
            err_count += 1
    raise ValueError("Error in RapidAPI..")
