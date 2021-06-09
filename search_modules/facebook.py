from typing import List
from utils.search import fb_people_search, keywords_from_speciality, facebook_search
from utils.types import *
import warnings

warnings.filterwarnings("ignore")


class Facebook:
    @staticmethod
    async def search(doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
        doc_name = doc_name.lower()
        print(f"[Facebook] Starting")
        search_hits: List[ModuleResult] = []
        search_results = fb_people_search(doc_name)
        print(f"[Facebook] People Search: {len(search_results)} result(s)")
        all_keywords: List[str] = []
        for keyword_set in keywords_from_speciality(speciality):
            all_keywords.extend(keyword_set["keywords"])
        for result in search_results:
            if any([x in result for x in ["/public", "/directory/", "/videos/", "/pages/"]]):
                continue
            total_keywords = len(all_keywords)
            facebook_profile = facebook_search(result)
            result_content = facebook_profile.lower()
            matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
            confidence = round((matched_keywords / total_keywords) * 100, 2)
            if confidence > 0:
                search_hits.append({"link": result, "confidence": confidence})
        print("[Facebook] Done")
        return {"source": "facebook", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}
