from typing import Any, Iterator, Tuple
import pandas as pd


class DataReader:
    def __init__(self, file_name: str) -> None:
        self._file_name = file_name
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

    def write_data(self, row_no: int, site_name: str, data: str):
        if site_name not in ["linkedin", "twitter", "youtube", "reddit", "instagram", "reddit"]:
            raise ValueError("Invalid Sitename")

        self._df.at[row_no, f"{site_name}Url"] = data
        self.save()

    def get_rows(self) -> Iterator[Tuple[Any, pd.Series]]:
        for i, row in self._df.iterrows():
            yield i, row

    def save(self):
        self._df.to_excel(self._file_name)
