import http.client, json, re, requests, zlib, pickle, sqlite3
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *
from dotenv import load_dotenv
from sqlitedict import SqliteDict
from requests.cookies import cookiejar_from_dict
from utils.config import config
from facebook_scraper import get_profile, get_posts
from facebook_scraper.exceptions import TemporarilyBanned

load_dotenv()

cache = SqliteDict(
    config["CACHE_PATH"],
    encode=lambda obj: sqlite3.Binary(zlib.compress(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL), 9)),
    decode=lambda obj: pickle.loads(zlib.decompress(bytes(obj))),
    autocommit=True,
)

if "Twitter" in config["SEARCH_MODULES"]:
    twitter_anon_session = requests.Session()

rapid_api_keys = config["RAPIDAPI_KEYS"]
rapid_api_index, facebook_index = 0, 0

facebook_accs = config["FACEBOOK_COOKIES"]


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


if "Twitter" in config["SEARCH_MODULES"]:
    refresh_twitter_anon_token()


async def linkedin_search(username: str) -> str:
    if f"linkedin:{username}" in cache:
        return cache[f"linkedin:{username}"]

    print(f"[Linkedin] Scraping [{username}]")
    header_dic = {"Authorization": "Bearer " + config["LINKEDIN_API_KEY"]}
    params = {
        "url": f"https://www.linkedin.com/in/{username}",
    }
    response = requests.get("https://nubela.co/proxycurl/api/v2/linkedin", params=params, headers=header_dic)
    search_result = response.text
    if response.status_code not in [200, 404]:
        raise RuntimeError(f"[Linkedin] Error Scraping [{response.status_code}] [{search_result}]")
    cache[f"linkedin:{username}"] = search_result
    return search_result


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    if speciality == "Registered Nurse - Oncology":
        return [
            {"keywords": ["Registered Nurse", "Nurse", "Oncology", " RN", "Cancer"], "operator": "OR"},
        ]
    if speciality == "Pharmacist - Oncology":
        return [
            {"keywords": ["Pharmacist", "Oncology", " Pharmacy", "Cancer"], "operator": "OR"},
        ]
    if speciality == "Internal Medicine - Hematology & Oncology":
        return [
            {
                "keywords": ["Internal Medicine", "Hematology", " Hematologist", "Oncologist", "Oncology", "Cancer"],
                "operator": "OR",
            },
        ]
    if speciality == "Internal Medicine - Medical Oncology":
        return [
            {
                "keywords": ["Internal Medicine", "Medical Oncology", "Oncologist", "Oncology", "Cancer"],
                "operator": "OR",
            },
        ]
    if speciality == "Radiology - Radiation Oncology":
        return [
            {"keywords": ["Radiation Oncology"], "operator": ""},
            {
                "keywords": ["Radiation", "Oncologist", "Oncology", "Cancer", "Radiology"],
                "operator": "OR",
            },
        ]
    if speciality == "Surgery - Surgical Oncology":
        return [
            {"keywords": ["Surgical Oncology"], "operator": ""},
            {
                "keywords": ["Oncologist", "Oncology", "Cancer", "Surgery", "Surgical"],
                "operator": "OR",
            },
        ]
    if speciality in ["NEPHROLOGY", "PEDIATRIC NEPHROLOGY"]:
        return [
            {"keywords": ["nephrology", "nephrologist", "kidney", "renal", "nephro"], "operator": "OR"},
        ]
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
            "X-Csrf-Token": config["TWITTER_X_CSRF_TOKEN"],
            "Authorization": f"Bearer {config['TWITTER_AUTHORIZATION']}",
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
            "auth_token": config["TWITTER_AUTH_TOKEN"],
            "ct0": config["TWITTER_X_CSRF_TOKEN"],
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


def facebook_search(fb_id: str):
    if f"facebook:{fb_id}" in cache:
        return cache[f"facebook:{fb_id}"]
    global facebook_index
    acc_data = ""
    facebook_index += 1
    fb_acc = facebook_index % len(facebook_accs)
    try:
        acc_data = json.dumps(get_profile(fb_id, cookies=cookiejar_from_dict(facebook_accs[fb_acc])))
        print(f"[Facebook] [{fb_acc+1}] Scraping [{fb_id}]")
        cache[f"facebook:{fb_id}"] = acc_data
    except TemporarilyBanned as e:
        print(f"[Facebook] [{fb_acc}] [{fb_id}] [{e}]")
    except Exception as e:
        print(f"[Facebook] [{fb_acc}] [{fb_id}] [{e}]")
        cache[f"facebook:{fb_id}"] = acc_data
    return acc_data


def get_facebook_username(fb_link):
    prefix = "/"
    if "/people/" in fb_link:
        prefix = "/people/"
    return fb_link.split(f".com{prefix}")[1].split("/")[0]
