from threading import Thread
from typing import List
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

doc_data = DataReader(config["DOCUMENT"]["INPUT"], config["DOCUMENT"]["OUTPUT"])

data_range = (int(config["DOCUMENT"]["START"]), int(config["DOCUMENT"]["STOP"]))
data_range_len = (data_range[1] - data_range[0]) // 3
data_ranges = [
    (data_range[0], data_range[0] + data_range_len),
    (data_range[0] + data_range_len, data_range[0] + (2 * data_range_len)),
    (data_range[0] + (2 * data_range_len), data_range[0] + (3 * data_range_len) + 1),
]

print(data_ranges)


async def main(thread_id: int, start: int, stop: int):
    try:
        for i, row in doc_data.get_rows(start, stop):
            doc_name = f"{row['fullName'].split('-')[-1]}"  # doc_name = f"{row['first']} {row['last'].split('-')[-1]}"
            doc_speciality = row["specialty"]
            percent_done = (i / doc_data._size) * 100
            print(f"[{thread_id}]==== #{i} : {doc_name} [{doc_speciality}] [{percent_done:.2f}%] ====")
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
        print("Exiting... Details Saved...")
        doc_data.save()
        sys.exit()
    print(f"[Thread {thread_id}] Saving Data...")
    doc_data.save()
    print(f"[Thread {thread_id}] Finished!")


thread_1 = Thread(target=asyncio.run, args=(main(1, *data_ranges[0]),), daemon=True)
thread_2 = Thread(target=asyncio.run, args=(main(2, *data_ranges[1]),), daemon=True)
thread_3 = Thread(target=asyncio.run, args=(main(3, *data_ranges[2]),), daemon=True)
thread_1.start()
thread_2.start()
thread_3.start()
thread_1.join()
thread_2.join()
thread_3.join()
