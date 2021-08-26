from typing import Dict
from utils.search import keywords_from_speciality
from utils.types import *
from utils.cache import cache
from utils.config import config
import requests
from utils.drive import get_file

google_api_sheet = get_file(config["GOOGLE_API_FILE"]["id"], config["GOOGLE_API_FILE"]["sheet"])
google_api_data = google_api_sheet.get_all_values()[1:]
google_api_keys = [
    [f"B{i+2}", key[0]] for i, key in enumerate(google_api_data) if "suspended" not in key[1].lower()
]
google_api_index = 0


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 5) -> ModuleResults:
    doc_name = doc_name.lower()
    print(f"[{thread_id}][Youtube] Searching")
    search_hits: List[ModuleResult] = []
    search_results = youtube_search(doc_name)[:max_terms]
    print(f"[{thread_id}][Youtube] Channel Search: {len(search_results)} result(s)")
    all_keywords: List[str] = []
    for keyword_set in keywords_from_speciality(speciality):
        all_keywords.extend(keyword_set["keywords"])
    for result in search_results:
        total_keywords = len(all_keywords)
        result_content = result["content"].lower()
        matched_keywords = []
        for keyword in all_keywords:
            if keyword.lower() in result_content:
                matched_keywords.append(keyword)
        confidence = round(((len(matched_keywords)) / (total_keywords)) * 100, 2)
        if confidence > 0:
            search_hits.append(
                {
                    "link": f"https://www.youtube.com/channel/{result['channelID']}",
                    "confidence": confidence,
                    "keywords": matched_keywords,
                }
            )
    print(f"[{thread_id}][Youtube] Done")
    return {
        "source": "youtube",
        "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms],
    }


def youtube_search(search_term: str) -> List[Dict[str, str]]:
    if f"youtube_search:{search_term}" in cache:
        return cache[f"youtube_search:{search_term}"]
    if config["DRY_RUN"]:
        return []
    global google_api_index
    err_count = 0
    json_data = {}
    while err_count < len(google_api_keys):
        try:
            res = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "type": "channel",
                    "key": google_api_keys[google_api_index % len(google_api_keys)][1],
                    "q": search_term,
                },
            )
            json_data = res.json()
            if "error" in json_data:
                raise ValueError("Error Scrapping Youtube.. ", json_data["error"]["message"])
            if "items" not in json_data:
                json_data["items"] = []

            final_youtube_results = [
                {
                    "channelID": x["id"]["channelId"],
                    "content": x["snippet"]["title"].lower() + x["snippet"]["description"].lower(),
                }
                for x in json_data["items"]
            ]
            cache[f"youtube_search:{search_term}"] = final_youtube_results
            return final_youtube_results
        except Exception as e:
            google_api_index += 1
            print(
                f"YoutubeAPI Switching key... {google_api_index % len(google_api_keys)} [{e.__class__}: {e}] [{json_data}]"
            )
            if "suspended" in str(e).lower():
                google_api_sheet.update(google_api_keys[google_api_index][0], "Key Suspended")
                google_api_sheet.format(
                    google_api_keys[google_api_index][0],
                    {
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 0, "blue": 0},
                        }
                    },
                )
            err_count += 1
    raise ValueError("Error in YoutubeAPI..")
