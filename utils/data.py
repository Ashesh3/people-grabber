from typing import Any, Tuple
import pandas as pd
from utils.types import *
from styleframe import StyleFrame
import threading


class DataReader:
    def __init__(self, file_name: str, save_name: str) -> None:
        self._save_file_name = save_name
        self._df = pd.read_excel(
            file_name,
            converters={
                "linkedinUrl": str,
                "instagramUrl": str,
                "twitterUrl": str,
                "redditUrl": str,
                "youtubeUrl": str,
                "facebookUrl": str,
            },
        )
        self._size = len(self._df.index)
        self._is_saving = False
        self._current_row = 0
        self._lock = threading.Lock()

    def write_data(self, row_no: int, site_name: str, data: List[ModuleResult]):
        if site_name not in ["linkedin", "twitter", "youtube", "facebook", "instagram", "reddit"]:
            raise ValueError("Invalid Sitename")

        self._df.at[row_no, f"{site_name}Url"] = ", \n".join([f'{result["confidence"]}:{result["link"]}' for result in data])

    def get_rows(self, start: int = 0, end=float("inf")) -> Tuple[int, Any]:
        with self._lock:
            if self._is_saving:
                return (0, False)
            if self._current_row < start:
                self._current_row = start
            if self._current_row > end:
                return (0, False)
            data = self._current_row, self._df.iloc[self._current_row]
            self._current_row += 1
            return data

    def save(self):
        if self._is_saving:
            print("Already Saving...")
        else:
            self._is_saving = True
            StyleFrame(self._df).to_excel(self._save_file_name).save()
