import http.client
import os
import json
import re
import requests
import shelve
import twitter
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *
from dotenv import load_dotenv
from linkedin_api import Linkedin
import asyncio


load_dotenv()
cache = shelve.open("cache", writeback=True)
linkedin_api = Linkedin(os.getenv("LINKEDIN_EMAIL"), os.getenv("LINKEDIN_PASS"))
twitter_api = twitter.Api(
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET_KEY"),
    access_token_key=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    sleep_on_rate_limit=True,
)
twitter_anon_session = requests.Session()


def refresh_twitter_anon_token():
    twitter_anon_session.headers.update(
        {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "accept": "*/*",
            "accept-language": "de,en-US;q=0.7,en;q=0.3",
            "te": "trailers",
        }
    )

    twitter_anon_session.get("https://twitter.com")

    main_js = twitter_anon_session.get(
        "https://abs.twimg.com/responsive-web/client-web/main.e46e1035.js",
    ).text
    token = re.search(r"s=\"([\w\%]{104})\"", main_js)[1]
    twitter_anon_session.headers.update({"authorization": f"Bearer {token}"})

    guest_token = twitter_anon_session.post("https://api.twitter.com/1.1/guest/activate.json").json()["guest_token"]
    twitter_anon_session.headers.update({"x-guest-token": guest_token})


refresh_twitter_anon_token()


async def linkedin_search(username: str) -> str:
    if f"linkedin:{username}" in cache:
        return cache[f"linkedin:{username}"]
    await asyncio.sleep(60)
    search_result = json.dumps(linkedin_api.get_profile_skills(username)) + json.dumps(linkedin_api.get_profile(username))
    cache[f"linkedin:{username}"] = search_result
    return search_result


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality == "Registered Nurse - Oncology":
        return [
            {"keywords": ["Registered Nurse", "Oncology"], "operator": "AND"},
            {"keywords": ["Nurse", "Oncology", " RN", "Cancer"], "operator": "OR"},
        ]
    if speciality in ["NEPHROLOGY", "PEDIATRIC NEPHROLOGY"]:
        return [
            {"keywords": ["nephrology", "nephrologist", "kidney", "renal", "nephro"], "operator": "OR"},
        ]
    # todo: add rest of keyword phases

    raise ValueError("Invalid Speciality")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return f'(intitle:"{doc_name}") site:{site} ' + '"' + f"\" {keyword['operator']} \"".join(keyword["keywords"]) + '"'


def google_search(search_term: str, max_terms: int = 5) -> List[GoogleResults]:
    if search_term in cache:
        return cache[search_term][:max_terms]
    conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
    conn.request(
        "GET",
        f"/api/v1/search/q={quote_plus(search_term)}&num=100",
        headers={
            "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", ""),
            "x-rapidapi-host": "google-search3.p.rapidapi.com",
        },
    )
    data = conn.getresponse().read().decode("utf-8")
    json_data = json.loads(data)
    if "messages" in json_data:
        raise ValueError("Error Scrapping Google.. ", json_data["messages"])

    final_search_results: List[GoogleResults] = [
        {"title": result["title"], "link": result["link"], "description": result["description"]}
        for result in json_data["results"]
    ]
    cache[search_term] = final_search_results
    return final_search_results[:max_terms]


async def twitter_query(query, search_type) -> Union[str, Dict[str, TwitterResults]]:
    if f"{query}:{search_type}" in cache:
        return cache[f"{query}:{search_type}"]
    if search_type == "likes":
        await asyncio.sleep(10)
        final_res = ""
        query_result = []
        try:
            query_result = twitter_api.GetFavorites(screen_name=query)
        except twitter.TwitterError as e:
            print(e)
        if query_result:
            final_res = json.dumps([res._json for res in query_result])
        cache[f"{query}:{search_type}"] = final_res
        return final_res
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

    res = twitter_anon_session.get(
        url="https://twitter.com/i/api/2/search/adaptive.json",
        params=param,
    )
    if res.status_code == 200:
        final_search_results = res.json()["globalObjects"][search_type]
        cache[f"{query}:{search_type}"] = final_search_results
        return final_search_results
    else:
        return {}
