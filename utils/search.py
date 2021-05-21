import http.client
import json
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *
import requests
import re
from fcache.cache import FileCache

cache = FileCache("doctor", flag="cs", app_cache_dir="cache")


# nephrology, nephrologist, kidney, renal, nephro


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality == "Registered Nurse - Oncology":
        return [
            {"keywords": ["Registered Nurse", "Oncology"], "operator": "AND"},
            {"keywords": ["Nurse", "Oncology", " RN", "Cancer"], "operator": "OR"},
        ]
    if speciality in ["NEPHROLOGY", "PEDIATRIC NEPHROLOGY"]:
        return [
            {"keywords": ["nephrology", "nephrologist", "kidney", "renal", "nephro", "MD"], "operator": "OR"},
        ]
    # todo: add rest of keyword phases

    raise ValueError("Invalid Speciality")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return f'(intitle:"{doc_name}") site:{site} ' + '"' + f"\" {keyword['operator']} \"".join(keyword["keywords"]) + '"'


def google_search(search_term) -> List[GoogleResults]:
    if search_term in cache:
        return cache[search_term]  # type: ignore
    try:
        conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
        conn.request(
            "GET",
            f"/api/v1/search/q={quote_plus(search_term)}&num=100",
            headers={
                "x-rapidapi-key": "30ed649aeamshbc757f7b0ab41c0p1bb1b2jsn33578965c40b",
                "x-rapidapi-host": "google-search3.p.rapidapi.com",
            },
        )
        data = conn.getresponse().read().decode("utf-8")
        json_data = json.loads(data)
        if "messages" in json_data:
            raise ValueError()
    except Exception:
        print("Error scrapping Google")
        return []

    final_search_results: List[GoogleResults] = [
        {"title": result["title"], "link": result["link"], "description": result["description"]}
        for result in json_data["results"]
    ]
    cache[search_term] = final_search_results
    return final_search_results


class TwitterSearch:
    def __init__(self):
        self.s = requests.Session()
        self.get_tokens()

    def get_tokens(self):
        s = self.s
        s.headers.update(
            {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
                "accept": "*/*",
                "accept-language": "de,en-US;q=0.7,en;q=0.3",
                "te": "trailers",
            }
        )

        # get guest_id cookie
        r = s.get("https://twitter.com")

        # get auth token
        main_js = s.get(
            "https://abs.twimg.com/responsive-web/client-web/main.e46e1035.js",
        ).text
        token = re.search(r"s=\"([\w\%]{104})\"", main_js)[1]
        s.headers.update({"authorization": f"Bearer {token}"})

        # activate token and get guest token
        guest_token = s.post("https://api.twitter.com/1.1/guest/activate.json").json()["guest_token"]
        s.headers.update({"x-guest-token": guest_token})

    def query(self, query, search_type) -> Dict[str, TwitterResults]:
        if f"{query}:{search_type}" in cache:
            return cache[f"{query}:{search_type}"]  # type: ignore
        param = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            "include_can_media_tag": "1",
            "skip_status": "1",
            "cards_platform": "Web-12",
            "include_cards": "1",
            "include_ext_alt_text": "true",
            "include_quote_count": "true",
            "include_reply_count": "1",
            "tweet_mode": "extended",
            "include_entities": "true",
            "include_user_entities": "true",
            "include_ext_media_color": "true",
            "include_ext_media_availability": "true",
            "send_error_codes": "true",
            "simple_quoted_tweet": "true",
            "q": query,
            "count": "30",
            "query_source": "typed_query",
            "pc": "1",
            "spelling_corrections": "1",
            "ext": "mediaStats,highlightedLabel",
        }
        if search_type == "users":
            param["result_filter"] = "user"

        res = self.s.get(
            url="https://twitter.com/i/api/2/search/adaptive.json",
            params=param,
        )
        if res.status_code == 200:
            final_search_results = res.json()["globalObjects"][search_type]
            cache[f"{query}:{search_type}"] = final_search_results
            return final_search_results
        else:
            return {}