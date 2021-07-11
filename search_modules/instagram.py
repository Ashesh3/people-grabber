from time import sleep

from requests.cookies import cookiejar_from_dict
from utils.image import put_image
import requests
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from utils.types import *
from utils.cache import cache
from utils.config import config

MAX_FACE_MATCH_POINTS = 3

insta_accs = config["INSTAGRAM_COOKIES"]
insta_index = 0


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 5) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[{thread_id}][Instagram] Searching")
    search_hits: List[ModuleResult] = []
    search_results = instagram_search(doc_name)[:max_terms]
    doc_image_urls = google_search(doc_name, "images", 1)
    doc_image = doc_image_urls[0]["link"] if doc_image_urls else ""
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
    if f"instagram_search:{name}:{max_terms}" in cache:
        return cache[f"instagram_search:{name}:{max_terms}"]
    if config["DRY_RUN"]:
        return []
    global insta_index
    tries = 0
    while tries < len(insta_accs):
        try:
            insta_index += 1
            insta_acc = insta_index % len(insta_accs)
            tries += 1
            api_results = requests.get(
                f"https://www.instagram.com/web/search/topsearch/?context=blended&query={name}&rank_token=0.09816429322112841&include_reel=false",
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "pragma": "no-cache",
                    "sec-ch-ua": '" Not;A Brand";v="99", "Microsoft Edge";v="91", "Chromium";v="91"',
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
                },
                cookies=cookiejar_from_dict(insta_accs[insta_acc]),
            ).json()
            results = []
            for item in api_results.get("users", [])[:max_terms]:
                profile_data = get_picture_bio(item["user"]["username"])
                results.append((item["user"]["username"], put_image(profile_data[0]), profile_data[1]))
            cache[f"instagram_search:{name}:{max_terms}"] = results
            return results
        except Exception:
            pass
    raise RuntimeError("[Instagram] Fatal Error Searching")


def get_picture_bio(username) -> Tuple[str, str]:
    print(f"[Instagram] Scraping {username}")
    bio = ""
    tries = 0
    global insta_index
    tries = 0
    while tries < len(insta_accs):
        try:
            insta_index += 1
            insta_acc = insta_index % len(insta_accs)
            tries += 1
            profile_info = requests.get(
                f"https://www.instagram.com/{username}/?__a=1",
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "pragma": "no-cache",
                    "sec-ch-ua": '" Not;A Brand";v="99", "Microsoft Edge";v="91", "Chromium";v="91"',
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
                },
                cookies=cookiejar_from_dict(insta_accs[insta_acc]),
            )
            if profile_info.status_code == 429:
                print("[Instagram] Rate Limit.. waiting 60s")
                sleep(60)
                continue
            bio = profile_info.json()["graphql"]["user"]["biography"]
            picture = profile_info.json()["graphql"]["user"]["profile_pic_url_hd"]
            return picture, bio
        except Exception:
            pass
    return ("", "")
