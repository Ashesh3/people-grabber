import http.client, os, json, re, requests, asyncio, zlib, pickle, sqlite3
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *
from dotenv import load_dotenv
from linkedin_api import Linkedin
from sqlitedict import SqliteDict
from requests.cookies import cookiejar_from_dict


load_dotenv()

cache = SqliteDict(
    "./cache.sqlite",
    encode=lambda obj: sqlite3.Binary(zlib.compress(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL), 9)),
    decode=lambda obj: pickle.loads(zlib.decompress(bytes(obj))),
    autocommit=True,
)

linkedin_emails = os.getenv("LINKEDIN_EMAILS", "").split(",")
linkedin_jsess = os.getenv("LINKEDIN_JSESSIONID", "").split(",")
linkedin_li_at = os.getenv("LINKEDIN_LI_AT", "").split(",")
linkedin_apis = []
for l_email, l_jsess, l_li_at in zip(linkedin_emails, linkedin_jsess, linkedin_li_at):
    print(f"Loading LinkedinID: {l_email}")
    linkedin_apis.append(
        Linkedin(
            "",
            "",
            cookies=cookiejar_from_dict(
                {
                    "liap": "true",
                    "JSESSIONID": l_jsess,
                    "li_at": l_li_at,
                }
            ),
        )
    )
    print("Loaded:", linkedin_apis[-1].get_user_profile()["miniProfile"]["firstName"])

twitter_anon_session = requests.Session()

rapid_api_keys = os.getenv("RAPIDAPI_KEY", "").split(",")
rapid_api_index = linkedin_api_index = 0


def refresh_twitter_anon_token():
    twitter_anon_session.headers.update(
        {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "accept": "*/*",
            "accept-language": "de,en-US;q=0.7,en;q=0.3",
            "te": "trailers",
        }
    )

    twitter_anon_session.get("https://twitter.com")

    main_js = twitter_anon_session.get(
        "https://abs.twimg.com/responsive-web/client-web/main.e46e1035.js",
    ).text
    token = re.search(r"s=\"([\w\%]{104})\"", main_js)[1]
    twitter_anon_session.headers.update({"authorization": f"Bearer {token}"})

    guest_token = twitter_anon_session.post("https://api.twitter.com/1.1/guest/activate.json").json()["guest_token"]
    twitter_anon_session.headers.update({"x-guest-token": guest_token})


refresh_twitter_anon_token()


async def linkedin_search(username: str) -> str:
    if f"linkedin:{username}" in cache:
        return cache[f"linkedin:{username}"]
    global linkedin_api_index
    err_count = 0
    while err_count < len(linkedin_apis):
        try:
            linkedin_api_index += 1
            linkedin_client = linkedin_apis[linkedin_api_index % len(linkedin_apis)]
            await asyncio.sleep(60)
            search_result = json.dumps(linkedin_client.get_profile_skills(username)) + json.dumps(
                linkedin_client.get_profile(username)
            )
            cache[f"linkedin:{username}"] = search_result
            return search_result
        except Exception:
            print(f"Linkedin Switching Acc to {((linkedin_api_index+1) % len(linkedin_apis))+1} ...")
            err_count += 1
    raise ValueError("Error in Linkedin..")


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality == "Registered Nurse - Oncology":
        return [
            {"keywords": ["Registered Nurse", "Oncology"], "operator": "AND"},
            {"keywords": ["Nurse", "Oncology", " RN", "Cancer"], "operator": "OR"},
        ]
    if speciality in ["NEPHROLOGY", "PEDIATRIC NEPHROLOGY"]:
        return [
            {"keywords": ["nephrology", "nephrologist", "kidney", "renal", "nephro"], "operator": "OR"},
        ]
    # todo: add rest of keyword phases

    raise ValueError("Invalid Speciality")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return f'(intitle:"{doc_name}") site:{site} ' + '"' + f"\" {keyword['operator']} \"".join(keyword["keywords"]) + '"'


def google_search(search_term: str, max_terms: int = 5) -> List[GoogleResults]:
    if search_term in cache:
        return cache[search_term][:max_terms]

    global rapid_api_index
    err_count = 0
    while err_count < len(rapid_api_keys):
        try:
            conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
            conn.request(
                "GET",
                f"/api/v1/search/q={quote_plus(search_term)}&num=100",
                headers={
                    "x-rapidapi-key": rapid_api_keys[rapid_api_index % len(rapid_api_keys)],
                    "x-rapidapi-host": "google-search3.p.rapidapi.com",
                },
            )
            data = conn.getresponse().read().decode("utf-8")
            json_data = json.loads(data)
            if "messages" in json_data:
                raise ValueError("Error Scrapping Google.. ", json_data["messages"])
            final_search_results: List[GoogleResults] = [
                {"title": result["title"], "link": result["link"], "description": result["description"]}
                for result in json_data["results"]
            ]
            cache[search_term] = final_search_results
            return final_search_results[:max_terms]
        except Exception:
            rapid_api_index += 1
            print(f"RapidApi Switching key... {rapid_api_index % len(rapid_api_keys)}")
            err_count += 1
    raise ValueError("Error in RapidAPI..")


def get_twitter_likes(user_id: str):
    response = requests.get(
        "https://twitter.com/i/api/graphql/OU4zjDOFfM9ZHq2aTjUNCA/Likes",
        headers={
            "Host": "twitter.com",
            "X-Csrf-Token": os.getenv("TWITTER_X_CSRF_TOKEN", ""),
            "Authorization": f"Bearer {os.getenv('TWITTER_AUTHORIZATION', '')}",
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
                + '","count":20,"withHighlightedLabel":false,"withTweetQuoteCount":false,"includePromotedContent":false,"withTweetResult":false,"withReactions":false,"withUserResults":false,"withClientEventToken":false,"withBirdwatchNotes":false,"withBirdwatchPivots":false,"withVoice":false,"withNonLegacyCard":true}',
            ),
        ),
        cookies={
            "auth_token": os.getenv("TWITTER_AUTH_TOKEN", ""),
            "ct0": os.getenv("TWITTER_CT0", ""),
        },
    )
    return response.text


def twitter_query(query, search_type) -> Union[str, Dict[str, TwitterResults]]:
    if f"{query}:{search_type}" in cache:
        return cache[f"{query}:{search_type}"]
    if search_type == "likes":
        query_result = get_twitter_likes(query)
        cache[f"{query}:{search_type}"] = query_result
        return query_result
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

    res = twitter_anon_session.get(
        url="https://twitter.com/i/api/2/search/adaptive.json",
        params=param,
    )
    if res.status_code == 200:
        final_search_results = res.json()["globalObjects"][search_type]
        cache[f"{query}:{search_type}"] = final_search_results
        return final_search_results
    else:
        return {}
