from typing import Any, Iterator, Tuple
import pandas as pd
from utils.types import *
from styleframe import StyleFrame


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

    def write_data(self, row_no: int, site_name: str, data: List[ModuleResults]):
        if site_name not in ["linkedin", "twitter", "youtube", "facebook", "instagram", "reddit"]:
            raise ValueError("Invalid Sitename")

        self._df.at[row_no, f"{site_name}Url"] = ", \n".join([f'{result["confidence"]}:{result["link"]}' for result in data])

    def get_rows(self, start: int = 0, end=float("inf")) -> Iterator[Tuple[Any, pd.Series]]:
        for row_no, (i, row) in enumerate(self._df.iterrows()):
            if row_no < start:
                continue
            if row_no > end:
                return
            yield i, row

    def save(self):
        StyleFrame(self._df).to_excel(self._save_file_name).save()
