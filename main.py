from threading import Thread
from typing import List
from search_modules.twitter import Twitter
from search_modules.linkedin import Linkedin
from search_modules.facebook import Facebook
from utils.data import DataReader
from search_modules import *
import asyncio
import os
import traceback
from datetime import datetime
from utils.config import config
from signal import SIGINT

doc_data = DataReader(config["DOCUMENT"]["INPUT"], config["DOCUMENT"]["OUTPUT"])

num_threads = int(config["THREADS"])


async def main(thread_id: int, start: int, stop: int):
    try:
        for i, row in doc_data.get_rows(start, stop):
            doc_name = " ".join([str(row[x]) for x in config["INPUT_COLS"]])
            doc_speciality = row["specialty"]
            percent_done = ((i - start) / (stop - start)) * 100
            print(f"[{thread_id}]==== #{i}/{stop} : {doc_name} [{doc_speciality}] [{percent_done:.2f}%] ====")
            start_time = datetime.now()
            enabled_search_modules: List[function] = []
            for search_module in [Linkedin, Twitter, Facebook]:
                if search_module.__name__ in config["SEARCH_MODULES"]:
                    enabled_search_modules.append(search_module.search(doc_name, doc_speciality))  # type:ignore
            search_results = await asyncio.gather(*enabled_search_modules)  # type:ignore
            print(search_results)
            print("[{}]Time elapsed: {}".format(thread_id, datetime.now() - start_time))
            for index, search_result in enumerate(search_results):
                doc_data.write_data(i, config["SEARCH_MODULES"][index].lower(), search_result)
    except:
        print(traceback.format_exc())
        print(f"[{thread_id}] Exiting... Details Saved...")
        doc_data.save()
        os.kill(os.getpid(), SIGINT)


start = int(config["DOCUMENT"]["START"])
stop = int(config["DOCUMENT"]["STOP"])
data_range_len = (stop - start) // num_threads
thread_list = []
for i in range(num_threads):
    stop = start + data_range_len
    thread = Thread(target=asyncio.run, args=(main(i + 1, start, stop),), daemon=True)
    thread_list.append(thread)
    start = stop

for thread in thread_list:
    thread.start()
for thread in thread_list:
    thread.join()

print(f"[SUCCESS] All Threads Finished! Saving Data...")
doc_data.save()
print(f"[SUCCESS] DONE!")
