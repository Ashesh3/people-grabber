import http.client, json, re, requests, zlib, pickle, sqlite3
from typing import List, Dict, Union
from urllib.parse import quote_plus
from utils.types import *
from sqlitedict import SqliteDict
from utils.config import config
from bs4 import BeautifulSoup
from time import sleep


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
    if config["DRY_RUN"]:
        return "{}"
    for tries in range(1, 11):
        print(f"[Linkedin] Scraping [{username}] [{tries}]")
        header_dic = {"Authorization": "Bearer " + config["LINKEDIN_API_KEY"]}
        params = {
            "url": f"https://www.linkedin.com/in/{username}",
        }
        response = requests.get("https://nubela.co/proxycurl/api/v2/linkedin", params=params, headers=header_dic)
        search_result = response.text
        if response.status_code not in [200, 404, 429]:
            raise RuntimeError(f"[Linkedin] Error Scraping [{response.status_code}] [{search_result}]")
        elif response.status_code == 429:
            print(f"[Linkedin] Ratelimited! Waiting 60secs... [{tries}]")
            sleep(60)
        else:
            cache[f"linkedin:{username}"] = search_result
            return search_result
    raise RuntimeError("[Linkedin] Permanent Failure")


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
    if config["DRY_RUN"]:
        return []
    global rapid_api_index
    err_count = 0
    json_data = {}
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
            if "message" in json_data:
                raise ValueError("Error Scrapping Google.. ", json_data["message"])
            final_search_results: List[GoogleResults] = [
                {"title": result["title"], "link": result["link"], "description": result["description"]}
                for result in json_data["results"]
            ]
            cache[search_term] = final_search_results
            return final_search_results[:max_terms]
        except Exception as e:
            rapid_api_index += 1
            print(f"RapidApi Switching key... {rapid_api_index % len(rapid_api_keys)} [{e.__class__}: {e}] [{json_data}]")
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
    if response.status_code != 200:
        raise RuntimeError(f"Twitter Likes error {response.status_code}")
    return response.text


def twitter_query(query, search_type) -> Union[str, Dict[str, TwitterResults]]:
    if f"{query}:{search_type}" in cache:
        return cache[f"{query}:{search_type}"]
    if config["DRY_RUN"]:
        return {}
    for _ in range(15):
        try:
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
                raise RuntimeError(f"Twitter Error {res.status_code} {res.text}")
        except Exception as e:
            print(f"Twitter Error: {e} Retrying")
            refresh_twitter_anon_token()
            sleep(30)
    raise ValueError("Permanent Twitter Failure")


def facebook_search(fb_link: str):
    fb_id = get_facebook_username(fb_link)
    if f"facebook:{fb_id}" in cache:
        return cache[f"facebook:{fb_id}"]
    if config["DRY_RUN"]:
        return ""
    sleep(10)
    global facebook_index
    facebook_index += 1
    fb_acc = facebook_index % len(facebook_accs)
    try:
        print(f"[Facebook] [{fb_acc+1}] Scraping [{fb_id}]")
        acc_resp = requests.get(
            fb_link,
            headers={
                "Host": "mbasic.facebook.com",
                "Sec-Ch-Ua": '\\" Not A;Brand\\";v=\\"99\\", \\"Chromium\\";v=\\"90\\"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Accept-Language": "en-US,en;q=0.9",
            },
            cookies=facebook_accs[fb_acc],
        ).text
        if any([x in acc_resp for x in ["use this feature at the moment", "temporarily blocked"]]):
            print(f"[Facebook Banned] [{fb_acc+1}] [Sleep 600]")
            sleep(600)
            raise RuntimeError("[ERROR] Facebook banned")
        cache[f"facebook:{fb_id}"] = acc_resp
        return acc_resp
    except Exception as e:
        print(f"[Facebook] [{fb_acc}] [{fb_id}] [{e}]")
    return ""


def get_facebook_username(fb_link):
    prefix = "/"
    if "/people/" in fb_link:
        prefix = "/people/"
    return fb_link.split(f".com{prefix}")[1].split("/")[0]


def facebook_legacy_search(fb_link: str):
    acc_data = requests.get(
        fb_link,
        headers={
            "authority": "www.facebook.com",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="90", "Microsoft Edge";v="90"',
            "sec-ch-ua-mobile": "?0",
            "upgrade-insecure-requests": "1",
            "User-Agent": "NokiaC3-00/5.0 (07.20) Profile/MIDP-2.1 Configuration/CLDC-1.1 Mozilla/5.0 AppleWebKit/420+ (KHTML, like Gecko) Safari/420+",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "sec-fetch-site": "none",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
            "accept-language": "en-US,en;q=0.9",
            "cookie": "datr=AG2vYDjuin9s_58hMyTbvceY; dpr=1.25",
        },
    ).text
    return acc_data


def fb_people_search(name):
    if f"facebook_people:{name}" in cache:
        return cache[f"facebook_people:{name}"]
    if config["DRY_RUN"]:
        return []
    sleep(30)
    global facebook_index
    facebook_index += 1
    fb_acc = facebook_index % len(facebook_accs)
    response = requests.get(
        "https://mbasic.facebook.com/search/people/",
        headers={
            "Host": "mbasic.facebook.com",
            "Sec-Ch-Ua": '\\" Not A;Brand\\";v=\\"99\\", \\"Chromium\\";v=\\"90\\"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "en-US,en;q=0.9",
        },
        params=(
            ("q", name),
            ("source", "filter"),
            ("isTrending", "0"),
        ),
        cookies=facebook_accs[fb_acc],
    )
    soup = BeautifulSoup(response.content, "html.parser")
    if not soup.select("#BrowseResultsContainer"):
        return []
    results = soup.select("#BrowseResultsContainer")[0].select(".n.bz a")
    pages = [f"https://facebook.com{results[i].get('href').split('refid')[0]}" for i in range(len(results))]
    cache[f"facebook_people:{name}"] = pages
    return pages
