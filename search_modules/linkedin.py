from typing import List
from utils.search import google_search, get_search_query, keywords_from_speciality, linkedin_search
from utils.types import *


class Linkedin:
    @staticmethod
    async def search(doc_name: str, speciality: str, max_terms: int = 10) -> List[ModuleResults]:
        doc_name = doc_name.lower()
        print(f"[Linkedin] Searching")

        search_hits: List[ModuleResults] = []

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
                result_content = (result["title"] + result["description"]).lower() + linkedin_profile.lower()
                matched_keywords = sum([keyword.lower() in result_content for keyword in keyword_set["keywords"]])
                confidence = round((matched_keywords / total_keywords) * 100, 2)
                if confidence > 0:
                    search_hits.append({"link": result["link"], "confidence": confidence})
        print("[Linkedin] Done")
        return sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]
