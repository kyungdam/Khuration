"""추출 정확도 측정 (정답표 채점).

  python -m app.crawler.eval_extract export --n 20   # 크롤링된 실제 공지 20건 → backend/eval/gold.csv (엑셀로 열기)
  (엑셀에서 '정답_' 칸을 원문과 비교해 고치고, 다 본 줄은 '검토완료'에 O)
  python -m app.crawler.eval_extract score           # 채점 → 화면 + backend/eval/report.md
  python -m app.crawler.eval_extract stats           # 정답 없이: 자동 검증이 확인·차단한 양 → backend/eval/stats.md

stats 는 정답표 없이 돈다. 크롤링 때 저장된 AI 답(추출 캐시)만 다시 검증해서 세므로 크레딧이 들지 않는다.
'정확도'가 아니라 '검증 단계가 원문으로 확인한 값 / 근거가 없어 막은 값'의 양이다.

채점 방식
- 같은 공지 글로 '검증 전'(AI 1차 답 그대로)과 '검증 후'(근거 대조 + 상위 모델 재추출 + 기권)를 각각 만들어 정답과 비교한다.
- 항목별: 정밀도 = 값을 낸 것 중 맞은 비율, 재현율 = 정답이 있는 것 중 맞힌 비율,
  잘못 확정 = 값을 냈는데 틀린 수 (지원 자격 안내에서 가장 위험한 오류).
- 마감일 정확도 = 날짜(없음 포함)가 정답과 같은 비율.
ChatKHU 키가 필요하다. 크롤링 때 만든 추출 캐시가 있으면 다시 부르지 않는다.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import timedelta
from pathlib import Path

from ..db import SessionLocal
from ..models import Notice
from .base import RawNotice
from .verify import extraction_source, norm

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
GOLD = EVAL_DIR / "gold.csv"
REPORT = EVAL_DIR / "report.md"
STATS = EVAL_DIR / "stats.md"

# (CSV 칸 이름, criteria 키) — 새 조건을 추가하면 여기에도 넣는다
FIELDS = [
    ("정답_마감일", "deadline"),
    ("정답_캠퍼스", "campuses"),
    ("정답_학과단과대", "depts"),
    ("정답_학년", "grades"),
    ("정답_최저학점", "min_gpa"),
    ("정답_최소이수학점", "min_credits"),
    ("정답_소득분위이하", "income_max"),
    ("정답_어학성적필요", "requires_lang_score"),
    ("정답_누구나", "open_to_all"),
]
HEAD = ["notice_id", "제목", "원문링크", "검토완료"] + [c for c, _ in FIELDS] + ["메모"]
LABEL = {"deadline": "마감일", "colleges": "단과대", "departments": "학과", "campuses": "캠퍼스", "depts": "학과·단과대", "grades": "학년", "min_gpa": "최저학점",
         "min_credits": "최소 이수학점", "income_max": "소득분위", "requires_lang_score": "어학 성적", "open_to_all": "누구나"}
CAMPUS = {"seoul": "서울", "global": "국제"}


# ---------- 값 ↔ 칸 ----------
def kst_date(dt) -> str:
    return (dt + timedelta(hours=9)).date().isoformat() if dt else ""


def to_cells(deadline, crit: dict) -> dict:
    c = crit or {}
    yn = lambda v: "O" if v is True else ""  # noqa: E731
    num = lambda v: "" if v is None else (str(int(v)) if float(v).is_integer() else str(v))  # noqa: E731
    return {
        "정답_마감일": kst_date(deadline),
        "정답_캠퍼스": ",".join(CAMPUS.get(x, x) for x in c.get("campuses") or []),
        "정답_학과단과대": ",".join((c.get("departments") or []) + (c.get("colleges") or [])),
        "정답_학년": ",".join(str(g) for g in c.get("grades") or []),
        "정답_최저학점": num(c.get("min_gpa")),
        "정답_최소이수학점": num(c.get("min_credits")),
        "정답_소득분위이하": num(c.get("income_max")),
        "정답_어학성적필요": yn(c.get("requires_lang_score")),
        "정답_누구나": yn(c.get("open_to_all")),
    }


def _split(s: str) -> list[str]:
    return [x.strip() for x in re.split(r"[,/·]", s or "") if x.strip()]


def parse_cell(key: str, s: str):
    """정답 칸 → 비교용 값 (빈칸 = 조건 없음)"""
    s = (s or "").strip()
    if key == "deadline":
        m = re.findall(r"\d+", s)
        return f"{int(m[0]):04d}-{int(m[1]):02d}-{int(m[2]):02d}" if len(m) >= 3 else ""
    if key == "campuses":
        return frozenset("seoul" if "서울" in x else "global" for x in _split(s))
    if key == "depts":
        return frozenset(norm(x) for x in _split(s))
    if key == "grades":
        return frozenset(int(x) for x in re.findall(r"[1-6]", s))
    if key in ("min_gpa", "min_credits", "income_max"):
        try:
            return float(s) if s else None
        except ValueError:
            return None
    return True if s.upper() in ("O", "Y", "TRUE", "1", "예") else None


def pred_value(key: str, ex):
    """추출 결과 → 비교용 값"""
    c = ex.criteria or {}
    if key == "deadline":
        return kst_date(ex.deadline)
    if key == "campuses":
        return frozenset(c.get("campuses") or [])
    if key == "depts":
        return frozenset(norm(x) for x in (c.get("departments") or []) + (c.get("colleges") or []))
    if key == "grades":
        return frozenset(c.get("grades") or [])
    if key in ("min_gpa", "min_credits", "income_max"):
        v = c.get(key)
        return float(v) if v is not None else None
    return True if c.get(key) is True else None


def _empty(v) -> bool:
    return v in (None, "", frozenset())


# ---------- 원문 다시 만들기 ----------
def rebuild(n: Notice) -> tuple[RawNotice, str]:
    raw = RawNotice(source_name=n.source_name, url=n.url, title=n.title, body_text=n.body_text or "", posted_at=n.posted_at)
    return raw, extraction_source(n.body_text or "", [a.extracted_text for a in n.attachments if a.extracted_text])


# ---------- 명령 ----------
def export(n: int, force: bool) -> None:
    if GOLD.exists() and not force:
        sys.exit(f"{GOLD} 가 이미 있어요. 덮어쓰려면 --force")
    EVAL_DIR.mkdir(exist_ok=True)
    with SessionLocal() as db:
        rows = (
            db.query(Notice).filter(Notice.is_demo.is_(False))
            .order_by(Notice.posted_at.desc().nullslast(), Notice.id.desc()).limit(n).all()
        )
        with GOLD.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: 엑셀에서 한글이 안 깨지게
            w = csv.DictWriter(f, HEAD)
            w.writeheader()
            for x in rows:
                crit = {k: v for k, v in (x.criteria or {}).items() if not k.startswith("_")}
                w.writerow({"notice_id": x.id, "제목": x.title, "원문링크": x.url, "검토완료": "", "메모": "",
                            **to_cells(x.deadline, crit)})
    print(f"{len(rows)}건 → {GOLD}")
    print("엑셀로 열어 '정답_' 칸을 원문과 비교해 고치고(조건이 없으면 빈칸), 다 본 줄의 '검토완료'에 O를 넣으세요.")


def _metrics(pairs: list[tuple]) -> dict:
    pred = sum(1 for p, _ in pairs if not _empty(p))
    gold = sum(1 for _, g in pairs if not _empty(g))
    ok = sum(1 for p, g in pairs if not _empty(p) and p == g)
    return {"pred": pred, "gold": gold, "ok": ok, "wrong": pred - ok,
            "precision": ok / pred if pred else None, "recall": ok / gold if gold else None}


def _pct(v) -> str:
    return "-" if v is None else f"{v * 100:.0f}%"


def score() -> None:
    from .extract_llm import extract_with_llm
    from ..llm import client

    if not client.available():
        sys.exit("ChatKHU 키가 없어요 (backend/.env)")
    if not GOLD.exists():
        sys.exit("정답표가 없어요. 먼저 export")
    with GOLD.open(encoding="utf-8-sig", newline="") as f:
        gold_rows = [r for r in csv.DictReader(f) if (r.get("검토완료") or "").strip().upper() in ("O", "Y", "V", "✔", "확인")]
    if not gold_rows:
        sys.exit("'검토완료'에 O 표시된 줄이 없어요")

    res = {"before": {k: [] for _, k in FIELDS}, "after": {k: [] for _, k in FIELDS}}
    misses: list[str] = []
    with SessionLocal() as db:
        for r in gold_rows:
            n = db.get(Notice, int(r["notice_id"]))
            if n is None:
                print(f"  공지 {r['notice_id']} 없음 (DB가 바뀌었나요?) → 건너뜀")
                continue
            raw, src = rebuild(n)
            print(f"  채점 중: {n.title[:40]}")
            before = extract_with_llm(raw, src, verify=False)
            after = extract_with_llm(raw, src, verify=True)
            for col, key in FIELDS:
                g = parse_cell(key, r.get(col, ""))
                pb, pa = pred_value(key, before), pred_value(key, after)
                res["before"][key].append((pb, g))
                res["after"][key].append((pa, g))
                if not _empty(pa) and pa != g:
                    misses.append(f"- [{n.id}] {n.title[:30]} · {LABEL[key]}: AI={_show(pa)} / 정답={_show(g)}")

    lines = [f"# 추출 정확도 (채점 {len(gold_rows)}건)", "",
             "| 항목 | 검증 전 정밀도 | 검증 후 정밀도 | 검증 전 재현율 | 검증 후 재현율 | 잘못 확정 (전→후) |",
             "|---|---|---|---|---|---|"]
    for _, key in FIELDS:
        b, a = _metrics(res["before"][key]), _metrics(res["after"][key])
        if not (b["pred"] or b["gold"] or a["pred"]):
            continue
        lines.append(f"| {LABEL[key]} | {_pct(b['precision'])} | {_pct(a['precision'])} | {_pct(b['recall'])} | "
                     f"{_pct(a['recall'])} | {b['wrong']} → {a['wrong']} |")
    dl_b = sum(1 for p, g in res["before"]["deadline"] if p == g) / max(len(res["before"]["deadline"]), 1)
    dl_a = sum(1 for p, g in res["after"]["deadline"] if p == g) / max(len(res["after"]["deadline"]), 1)
    wrong_b = sum(_metrics(v)["wrong"] for v in res["before"].values())
    wrong_a = sum(_metrics(v)["wrong"] for v in res["after"].values())
    lines += ["", f"- 마감일 정확도(없음 포함 일치): {_pct(dl_b)} → {_pct(dl_a)}",
              f"- 전체 잘못 확정(틀린 값을 확정해서 보여준 수): {wrong_b} → {wrong_a}",
              "- 정밀도: 값을 낸 것 중 맞은 비율 / 재현율: 정답에 조건이 있는 것 중 맞힌 비율",
              "", "## 검증 후에도 틀린 항목", *(misses or ["- 없음"])]
    text = "\n".join(lines)
    EVAL_DIR.mkdir(exist_ok=True)
    REPORT.write_text(text + "\n", encoding="utf-8")
    print("\n" + text + f"\n\n→ {REPORT}")


class _NoNewCalls:
    """stats 동안 캐시에 없는 AI 호출을 막는다 (크레딧 0)"""

    def __enter__(self):
        from ..llm import client

        self.client, self.orig = client, client.chat

        def blocked(*a, **k):
            raise client.LLMError("캐시 없음")

        client.chat = blocked
        return self

    def __exit__(self, *exc):
        self.client.chat = self.orig


def stats() -> None:
    from collections import Counter

    from ..config import settings
    from . import extract_llm as el

    proposed = kept1 = 0
    reasons: Counter = Counter()
    per_field: dict[str, Counter] = {}
    final_kept = strong_used = no_cache = notices = all_check = 0
    dl_prop = dl_ok1 = dl_final = 0
    with SessionLocal() as db, _NoNewCalls():
        rows = db.query(Notice).filter(Notice.is_demo.is_(False)).all()
        for n in rows:
            raw, src = rebuild(n)
            posted = raw.posted_at.strftime("%Y-%m-%d") if raw.posted_at else "알 수 없음"
            body = src[: el.MAX_TEXT_CHARS]
            try:
                data = el._call(settings.chatkhu_model_extract, raw, posted, body)
            except Exception:
                no_cache += 1
                continue
            notices += 1
            _, _, _, r1 = el._checked(data, raw, f"{raw.title}\n{body}")
            proposed += len(r1.kept) + len(r1.dropped)
            kept1 += len(r1.kept)
            for k in r1.kept:
                per_field.setdefault(k, Counter())["확인"] += 1
            for k, why in r1.dropped.items():
                reasons[why] += 1
                per_field.setdefault(k, Counter())["차단"] += 1
            if data.get("deadline"):
                dl_prop += 1
                dl_ok1 += "deadline" in r1.kept
            ex = el.extract_with_llm(raw, src)  # 상위 모델 답이 캐시에 있으면 그것까지 반영
            fk = ex.verification.get("kept", [])
            final_kept += len(fk)
            strong_used += ex.engine == "llm+strong"
            dl_final += "deadline" in fk
            all_check += not [k for k in fk if k != "deadline"]

    if not notices:
        sys.exit("검증할 추출 결과가 없어요. 먼저 크롤링(python -m app.crawler.run)을 실행하세요.")
    pct = lambda a, b: f"{a / b * 100:.0f}%" if b else "-"  # noqa: E731
    lines = [
        f"# 자동 검증 통계 (실제 공지 {notices}건, 정답표 없이)", "",
        f"- AI가 제시한 값(조건+마감일): **{proposed}개**",
        f"- 원문 근거로 확인: **{kept1}개 ({pct(kept1, proposed)})**",
        f"- 근거가 없거나 맞지 않아 자동 차단: **{proposed - kept1}개 ({pct(proposed - kept1, proposed)})**"
        " → 앱에서는 '확인 필요'로 표시",
        f"- 상위 모델 재추출이 쓰인 공지: {strong_used}건 / 최종 확인된 값: {final_kept}개",
        f"- 마감일: AI 제시 {dl_prop}건 중 원문 날짜와 일치 {dl_ok1}건 ({pct(dl_ok1, dl_prop)}), 최종 {dl_final}건",
        f"- 확인된 지원 조건이 하나도 없는 공지(전부 '확인 필요'): {all_check}건 ({pct(all_check, notices)})",
        "", "## 차단 이유", *(f"- {why}: {c}개" for why, c in reasons.most_common()),
        "", "## 항목별 (확인 / 차단)",
        *(f"- {LABEL.get(k, k)}: {c['확인']} / {c['차단']}" for k, c in sorted(per_field.items())),
    ]
    if no_cache:
        lines += ["", f"(추출 캐시가 없어 제외한 공지 {no_cache}건 — 크롤링을 한 번 더 하면 포함됩니다)"]
    text = "\n".join(lines)
    EVAL_DIR.mkdir(exist_ok=True)
    STATS.write_text(text + "\n", encoding="utf-8")
    print(text + f"\n\n→ {STATS}")


def _show(v) -> str:
    if isinstance(v, frozenset):
        return ",".join(sorted(map(str, v))) or "없음"
    return "없음" if _empty(v) else str(v)


def main():
    p = argparse.ArgumentParser(description="추출 정확도 측정")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="정답표 만들기 (backend/eval/gold.csv)")
    e.add_argument("--n", type=int, default=20)
    e.add_argument("--force", action="store_true")
    sub.add_parser("score", help="채점 (backend/eval/report.md)")
    sub.add_parser("stats", help="정답 없이 자동 검증 통계 (backend/eval/stats.md, 크레딧 0)")
    a = p.parse_args()
    {"export": lambda: export(a.n, a.force), "score": score, "stats": stats}[a.cmd]()


if __name__ == "__main__":
    main()
