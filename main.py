from search_modules import facebook
from search_modules.twitter import Twitter
from search_modules.linkedin import Linkedin
from search_modules.facebook import Facebook
from utils.data import DataReader
from search_modules import *
import asyncio
import sys
import traceback
from datetime import datetime

doc_data = DataReader("doc_data.xlsx", "doc_data_output.xlsx")


async def main():
    try:
        for i, row in doc_data.get_rows():
            doc_name = f"{row['fullName'].split('-')[-1]}"  # doc_name = f"{row['first']} {row['last'].split('-')[-1]}"
            doc_speciality = row["specialty"]
            percent_done = (i / doc_data._size) * 100
            print(f"==== #{i} : {doc_name} [{doc_speciality}] [{percent_done:.2f}%] ====")
            start_time = datetime.now()
            search_results = await asyncio.gather(
                Linkedin.search(doc_name, doc_speciality),
                Twitter.search(doc_name, doc_speciality),
                Facebook.search(doc_name, doc_speciality),
            )
            print(search_results)
            print("Time elapsed: {}".format(datetime.now() - start_time))
            linkedin_links, twitter_links, facebook_links = search_results
            doc_data.write_data(i, "linkedin", linkedin_links)
            doc_data.write_data(i, "twitter", twitter_links)
            doc_data.write_data(i, "facebook", facebook_links)
    except:
        print(traceback.format_exc())
        print("Exiting... Details Saved...")
        doc_data.save()
        sys.exit()

    doc_data.save()


asyncio.run(main())
