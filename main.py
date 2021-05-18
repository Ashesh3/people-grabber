from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from time import sleep

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--log-level=3")
driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

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


def search_profile(name):
    name = name.lower()
    print(f"Processing: {name}")

    social_links = {"linkedin": "", "twitter": "", "instagram": "", "reddit": "", "youtube": "", "facebook": ""}

    for platform in social_links:
        print(f"Searching: {platform}")
        search_query = f'{name} site:{platform}.com "cancer" "oncology"'

        driver.get(f"https://www.google.com/search?q={search_query}")
        search_headings = driver.find_elements_by_css_selector(".yuRUbf")
        for heading in search_headings:
            site_title = heading.find_element_by_tag_name("h3").text
            site_link = heading.find_element_by_tag_name("a").get_attribute("href").split("?")[0]

            if name in site_title.lower() and site_link not in social_links[platform]:
                social_links[platform] += site_link + ", "

        print("Links:", social_links[platform], "\nWaiting 10 seconds...")
        sleep(10)

    return social_links


for i, row in df.iterrows():
    doc_name = f"{row['first']} {row['last']}"
    links_dict = search_profile(doc_name)

    for key in links_dict:
        df.at[i, f"{key}Url"] = links_dict[key]

    print("Waiting 60 seconds...")
    sleep(60)

df.to_excel("filled_doc_data.xlsx")
driver.quit()