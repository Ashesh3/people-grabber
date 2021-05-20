from typing import List, TypedDict


class KeywordSet(TypedDict):
    keywords: List[str]
    operator: str


class GoogleResults(TypedDict):
    title: str
    link: str
    description: str


class ModuleResults(TypedDict):
    link: str
    confidence: float
