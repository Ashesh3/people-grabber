from typing import List
from utils.search import google_search, get_search_query, keywords_from_speciality, facebook_search, get_facebook_username
from utils.types import *
import warnings

warnings.filterwarnings("ignore")


class Facebook:
    @staticmethod
    async def search(doc_name: str, speciality: str, max_terms: int = 10) -> List[ModuleResults]:
        doc_name = doc_name.lower()
        print(f"[Facebook] Starting")
        search_hits: List[ModuleResults] = []
        search_query = get_search_query(doc_name, "www.facebook.com", {"keywords": [], "operator": ""})
        search_results = google_search(search_query)
        print(f"[Facebook] Google Search: {len(search_results)} result(s)")
        all_keywords: List[str] = []
        for keyword_set in keywords_from_speciality(speciality):
            all_keywords.extend(keyword_set["keywords"])
        for result in search_results:
            if any([x in result["link"] for x in ["/public", "/directory/", "/videos/", "/pages/"]]):
                continue
            total_keywords = len(all_keywords)
            facebook_profile = facebook_search(get_facebook_username(result["link"]))
            result_content = (result["title"] + result["description"]).lower() + facebook_profile.lower()
            matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
            confidence = round((matched_keywords / total_keywords) * 100, 2)
            if confidence > 0:
                search_hits.append({"link": result["link"], "confidence": confidence})
        print("[Facebook] Done")
        return sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]
