from typing import List
from utils.search import google_search, get_search_query, keywords_from_speciality
from utils.types import *


class Linkedin:
    @staticmethod
    def search(doc_name: str, speciality: str) -> List[ModuleResults]:
        doc_name = doc_name.lower()
        print(f"Searching: Linkedin")

        search_hits: List[ModuleResults] = []

        keywords_sets = keywords_from_speciality(speciality)
        for keyword_set in keywords_sets:
            search_query = get_search_query(doc_name, "www.linkedin.com", keyword_set)
            search_results = google_search(search_query)

            for result in search_results:
                total_keywords = len(keyword_set["keywords"])
                result_content = result["title"] + result["description"]
                matched_keywords = sum([keyword in result_content for keyword in keyword_set["keywords"]])
                confidence = round((matched_keywords / total_keywords) * 100, 2)
                search_hits.append({"link": result["link"], "confidence": confidence})

        return sorted(search_hits, key=lambda x: x["confidence"], reverse=True)
