from time import sleep
from data import DataReader
from search_modules import *

keywords = ["oncology", "cancer", "nurse"]
doc_data = DataReader("doc_data.xlsx")

for i, row in doc_data.get_rows():
    doc_name = f"{row['first']} {row['last']}"
    print(f"==== #{i} : {doc_name} ====")

    linkedin_links = Linkedin.search(doc_name, keywords)
    doc_data.write_data(i, "linkedin", ", ".join(linkedin_links))

    twitter_results = Twitter.search(doc_name, keywords)
    doc_data.write_data(i, "twitter", ", ".join(twitter_results))

    print("Waiting 10 seconds...")
    sleep(10)
