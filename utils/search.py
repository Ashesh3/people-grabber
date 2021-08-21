import requests
import face_recognition
from typing import List
from urllib.parse import quote_plus
from utils.types import *
from utils.config import config
from utils.cache import cache
from utils.image import *
from utils.drive import get_file

google_api_sheet = get_file(config["GOOGLE_API_FILE"]["id"], config["GOOGLE_API_FILE"]["sheet"])
google_api_data = google_api_sheet.get_all_values()[1:]
google_api_keys = [
    [f"B{i+2}", key[0]] for i, key in enumerate(google_api_data) if "suspended" not in key[1].lower()
]

google_api_index = 0

keywords = get_file(config["KEYWORDS_FILE"]["id"], config["KEYWORDS_FILE"]["sheet"]).get_all_values()[1:]


def keywords_from_speciality(speciality: str) -> List[KeywordSet]:
    for keyword in keywords:
        if speciality.lower().startswith(keyword[0].lower()):
            return [{"keywords": keyword[1].split(","), "operator": "OR"}]
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
    while err_count < len(google_api_keys):
        try:
            res = requests.get(
                url="https://customsearch.googleapis.com/customsearch/v1"
                + f"?cx={'400252859a1a12146' if search_type=='images' else 'b95eae56201592bc4'}"
                + f"&q={quote_plus(search_term)}"
                + f"&searchType={'image&imgType=face' if search_type=='images' else 'search_type_undefined'}"
                + f"&key={google_api_keys[google_api_index % len(google_api_keys)][1]}"
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
                f"GoogleAPI Switching key... {google_api_index % len(google_api_keys)} [{e.__class__}: {e}] [{json_data}]"
            )
            if "suspended" in str(e).lower():
                google_api_sheet.update(google_api_keys[google_api_index][0], "Key Suspended")
                google_api_sheet.format(
                    google_api_keys[google_api_index][0],
                    {
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 0, "blue": 0},
                        }
                    },
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
