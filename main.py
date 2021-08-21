from threading import Thread
from typing import List
from utils.data import DataReader
from search_modules import *
import asyncio
import traceback
from datetime import datetime
from utils.config import config
from search_modules import facebook, linkedin, twitter, instagram, youtube

doc_data = DataReader(config["DOCUMENT"]["INPUT"], config["DOCUMENT"]["OUTPUT"])

num_threads = int(config["THREADS"])


async def main(thread_id: int, start: int, stop: int):
    try:
        while True:
            row_id, row = doc_data.get_rows(start, stop)
            if type(row) == bool and row == False:
                break
            doc_name = " ".join([str(row[x]) for x in config["INPUT_COLS"]])
            doc_speciality = row["specialty"]
            percent_done = ((row_id - start) / (stop - start)) * 100
            print(
                f"[{thread_id}]==== {start} - #{row_id}/{stop} : {doc_name} [{doc_speciality}] [{percent_done:.2f}%] ===="
            )
            start_time = datetime.now()
            enabled_search_modules: List[function] = []
            for search_module in [linkedin, twitter, facebook, instagram, youtube]:
                if search_module.__name__.split(".")[-1].title() in config["SEARCH_MODULES"]:
                    enabled_search_modules.append(
                        search_module.search(thread_id, doc_name, doc_speciality)
                    )  # type:ignore
            search_results: List[ModuleResults] = await asyncio.gather(*enabled_search_modules)  # type:ignore
            print(search_results)
            print("[{}]Time elapsed: {}".format(thread_id, datetime.now() - start_time))
            for search_result in search_results:
                doc_data.write_data(row_id, search_result["source"], search_result["results"])
    except:
        print(traceback.format_exc())
        print(f"[{thread_id}] Exiting... Details Saved...")
        doc_data.save()
        doc_data.upload()


start = int(config["DOCUMENT"]["START"])
stop = int(config["DOCUMENT"]["STOP"])
thread_list = []

if start == stop:
    raise RuntimeError("No Entries")

for i in range(num_threads):
    thread = Thread(target=asyncio.run, args=(main(i + 1, start, stop),), daemon=True)
    thread_list.append(thread)

for thread in thread_list:
    thread.start()
for thread in thread_list:
    thread.join()

print(f"[SUCCESS] All Threads Finished! Saving Data...")
doc_data.save()
doc_data.upload()
print(f"[SUCCESS] DONE!")
