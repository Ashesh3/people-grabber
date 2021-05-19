from typing import List
from .ISearch import SerchModule
from ..search import google_search, get_search_query


class Twitter(SerchModule):
    @staticmethod
    def search(doc_name: str, keywords: List[str]):
        doc_name = doc_name.lower()
        print(f"Searching: Twitter")

        search_query = get_search_query(doc_name, "www.twitter.com", keywords)
        results = google_search(search_query)

        search_hits = []

        for result in results:
            # Todo: Add Filtering Logic and append to search_hits
            # A single result object is in the form {"title": ..., "link": ..., "description": ...}
            # On match, append result.link to search_hits
            if ...:
                search_hits.append(...)

        return search_hits