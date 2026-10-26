"""KHU AI 대화. 지금은 규칙 기반: 질문에서 키워드를 뽑아 내 맞춤 피드에서 찾아 준다.
TODO: ChatKHU API 형식 확인 후 답변 문장 생성만 LLM으로 교체.
      공지 검색·자격 판정은 계속 코드가 한다(LLM이 지원 자격을 지어내지 않게)."""
from .intent import extract_keywords

LABEL = {
    "ai_data": "AI·데이터", "dev_it": "개발·IT", "design": "디자인", "scholarship": "장학",
    "startup": "창업", "language_abroad": "어학·해외", "internship": "현장실습", "contest": "공모전",
}


def answer(message: str, feed: list, tags: dict) -> dict:
    kws = extract_keywords(message)
    week = any(w in message for w in ["이번 주", "이번주", "급한", "임박"])
    picked = []
    for it in feed:
        if kws and not (set(kws) & set(it.topics)):
            continue
        if week and (it.d_day is None or it.d_day > 7):
            continue
        picked.append(it)
    picked.sort(key=lambda i: i.d_day if i.d_day is not None else 9999)
    picked = picked[:3]

    what = "·".join(LABEL[k] for k in kws if k in LABEL) or "관심 분야"
    if picked:
        mine = [LABEL[k] for k in tags.get("interests", []) if k in LABEL]
        lead = f"관심 분야 {', '.join(mine)}를 반영해 " if mine else ""
        text = f"{lead}지금 지원할 수 있는 {what} 공지 {len(picked)}건을 찾았어요."
        if picked[0].d_day is not None:
            text += f" 마감이 가장 가까운 공지는 D-{picked[0].d_day}예요."
    else:
        text = f"지금 지원할 수 있는 {what} 공지를 찾지 못했어요. 공지사항 탭에서 직접 검색해 보세요."
    return {
        "answer": text,
        "keywords": kws,
        "items": picked,
        "sources": sorted({i.source for i in picked}),
        "engine": "rule",
    }
