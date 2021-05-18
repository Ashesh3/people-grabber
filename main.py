import pandas as pd
from time import sleep
import http.client
import json
from urllib.parse import quote_plus

# for headless
# chrome_options = Options()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--window-size=1920x1080")
# driver = webdriver.Chrome(ChromeDriverManager().install(), options = chrome_options)

df = pd.read_excel(
    "doc_data.xlsx",
    converters={
        "linkedinUrl": str,
        "instagramUrl": str,
        "twitterUrl": str,
        "redditUrl": str,
        "youtubeUrl": str,
        "facebookUrl": str,
    },
)


def google(search_term):
    conn = http.client.HTTPSConnection("google-search3.p.rapidapi.com")
    conn.request(
        "GET",
        f"/api/v1/search/q={quote_plus(search_term)}&num=100",
        headers={
            "x-rapidapi-key": "FJviVQShGTmshjDIBZX74GdlFRkOp1eUIT0jsnL7BOQJL4fWV6",
            "x-rapidapi-host": "google-search3.p.rapidapi.com",
        },
    )
    try:
        data = conn.getresponse().read().decode("utf-8")
        json_data = json.loads(data)
    except Exception:
        print("Error scrapping Google")
        return []
    return [{"title": result["title"], "link": result["link"]} for result in json_data["results"]]


def search_profile(name):
    name = name.lower()
    print(f"Processing: {name}")

    social_links = {"linkedin": "", "twitter": "", "instagram": "", "reddit": "", "youtube": "", "facebook": ""}

    for platform in social_links:
        print(f"Searching: {platform}")
        search_query = f'{name} site:{platform}.com "cancer" OR "oncology"'

        results = google(search_query)

        for result in results:
            if name in result["title"].lower() and result["link"] not in social_links[platform]:
                social_links[platform] += result["link"] + ", "

        print("Links:", social_links[platform])
        sleep(2)

    return social_links


for i, row in df.iterrows():
    doc_name = f"{row['first']} {row['last']}"
    links_dict = search_profile(doc_name)

    for key in links_dict:
        df.at[i, f"{key}Url"] = links_dict[key]

    df.to_excel("filled_doc_data.xlsx")
    print("Waiting 10 seconds...")
    sleep(10)
