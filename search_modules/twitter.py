from typing import List
from .ISearch import SerchModule
from ..search import google_search, get_search_query, keywords_from_speciality


class Twitter(SerchModule):
    @staticmethod
    def search(doc_name: str, speciality: str) -> List[str]:
        doc_name = doc_name.lower()
        print(f"Searching: Twitter")

        search_results = []
        keywords_set = keywords_from_speciality(speciality)
        for keyword in keywords_set:
            search_query = get_search_query(doc_name, "www.twitter.com", keyword)
            search_results.extend(google_search(search_query))

        search_hits: List[str] = []
        for result in search_results:
            # Todo: Add Filtering Logic and append to search_hits
            # A single result object is in the form {"title": ..., "link": ..., "description": ...}
            # On match, append result.link to search_hits
            if ...:
                ...
                # search_hits.append(result.link)

        return search_hits