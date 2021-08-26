from utils.image import put_image
from os import path
from shutil import rmtree
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from utils.types import *
from utils.cache import cache, account_cache
from utils.config import config
from utils.drive import get_file
from igramscraper.instagram import Instagram

MAX_FACE_MATCH_POINTS = 3

instagram_accs_sheet = get_file(config["INSTAGRAM_ACCOUNT_FILE"]["id"], config["INSTAGRAM_ACCOUNT_FILE"]["sheet"])
instagram_accs_data = instagram_accs_sheet.get_all_values()[1:]
instagram_accs = []

for index, acc in enumerate(instagram_accs_data):
    if acc[3] == "Active" and f"instagram_login:{acc[0]}:{acc[1]}" in account_cache:
        instagram_accs.append(account_cache[f"instagram_login:{acc[0]}:{acc[1]}"])
        continue
    if acc[3] in ["Active", ""]:
        instagram = Instagram()
        try:
            instagram.with_credentials(acc[0], acc[1])
            instagram.login(True)
        except Exception as e:
            print(f"[instagram] Login Error -> {acc[0]} : {e}")
            instagram_accs_sheet.update(f"D{index+2}", "Account Disabled")
            instagram_accs_sheet.format(
                f"D{index+2}",
                {"textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0}}},
            )
            continue
        instagram_accs.append([f"D{index+2}", instagram.user_session])
        instagram_accs_sheet.update(f"D{index+2}", "Active")
        instagram_accs_sheet.format(
            f"D{index+2}",
            {"textFormat": {"bold": True, "foregroundColor": {"red": 0.2039, "green": 0.6588, "blue": 0.3254}}},
        )
        account_cache[f"instagram_login:{acc[0]}:{acc[1]}"] = [f"D{index+2}", instagram.user_session]

if path.exists("./sessions"):
    rmtree("./sessions")

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
    while tries < len(instagram_accs):
        insta_index += 1
        insta_acc = insta_index % len(instagram_accs)
        tries += 1
        try:
            instagram_instance = Instagram()
            instagram_instance.user_session = instagram_accs[insta_acc][1]
            api_results = instagram_instance.search_accounts_by_username(name)
            results = []
            for acc in api_results[:max_terms]:
                profile_data = get_picture_bio(acc.username)
                results.append((acc.username, put_image(profile_data[0]), profile_data[1]))
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
    while tries < len(instagram_accs):
        insta_index += 1
        insta_acc = insta_index % len(instagram_accs)
        tries += 1
        try:
            instagram_instance = Instagram()
            instagram_instance.user_session = instagram_accs[insta_acc][1]
            profile_info = instagram_instance.get_account(username)
            bio = profile_info.biography
            picture = profile_info.get_profile_picture_url()
            cache[f"instagram_details:{username}"] = (str(picture), bio or "")
            return (str(picture), bio or "")
        except Exception:
            pass
    return ("", "")
