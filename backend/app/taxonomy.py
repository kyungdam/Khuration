"""학과·분류·관심 분야 목록 (단일 출처: taxonomy.json).

서버의 판정(matching), 추출(crawler), KHU AI(llm), 입력 검사(schemas)와 앱(/meta)이 모두 여기서 읽는다.
예전에는 같은 목록이 4곳에 따로 있어 내용이 어긋났다(예: 컴퓨터공학과의 단과대).
"""
import json
from pathlib import Path

_T = json.loads((Path(__file__).with_name("taxonomy.json")).read_text(encoding="utf-8"))

CAMPUS_LABEL: dict[str, str] = {c["key"]: c["label"] for c in _T["campuses"]}
DEPARTMENTS: list[dict] = _T["departments"]
COLLEGE_OF: dict[str, str] = {d["dept"]: d["college"] for d in DEPARTMENTS}

# 분류: 첫 번째로 맞는 규칙이 이긴다(순서 중요). 키워드가 없는 '학사'는 기본값
CATEGORY_RULES: list[tuple[str, list[str]]] = [(c["name"], c["keywords"]) for c in _T["categories"] if c["keywords"]]
CATEGORY_NAMES: list[str] = [c["name"] for c in _T["categories"]]
CATEGORY_KEY: dict[str, str] = {c["name"]: c["key"] for c in _T["categories"] if c["key"]}

INTEREST_KEYS: set[str] = {i["key"] for i in _T["interests"]}
TOPIC_RULES: dict[str, list[str]] = {i["key"]: i["topic_keywords"] for i in _T["interests"]}
INTENT_RULES: dict[str, list[str]] = {i["key"]: i["intent_keywords"] for i in _T["interests"] + _T["extra_intents"]}
# KHU AI 문장에 쓰는 짧은 이름 (장학금 → 장학)
LABEL: dict[str, str] = {i["key"]: i.get("short", i["label"]) for i in _T["interests"] + _T["extra_intents"]}


def meta() -> dict:
    """앱(web/index.html)이 GET /meta 로 받는 선택지"""
    return {
        "campuses": _T["campuses"],
        "departments": DEPARTMENTS,
        "categories": CATEGORY_NAMES,
        "interests": [{"key": i["key"], "label": i["label"]} for i in _T["interests"]],
        "grades": _T["grades"],
        "income_bands": _T["income_bands"],
    }
