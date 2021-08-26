import os
from typing import Any, Tuple
import pandas as pd
from utils.types import *
import threading
from utils.drive import consolidate_push
from utils.config import config


class DataReader:
    def __init__(self, file_name: str, save_name: str) -> None:
        self._save_file_name = save_name
        self._df = pd.read_excel(
            file_name,
            dtype=str,
        )
        self._df_len = len(self._df)
        self._size = len(self._df.index)
        self._is_saving = False
        self._current_row = 0
        self._lock = threading.Lock()

    def write_data(self, row_no: int, site_name: str, data: List[ModuleResult]):
        if site_name not in ["linkedin", "twitter", "youtube", "facebook", "instagram", "reddit"]:
            raise ValueError("Invalid Sitename")

        self._df.at[row_no, f"{site_name}Url"] = ", \n".join(
            [f'{result["confidence"]}:{result["link"]}' for result in data]
        )

        # if f"{site_name}Keywords" not in self._df:
        #     self._df[f"{site_name}Keywords"] = ""

        self._df.at[row_no, f"{site_name}Keywords"] = ", \n".join(
            [", ".join(result["keywords"]) for result in data]
        )

    def get_rows(self, start: int = 0, end=float("inf")) -> Tuple[int, Any]:
        with self._lock:
            if self._current_row < start:
                self._current_row = start
        if self._current_row >= min(end, self._df_len):
            return (0, False)
        data = self._current_row, self._df.iloc[self._current_row]
        self._current_row += 1
        self.checkpoint()
        return data

    def checkpoint(self):
        if os.path.isfile("save"):
            print("====Checkpoint Triggered.. Saving====")
            os.remove("save")
            self.save()

    def save(self):
        print("====Saving!====")
        if self._is_saving:
            print("Already Saving...")
        else:
            self._is_saving = True
            self._upload()
            self._is_saving = False
        print("====Saved!====")

    def _upload(self):
        print("====Uploading Data====")
        consolidate_push(
            config["REMOTE_FILE"]["id"],
            self._df,
            config["REMOTE_FILE"]["identifier"],
            config["REMOTE_FILE"]["sheet"],
            self._save_file_name,
        )
        print("====Data Successfully Uplaoaded====")
