import json, requests
from time import sleep
from typing import List
from utils.search import google_search, get_search_query, keywords_from_speciality
from utils.types import *
from utils.cache import Cache
from utils.config import config

linkedin_cache = Cache("linkedin")


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[{thread_id}][Linkedin] Searching")

    search_hits: List[ModuleResult] = []

    keywords_sets = keywords_from_speciality(speciality)
    for keyword_set in keywords_sets:
        search_query = get_search_query(doc_name, "www.linkedin.com", keyword_set)
        search_results = google_search(search_query, "search")
        print(f"[{thread_id}][Linkedin] Google Search: {len(search_results)} result(s)")
        for result in search_results:
            if "pub/dir" in result["link"] or "linkedin.com/in/" not in result["link"]:
                continue
            total_keywords = len(keyword_set["keywords"])
            linkedin_profile = await linkedin_search(
                thread_id, result["link"].split("linkedin.com/in/")[1].split("?")[0].split("/")[0]
            )
            linkedin_profile_json = json.loads(linkedin_profile)
            clean_data(linkedin_profile_json)
            linkedin_profile = json.dumps(linkedin_profile_json)
            result_content = linkedin_profile.lower()
            matched_keywords = sum([keyword.lower() in result_content for keyword in keyword_set["keywords"]])
            confidence = round((matched_keywords / total_keywords) * 100, 2)
            if confidence > 0:
                search_hits.append({"link": result["link"], "confidence": confidence})
    print(f"[{thread_id}][Linkedin] Done")
    return {"source": "linkedin", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}


def clean_data(linkedin_profile_json):
    if "peopleAlsoViewed" in linkedin_profile_json:
        del linkedin_profile_json["peopleAlsoViewed"]
    if "people_also_viewed" in linkedin_profile_json:
        del linkedin_profile_json["people_also_viewed"]
    if "similarly_named_profiles" in linkedin_profile_json:
        del linkedin_profile_json["similarly_named_profiles"]


async def linkedin_search(thread_id: int, username: str) -> str:
    if f"linkedin:{username}" in linkedin_cache:
        return linkedin_cache[f"linkedin:{username}"]
    if config["DRY_RUN"]:
        return "{}"
    for tries in range(1, 11):
        print(f"[{thread_id}][Linkedin] Scraping [{username}] [{tries}]")
        header_dic = {"Authorization": "Bearer " + config["LINKEDIN_API_KEY"]}
        params = {
            "url": f"https://www.linkedin.com/in/{username}",
        }
        response = requests.get(f"{config['LINKEDIN_HOST']}/proxycurl/api/v2/linkedin", params=params, headers=header_dic)
        search_result = response.text
        if response.status_code not in [200, 404, 429]:
            raise RuntimeError(f"[Linkedin] Error Scraping [{response.status_code}] [{search_result}]")
        elif response.status_code == 429:
            print(f"[{thread_id}][Linkedin] Ratelimited! Waiting 60secs... [{tries}]")
            sleep(60)
        else:
            linkedin_cache[f"linkedin:{username}"] = search_result
            return search_result
    raise RuntimeError("[{thread_id}][Linkedin] Permanent Failure")
