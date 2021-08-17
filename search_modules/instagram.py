from utils.image import put_image
import requests
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from utils.types import *
from utils.cache import cache
from utils.config import config

MAX_FACE_MATCH_POINTS = 3

insta_accs = config["INSTAGRAM_API_KEYS"]
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
        confidence = round(
            ((matched_keywords + face_match_points) / (total_keywords + MAX_FACE_MATCH_POINTS)) * 100, 2
        )
        if confidence > 0:
            search_hits.append(
                {"link": f"https://www.instagram.com/{instagram_profile[0]}", "confidence": confidence}
            )
    print(f"[{thread_id}][Instagram] Done")
    return {
        "source": "instagram",
        "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms],
    }


def instagram_search(name, max_terms=5) -> List[Tuple[str, str, str]]:
    if f"instagram_search:{name}" in cache:
        return cache[f"instagram_search:{name}"][:max_terms]
    if config["DRY_RUN"]:
        return []
    global insta_index
    tries = 0
    while tries < len(insta_accs):
        try:
            insta_index += 1
            insta_acc = insta_index % len(insta_accs)
            tries += 1
            api_results = requests.request(
                "GET",
                "https://instagram47.p.rapidapi.com/search",
                headers={
                    "x-rapidapi-key": insta_accs[insta_acc],
                    "x-rapidapi-host": "instagram47.p.rapidapi.com",
                },
                params={"search": name.replace(" ", "%20", 1).replace("-", "").split(" ")[0]},
            ).json()
            if api_results["statusCode"] in [204, 202]:
                cache[f"instagram_search:{name}"] = []
                return []
            api_results = api_results["body"]
            results = []
            for item in api_results.get("users", [])[:max_terms]:
                profile_data = get_picture_bio(item["user"]["pk"])
                results.append((item["user"]["username"], put_image(profile_data[0]), profile_data[1]))
            cache[f"instagram_search:{name}"] = results
            return results
        except Exception as e:
            print("[Instagram] Search Error: ", e)
    raise RuntimeError("[Instagram] Fatal Error Searching")


def get_picture_bio(username) -> Tuple[str, str]:
    print(f"[Instagram] Scraping {username}")
    if f"instagram_details:{username}" in cache:
        return cache[f"instagram_details:{username}"]
    bio = ""
    tries = 0
    global insta_index
    while tries < len(insta_accs):
        try:
            insta_index += 1
            insta_acc = insta_index % len(insta_accs)
            tries += 1
            profile_info = requests.request(
                "GET",
                "https://instagram47.p.rapidapi.com/email_and_details",
                headers={
                    "x-rapidapi-key": insta_accs[insta_acc],
                    "x-rapidapi-host": "instagram47.p.rapidapi.com",
                },
                params={"userid": username},
            ).json()["body"]
            bio = profile_info["biography"]
            picture = profile_info["hd_profile_pic_versions"][-1]["url"]
            cache[f"instagram_details:{username}"] = (picture, bio)
            return (picture, bio)
        except Exception:
            pass
    return ("", "")
