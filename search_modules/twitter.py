from typing import Any, Dict, List, Union
from utils.types import *
from utils.search import twitter_query
from utils.search import keywords_from_speciality


class Twitter:
    @staticmethod
    async def search(doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
        print(f"[Twitter] Searching")
        search_hits: List[ModuleResult] = []
        users: Dict[str, TwitterResults] = twitter_query(doc_name.title(), "users")  # type:ignore
        print(f"[Twitter] {len(users)} result(s)")
        for user_key in list(users.keys())[:10]:
            if doc_name.split(" ")[0].lower() not in users[user_key]["name"].lower():
                continue
            screen_name = users[user_key]["screen_name"]
            full_profile = users[user_key]["description"]
            full_profile += str(twitter_query(user_key, "likes"))
            all_keywords: List[str] = []
            for keyword_set in keywords_from_speciality(speciality):
                all_keywords.extend(keyword_set["keywords"])

            total_keywords = len(all_keywords)
            result_content = full_profile.lower()
            matched_keywords = sum([keyword.lower() in result_content for keyword in all_keywords])
            confidence = round((matched_keywords / total_keywords) * 100, 2)
            if confidence > 0:
                search_hits.append({"link": f"https://twitter.com/{screen_name}", "confidence": confidence})
        print("[Twitter] Done")
        return {"source": "twitter", "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms]}
