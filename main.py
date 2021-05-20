from search_modules.twitter import Twitter
from search_modules.linkedin import Linkedin
from utils.data import DataReader
from search_modules import *
from time import sleep

doc_data = DataReader("doc_data.xlsx", "doc_data_output.xlsx")

for i, row in doc_data.get_rows():
    doc_name = f"{row['first']} {row['last'].split('-')[-1]}"
    doc_speciality = row["specialty"]

    print(f"==== #{i} : {doc_name} [{doc_speciality}] ====")

    linkedin_links = Linkedin.search(doc_name, doc_speciality)
    print(linkedin_links)
    doc_data.write_data(i, "linkedin", linkedin_links)

    twitter_links = Twitter.search(doc_name, doc_speciality)
    print(twitter_links)
    doc_data.write_data(i, "twitter", twitter_links)

    sleep(5)