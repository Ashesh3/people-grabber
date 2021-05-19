from abc import ABC, abstractmethod
from typing import List


class SerchModule(ABC):
    @abstractmethod
    @staticmethod
    def search(doc_name: str, keywords: List[str]) -> object:
        pass
