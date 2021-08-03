import requests
import face_recognition
from typing import List
from urllib.parse import quote_plus
from utils.types import *
from utils.config import config
from utils.cache import cache
from utils.image import *


google_keys = config["GOOGLE_SEARCH_KEYS"]
google_api_index = 0


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    for keyword in config["KEYWORDS"]:
        if speciality.startswith(keyword):
            return config["KEYWORDS"][keyword]
    raise ValueError(f"Invalid Speciality: {speciality}")


def get_search_query(doc_name: str, site: str, keyword: KeywordSet) -> str:
    return (
        f'(intitle:"{doc_name}") site:{site} '
        + '"'
        + f"\" {keyword['operator']} \"".join(keyword["keywords"])
        + '"'
    )


def google_search(search_term: str, search_type, max_terms: int = 5) -> List[GoogleResults]:
    if search_type not in ["search", "images"]:
        raise RuntimeError("Invalid Google Search")
    if f"{search_type}:{search_term}" in cache:
        return cache[f"{search_type}:{search_term}"][:max_terms]
    if config["DRY_RUN"]:
        return []
    global google_api_index
    err_count = 0
    json_data = {}
    while err_count < len(google_keys):
        try:
            res = requests.get(
                url="https://customsearch.googleapis.com/customsearch/v1"
                + f"?cx={'400252859a1a12146' if search_type=='images' else 'b95eae56201592bc4'}"
                + f"&q={quote_plus(search_term)}"
                + f"&searchType={'image&imgType=face' if search_type=='images' else 'search_type_undefined'}"
                + f"&key={google_keys[google_api_index % len(google_keys)]}"
            )
            json_data = res.json()
            if "error" in json_data:
                raise ValueError("Error Scrapping Google.. ", json_data["error"]["message"])
            if "items" not in json_data:
                json_data["items"] = []
            if search_type == "search":
                final_search_results: List[GoogleResults] = [
                    {"title": result["title"], "link": result["link"], "description": result["snippet"]}
                    for result in json_data["items"]
                ]
                cache[f"{search_type}:{search_term}"] = final_search_results
                return final_search_results[:max_terms]
            elif search_type == "images":
                final_image_results: List[GoogleResults] = [
                    {"title": result["title"], "link": result["link"], "description": result["snippet"]}
                    for result in json_data["items"]
                ]
                cache[f"{search_type}:{search_term}"] = final_image_results
                return final_image_results[:max_terms]
        except Exception as e:
            google_api_index += 1
            print(
                f"GoogleAPI Switching key... {google_api_index % len(google_keys)} [{e.__class__}: {e}] [{json_data}]"
            )
            err_count += 1
    raise ValueError("Error in GoogleAPI..")


def similar_image(source, test) -> bool:
    if f"face:{source} {test}" in cache:
        return cache[f"face:{source} {test}"]
    if config["DRY_RUN"]:
        return False
    if not source or not test:
        cache[f"face:{source} {test}"] = False
        return False
    try:
        known_image = face_recognition.load_image_file(requests.get(source, stream=True).raw)
        unknown_image = face_recognition.load_image_file(requests.get(test, stream=True).raw)

        known_encoding = face_recognition.face_encodings(known_image)
        unknown_encoding = face_recognition.face_encodings(unknown_image)

        if not known_encoding or not unknown_encoding:
            cache[f"face:{source} {test}"] = False
            return False

        result = face_recognition.compare_faces([known_encoding[0]], unknown_encoding[0])[0]
        cache[f"face:{source} {test}"] = result

        return result

    except Exception as e:
        print("FaceAPI Error :", e)
        cache[f"face:{source} {test}"] = False
    return False
