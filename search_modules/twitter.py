import requests
from typing import Dict, List, Union
from time import sleep
from utils.types import *
from utils.search import keywords_from_speciality
from utils.cache import cache
from utils.config import config

twitter_accs = config["TWITTER_COOKIES"]
twitter_index = 0


async def search(thread_id: int, doc_name: str, speciality: str, max_terms: int = 10) -> ModuleResults:
    print(f"[{thread_id}][Twitter] Searching")
    search_hits: List[ModuleResult] = []
    users: Dict[str, TwitterResults] = twitter_query(doc_name.title(), "users")  # type:ignore
    print(f"[{thread_id}][Twitter] {len(users)} result(s)")
    for user_key in list(users.keys())[:max_terms]:
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
        matched_keywords: List[str] = []
        for keyword in all_keywords:
            if keyword.lower() in result_content:
                matched_keywords.append(keyword)
        confidence = round((len(matched_keywords) / total_keywords) * 100, 2)
        if confidence > 0:
            search_hits.append(
                {
                    "link": f"https://twitter.com/{screen_name}",
                    "confidence": confidence,
                    "keywords": matched_keywords,
                }
            )
    print(f"[{thread_id}][Twitter] Done")
    return {
        "source": "twitter",
        "results": sorted(search_hits, key=lambda x: x["confidence"], reverse=True)[:max_terms],
    }


def get_twitter_likes(user_id: str):
    global twitter_index
    for tries in range(10):
        try:
            twitter_index += 1
            twitter_acc = twitter_index % len(twitter_accs)
            response = requests.get(
                "https://twitter.com/i/api/graphql/Ay8caIt8NEaf_ulIvhl4uQ/Likes",
                headers={
                    "Host": "twitter.com",
                    "X-Csrf-Token": twitter_accs[twitter_acc]["X_CSRF_TOKEN"],
                    "Authorization": f"Bearer {twitter_accs[twitter_acc]['AUTHORIZATION']}",
                    "Content-Type": "application/json",
                    "X-Twitter-Auth-Type": "OAuth2Session",
                    "X-Twitter-Active-User": "yes",
                    "Accept": "*/*",
                    "Referer": "https://twitter.com/BrentToderian/likes",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                params=(
                    (
                        "variables",
                        '{"userId":"'
                        + user_id
                        + '","count":100,"withHighlightedLabel":false,"withTweetQuoteCount":false,"includePromotedContent":false,"withTweetResult":true,"withReactions":false,"withSuperFollowsTweetFields":false,"withSuperFollowsUserFields":false,"withUserResults":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withBirdwatchPivots":false,"withVoice":false}',
                    ),
                ),
                cookies={
                    "auth_token": twitter_accs[twitter_acc]["AUTH_TOKEN"],
                    "ct0": twitter_accs[twitter_acc]["X_CSRF_TOKEN"],
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"Twitter Likes error {response.status_code} [Try {tries}]")
            return response.text
        except Exception:
            pass
    raise RuntimeError("[Twitter] Fatal Error Getting Likes")


def twitter_query(query, search_type) -> Union[str, Dict[str, TwitterResults]]:
    if f"{query}:{search_type}" in cache:
        return cache[f"{query}:{search_type}"]
    if config["DRY_RUN"]:
        return {}
    global twitter_index
    for _ in range(15):
        try:
            if search_type == "likes":
                query_result = get_twitter_likes(query)
                cache[f"{query}:{search_type}"] = query_result
                return query_result
            twitter_index += 1
            twitter_acc = twitter_index % len(twitter_accs)
            param = {
                "include_profile_interstitial_type": "1",
                "include_blocking": "1",
                "include_blocked_by": "1",
                "include_followed_by": "1",
                "include_want_retweets": "1",
                "include_mute_edge": "1",
                "include_can_dm": "1",
                "include_can_media_tag": "1",
                "skip_status": "1",
                "cards_platform": "Web-12",
                "include_cards": "1",
                "include_ext_alt_text": "true",
                "include_quote_count": "true",
                "include_reply_count": "1",
                "tweet_mode": "extended",
                "include_entities": "true",
                "include_user_entities": "true",
                "include_ext_media_color": "true",
                "include_ext_media_availability": "true",
                "send_error_codes": "true",
                "simple_quoted_tweet": "true",
                "q": query,
                "count": "30",
                "query_source": "typed_query",
                "pc": "1",
                "spelling_corrections": "1",
                "ext": "mediaStats,highlightedLabel",
            }
            if search_type == "users":
                param["result_filter"] = "user"

            res = requests.get(
                url="https://twitter.com/i/api/2/search/adaptive.json",
                params=param,
                cookies={
                    "auth_token": twitter_accs[twitter_acc]["AUTH_TOKEN"],
                    "ct0": twitter_accs[twitter_acc]["X_CSRF_TOKEN"],
                },
                headers={
                    "Host": "twitter.com",
                    "X-Csrf-Token": twitter_accs[twitter_acc]["X_CSRF_TOKEN"],
                    "Authorization": f"Bearer {twitter_accs[twitter_acc]['AUTHORIZATION']}",
                    "Content-Type": "application/json",
                    "X-Twitter-Auth-Type": "OAuth2Session",
                    "X-Twitter-Active-User": "yes",
                    "Accept": "*/*",
                    "Referer": "https://twitter.com/BrentToderian/likes",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            if res.status_code == 200:
                final_search_results = res.json()["globalObjects"][search_type]
                cache[f"{query}:{search_type}"] = final_search_results
                return final_search_results
            else:
                raise RuntimeError(f"Twitter Error {res.status_code} {res.text}")
        except Exception as e:
            print(f"Twitter Error: {e} Retrying")
            sleep(30)
    raise ValueError("Permanent Twitter Failure")
