from typing import List, TypedDict


class KeywordSet(TypedDict):
    keywords: List[str]
    operator: str


class GoogleResults(TypedDict):
    title: str
    link: str
    description: str


class ModuleResult(TypedDict):
    link: str
    confidence: float


class ModuleResults(TypedDict):
    source: str
    results: List[ModuleResult]


class TwitterResults(TypedDict):
    name: str
    screen_name: str
    description: str
    full_text: str
