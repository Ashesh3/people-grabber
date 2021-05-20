from typing import List
from utils.types import ModuleResults
from utils.search import TwitterSearch
from utils.search import keywords_from_speciality


class Twitter:
    @staticmethod
    def search(doc_name: str, speciality: str, max_terms: int = 10) -> List[ModuleResults]:
        print(f"Searching: Twitter")
        t_search = TwitterSearch()
        search_hits: List[ModuleResults] = []
        users = t_search.query(doc_name.title(), "users")

        for user_key in users:
            if doc_name.lower() not in users[user_key]["name"].lower():
                continue
            screen_name = users[user_key]["screen_name"]
            full_profile = users[user_key]["description"]
            tweets_result = t_search.query(f"from:{screen_name}", "tweets")
            for tweet_key in tweets_result:
                tweet_text = tweets_result[tweet_key]["full_text"]
                full_profile += "\n" + tweet_text

            all_keywords: List[str] = []
            for keyword_set in keywords_from_speciality(speciality):
                all_keywords.extend(keyword_set["keywords"])

            total_keywords = len(all_keywords)
            result_content = full_profile.lower()
            matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
            confidence = round((matched_keywords / total_keywords) * 100, 2)
            if confidence > 0:
                search_hits.append({"link": f"https://twitter.com/{screen_name}", "confidence": confidence})

        return sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]
