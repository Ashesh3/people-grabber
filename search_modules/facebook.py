import warnings, requests
from typing import List
from utils.search import keywords_from_speciality, google_search
from time import sleep
from utils.types import *
from utils.cache import Cache
from utils.config import config
from bs4 import BeautifulSoup

facebook_cache = Cache("facebook")
warnings.filterwarnings("ignore")
facebook_accs = config["FACEBOOK_COOKIES"]
facebook_index = 0


async def search(doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[Facebook] Searching")
    search_hits: List[ModuleResult] = []
    search_results = fb_people_search(doc_name)
    doc_image = google_search(doc_name, "images", 1)
    print(f"[Facebook] People Search: {len(search_results)} result(s)")
    all_keywords: List[str] = []
    for keyword_set in keywords_from_speciality(speciality):
        all_keywords.extend(keyword_set["keywords"])
    for result in search_results:
        if any([x in result for x in ["/public", "/directory/", "/videos/", "/pages/"]]):
            continue
        total_keywords = len(all_keywords)
        facebook_profile = get_profile(result)
        result_content = facebook_profile.lower()
        matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
        confidence = round((matched_keywords / total_keywords) * 100, 2)
        if confidence > 0:
            search_hits.append({"link": result, "confidence": confidence})
    print("[Facebook] Done")
    return {"source": "facebook", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}


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


def get_profile(fb_link: str):
    fb_id = get_facebook_username(fb_link)
    if f"facebook:{fb_id}" in facebook_cache:
        return facebook_cache[f"facebook:{fb_id}"]
    if config["DRY_RUN"]:
        return ""
    sleep(10)
    global facebook_index
    facebook_index += 1
    fb_acc = facebook_index % len(facebook_accs)
    try:
        print(f"[Facebook] [{fb_acc+1}] Scraping [{fb_id}]")
        acc_resp = requests.get(
            fb_link,
            headers=get_facebook_headers(
                "mbasic.facebook.com",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            ),
            cookies=facebook_accs[fb_acc],
        ).text
        if any([x in acc_resp for x in ["use this feature at the moment", "temporarily blocked"]]):
            print(f"[Facebook Banned] [{fb_acc+1}] [Sleep 600]")
            sleep(600)
            raise RuntimeError("[ERROR] Facebook banned")
        soup = BeautifulSoup(acc_resp, "html.parser")
        image_url = "https://mbasic.facebook.com/" + soup.select("#root")[0].findAll(
            "a", id=lambda x: x and x.startswith("u_0_3_")
        )[0].get("href")
        facebook_cache[f"facebook:{fb_id}"] = acc_resp
        return acc_resp
    except Exception as e:
        print(f"[Facebook] [{fb_acc}] [{fb_id}] [{e}]")
    return ""


def get_facebook_username(fb_link):
    prefix = "/"
    if "/people/" in fb_link:
        prefix = "/people/"
    return fb_link.split(f".com{prefix}")[1].split("/")[0].split("?")[0]


def facebook_legacy_search(fb_link: str):
    acc_data = requests.get(
        fb_link,
        headers=get_facebook_headers(
            "www.facebook.com",
            "NokiaC3-00/5.0 (07.20) Profile/MIDP-2.1 Configuration/CLDC-1.1 Mozilla/5.0 AppleWebKit/420+ (KHTML, like Gecko) Safari/420+",
        ),
    ).text
    return acc_data


def fb_people_search(name):
    if f"facebook_people:{name}" in facebook_cache:
        return facebook_cache[f"facebook_people:{name}"]
    if config["DRY_RUN"]:
        return []
    sleep(30)
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
        if len(results[i].select("img")) > 0 and results[i].get("href") and "add_friend" not in results[i].get("href")
    ]
    facebook_cache[f"facebook_people:{name}"] = pages
    return pages
