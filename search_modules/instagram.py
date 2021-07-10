from instagram_private_api import Client
from utils.image import put_image
import requests, os, json, codecs
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from time import sleep
from utils.types import *
from utils.cache import cache
from utils.config import config


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {"__class__": "bytes", "__value__": codecs.encode(python_object, "base64").decode()}
    raise TypeError(repr(python_object) + " is not JSON serializable")


def from_json(json_object):
    if "__class__" in json_object and json_object["__class__"] == "bytes":
        return codecs.decode(json_object["__value__"].encode(), "base64")
    return json_object


def onlogin_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, "w") as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print("SAVED: {0!s}".format(new_settings_file))


settings_file = "cache_insta_cookies.json"
if not os.path.isfile(settings_file):
    print("Unable to find file: {0!s}".format(settings_file))

    api = Client(
        config["INSTAGRAM_CREDENTIALS"]["user_name"],
        config["INSTAGRAM_CREDENTIALS"]["password"],
        on_login=lambda x: onlogin_callback(x, "cache_insta_cookies.json"),
    )
else:
    with open(settings_file) as file_data:
        cached_settings = json.load(file_data, object_hook=from_json)
    print("Reusing settings: {0!s}".format(settings_file))

    device_id = cached_settings.get("device_id")
    api = Client(
        config["INSTAGRAM_CREDENTIALS"]["user_name"], config["INSTAGRAM_CREDENTIALS"]["password"], settings=cached_settings
    )


MAX_FACE_MATCH_POINTS = 3


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
    tries = 0
    while tries < 10:
        try:
            tries += 1
            api_results = requests.get(
                f"https://www.instagram.com/web/search/topsearch/?context=blended&query={name}&rank_token=0.09816429322112841&include_reel=false",
                cookies=api.cookie_jar,
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
    try:
        while tries < 10:
            tries += 1
            profile_info = requests.get(f"https://www.instagram.com/{username}/?__a=1", cookies=api.cookie_jar)
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
