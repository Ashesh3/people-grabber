from instagram_private_api import Client
from utils.image import put_image
import requests
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from time import sleep
from utils.types import *
from utils.cache import Cache
from utils.config import config

instagram_cache = Cache("instagram")

api = Client(config["INSTAGRAM_CREDENTIALS"]["user_name"], config["INSTAGRAM_CREDENTIALS"]["password"])


MAX_FACE_MATCH_POINTS = 3


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 5) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[{thread_id}][Instagram] Searching")
    search_hits: List[ModuleResult] = []
    search_results = instagram_search(doc_name)[:max_terms]
    doc_image_urls = google_search(doc_name, "images", 1)
    doc_image = doc_image_urls[0]["link"]
    print(f"[{thread_id}][Instagram] People Search: {len(search_results)} result(s)")
    all_keywords: List[str] = []
    for keyword_set in keywords_from_speciality(speciality):
        all_keywords.extend(keyword_set["keywords"])
    for instagram_profile in search_results:
        total_keywords = len(all_keywords)
        face_match_points = 0
        result_content = instagram_profile[2].lower()
        if instagram_profile[1] and similar_image(doc_image, instagram_profile[1]):
            face_match_points = MAX_FACE_MATCH_POINTS
        print(f"[{thread_id}][Instagram] FACE MATCH: {face_match_points==MAX_FACE_MATCH_POINTS}")
        matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
        confidence = round(((matched_keywords + face_match_points) / (total_keywords + MAX_FACE_MATCH_POINTS)) * 100, 2)
        if confidence > 0:
            search_hits.append({"link": f"https://www.instagram.com/{instagram_profile[0]}", "confidence": confidence})
    print(f"[{thread_id}][Instagram] Done")
    return {"source": "instagram", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}


def instagram_search(name, max_terms=5) -> List[Tuple[str, str, str]]:
    if f"instagram_search:{name}:{max_terms}" in instagram_cache:
        return instagram_cache[f"instagram_search:{name}:{max_terms}"]
    if config["DRY_RUN"]:
        return []
    api_results = api.search_users(name)
    results = []
    for item in api_results.get("users", [])[:max_terms]:
        profile_data = get_picture_bio(item["username"])
        results.append((item["username"], put_image(profile_data[0]), profile_data[1]))
    instagram_cache[f"instagram_search:{name}:{max_terms}"] = results
    return results


def get_picture_bio(username) -> Tuple[str, str]:
    print(f"[Instagram] Scraping {username}")
    bio = ""
    try:
        tries = 0
        while tries < 10:
            profile_info = requests.get(f"https://www.instagram.com/{username}/?__a=1", cookies=api.cookie_jar)
            if profile_info.status_code == 429:
                sleep(60)
                tries += 1
                continue
            bio = profile_info.json()["graphql"]["user"]["biography"]
            picture = profile_info.json()["graphql"]["user"]["profile_pic_url_hd"]
            return picture, bio
    except Exception:
        pass
    return ("", "")
