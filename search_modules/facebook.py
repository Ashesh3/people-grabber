from utils.image import put_image
import warnings, requests, json
from requests.cookies import cookiejar_from_dict
from typing import List, Tuple
from utils.search import keywords_from_speciality, google_search, similar_image
from time import sleep
from utils.types import *
from utils.cache import cache
from utils.config import config
from bs4 import BeautifulSoup
import requests
import facebook_scraper
from facebook_scraper.exceptions import TemporarilyBanned

warnings.filterwarnings("ignore")
facebook_accs = config["FACEBOOK_COOKIES"]
facebook_index = 0
MAX_FACE_MATCH_POINTS = 3


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 5) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[{thread_id}][Facebook] Searching")
    search_hits: List[ModuleResult] = []
    search_results = fb_people_search(doc_name)[:max_terms]
    doc_image_urls = google_search(doc_name, "images", 1)
    doc_image = doc_image_urls[0]["link"] if doc_image_urls else ""
    print(f"[{thread_id}][Facebook] People Search: {len(search_results)} result(s)")
    all_keywords: List[str] = []
    for keyword_set in keywords_from_speciality(speciality):
        all_keywords.extend(keyword_set["keywords"])
    for result in search_results:
        if any([x in result for x in ["/public", "/directory/", "/videos/", "/pages/"]]):
            continue
        total_keywords = len(all_keywords)
        facebook_profile = get_profile(thread_id, result)
        result_content = facebook_profile[0].lower()
        face_match_points = 0
        if facebook_profile[1]:
            if similar_image(doc_image, facebook_profile[1]):
                face_match_points = MAX_FACE_MATCH_POINTS
            print(f"[{thread_id}][Facebook] FACE MATCH: {face_match_points==MAX_FACE_MATCH_POINTS}")
        matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
        confidence = round(
            ((matched_keywords + face_match_points) / (total_keywords + MAX_FACE_MATCH_POINTS)) * 100, 2
        )
        if confidence > 0:
            search_hits.append({"link": result, "confidence": confidence})
    print(f"[{thread_id}][Facebook] Done")
    return {
        "source": "facebook",
        "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms],
    }


def get_facebook_headers(host, useragent):
    return {
        "Host": host,
        "Sec-Ch-Ua": '\\" Not A;Brand\\";v=\\"99\\", \\"Chromium\\";v=\\"90\\"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": useragent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en-US,en;q=0.9",
    }


def get_profile(thread_id: int, fb_link: str) -> Tuple[str, str]:
    fb_link = fb_link.replace("https://facebook.com", "https://mbasic.facebook.com")
    global facebook_index
    fb_id = get_facebook_username(fb_link)
    if f"facebook:{fb_id}" in cache:
        return cache[f"facebook:{fb_id}"]
    if config["DRY_RUN"]:
        return ("", "")
    acc_data = ("", "")
    for tries in range(10):
        try:
            facebook_index += 1
            fb_acc = facebook_index % len(facebook_accs)
            try:
                scrap_data = facebook_scraper.get_profile(
                    fb_id, cookies=cookiejar_from_dict(facebook_accs[fb_acc])
                )
                print(f"[{thread_id}][Facebook] [{fb_acc+1}] Scraping [{fb_id}]")
                acc_pic = json.loads(json.dumps(scrap_data)).get("profile_picture", "")
                acc_data = (json.dumps(scrap_data), put_image(acc_pic))
                cache[f"facebook:{fb_id}"] = acc_data
            except TemporarilyBanned as e:
                sleep(1 * 60)
                print(f"[{thread_id}][{facebook_index}][Facebook] Temporarily Banned [Try {tries}]")
            except Exception as e:
                print(f"[Facebook] [{fb_acc}] [{fb_id}] [{e}]")
                cache[f"facebook:{fb_id}"] = acc_data
            return acc_data
        except Exception:
            pass
    raise RuntimeError("[Facebook] Fatal Error Scraping Profile")


def get_facebook_username(fb_link):
    if "profile.php" in fb_link:
        return "profile.php" + fb_link.split("/profile.php")[1]
    prefix = "/"
    if "/people/" in fb_link:
        prefix = "/people/"
    return fb_link.split(f".com{prefix}")[1].split("/")[0].split("?")[0]


def fb_people_search(name):
    if f"facebook_people:{name}" in cache:
        return cache[f"facebook_people:{name}"]
    if config["DRY_RUN"]:
        return []
    sleep(10)
    global facebook_index
    facebook_index += 1
    fb_acc = facebook_index % len(facebook_accs)
    response = requests.get(
        "https://mbasic.facebook.com/search/people/",
        headers=get_facebook_headers(
            "mbasic.facebook.com",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        ),
        params=(
            ("q", name),
            ("source", "filter"),
            ("isTrending", "0"),
        ),
        cookies=facebook_accs[fb_acc],
    )
    soup = BeautifulSoup(response.content, "html.parser")
    if not soup.select("#BrowseResultsContainer"):
        return []
    results = soup.select("#BrowseResultsContainer")[0].select("table a")
    pages = [
        f"https://facebook.com{results[i].get('href').split('refid')[0]}"
        for i in range(len(results))
        if len(results[i].select("img")) > 0
        and results[i].get("href")
        and "add_friend" not in results[i].get("href")
    ]
    cache[f"facebook_people:{name}"] = pages
    return pages
