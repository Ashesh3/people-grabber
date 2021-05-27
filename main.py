from typing import List
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
from utils.config import config

doc_data = DataReader("doc_data.xlsx", "doc_data_output.xlsx")


async def main():
    try:
        for i, row in doc_data.get_rows():
            doc_name = f"{row['fullName'].split('-')[-1]}"  # doc_name = f"{row['first']} {row['last'].split('-')[-1]}"
            doc_speciality = row["specialty"]
            percent_done = (i / doc_data._size) * 100
            print(f"==== #{i} : {doc_name} [{doc_speciality}] [{percent_done:.2f}%] ====")
            start_time = datetime.now()
            enabled_search_modules: List[function] = []
            for search_module in [Linkedin, Twitter, Facebook]:
                if search_module.__name__ in config["SEARCH_MODULES"]:
                    enabled_search_modules.append(search_module.search(doc_name, doc_speciality))
            search_results = await asyncio.gather(*enabled_search_modules)  # type:ignore
            print(search_results)
            print("Time elapsed: {}".format(datetime.now() - start_time))
            for index, search_result in enumerate(search_results):
                doc_data.write_data(i, config["SEARCH_MODULES"][index].lower(), search_result)
    except:
        print(traceback.format_exc())
        print("Exiting... Details Saved...")
        doc_data.save()
        sys.exit()

    doc_data.save()


asyncio.run(main())
