from typing import List
from utils.search import google_search, get_search_query, keywords_from_speciality, linkedin_search
from utils.types import *
import json


class Linkedin:
    @staticmethod
    async def search(doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
        doc_name = doc_name.lower()
        print(f"[Linkedin] Searching")

        search_hits: List[ModuleResult] = []

        keywords_sets = keywords_from_speciality(speciality)
        for keyword_set in keywords_sets:
            search_query = get_search_query(doc_name, "www.linkedin.com", keyword_set)
            search_results = google_search(search_query)
            print(f"[Linkedin] Google Search: {len(search_results)} result(s)")
            for result in search_results:
                if "pub/dir" in result["link"] or "linkedin.com/in/" not in result["link"]:
                    continue
                total_keywords = len(keyword_set["keywords"])
                linkedin_profile = await linkedin_search(result["link"].split("linkedin.com/in/")[1].split("?")[0].split("/")[0])
                linkedin_profile_json = json.loads(linkedin_profile)
                if "people_also_viewed" in linkedin_profile:
                    del linkedin_profile_json["people_also_viewed"]
                if "similarly_named_profiles" in linkedin_profile:
                    del linkedin_profile_json["similarly_named_profiles"]
                linkedin_profile = json.dumps(linkedin_profile_json)
                result_content = linkedin_profile.lower()
                matched_keywords = sum([keyword.lower() in result_content for keyword in keyword_set["keywords"]])
                confidence = round((matched_keywords / total_keywords) * 100, 2)
                if confidence > 0:
                    search_hits.append({"link": result["link"], "confidence": confidence})
        print("[Linkedin] Done")
        return {"source": "linkedin", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}
