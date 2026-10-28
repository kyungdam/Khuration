"""생각 수준(reasoning_effort) 비교: 실제 공지로 '기본값'과 'low'를 번갈아 추출해 시간·토큰·결과를 비교한다.

    python -m app.llm.bench_effort              # 크롤링된 실제 공지 5건 × 2회 (AI 호출 20번)
    python -m app.llm.bench_effort --n 5 --repeat 3

- 추출 캐시를 쓰지 않고 매번 ChatKHU를 부른다(크레딧 사용). 캐시 파일은 건드리지 않는다.
- 크롤링 때와 같은 지시문(extract_llm.SYSTEM)·같은 입력·같은 검증(verify)을 쓴다.
- 결과 → 화면 + backend/eval/effort_bench.md
"""
from __future__ import annotations

import argparse
import statistics as st
import time
from pathlib import Path

from ..config import settings
from ..crawler import verify as vf
from ..crawler.extract_llm import MAX_TEXT_CHARS, SYSTEM, sanitize_criteria
from ..db import SessionLocal
from ..models import Notice
from . import client

OUT = Path(__file__).resolve().parents[2] / "eval" / "effort_bench.md"
LEVELS = [("", "기본값"), ("low", "low")]


def pick(n: int) -> list[tuple[Notice, str]]:
    """실제(크롤링) 공지 중 글이 충분히 긴 최신 공지 n건 (본문 + 빈 양식이 아닌 첨부)"""
    out = []
    with SessionLocal() as db:
        rows = (db.query(Notice).filter(Notice.is_demo.is_(False))
                .order_by(Notice.posted_at.desc().nullslast(), Notice.id.desc()).limit(80).all())
        for x in rows:
            text = vf.extraction_source(x.body_text or "", [a.extracted_text for a in x.attachments if a.extracted_text])
            if len(text) >= 300:
                db.expunge(x)
                out.append((x, text[:MAX_TEXT_CHARS]))
            if len(out) == n:
                break
    return out


def run_once(n: Notice, body: str, effort: str, model: str) -> dict:
    posted = n.posted_at.strftime("%Y-%m-%d") if n.posted_at else "알 수 없음"
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"게시일: {posted}\n출처: {n.source_name}\n제목: {n.title}\n\n<공지>\n{body}\n</공지>"},
    ]
    t = time.perf_counter()
    out = client.chat(msgs, model, max_tokens=8000, timeout=180, json_mode=True, reasoning=effort)
    sec = time.perf_counter() - t
    u = dict(client.last_usage or {})
    think = client.think_tokens(u)
    try:
        data = client.parse_json(out)
        crit, dl, ev, rep = vf.verify(sanitize_criteria(data.get("criteria")), data.get("deadline"),
                                      data.get("evidence"), f"{n.title}\n{body}", n.posted_at)
        result = {"deadline": dl, **{k: crit.get(k) for k in rep.kept if k != "deadline"}}
        ok = True
    except client.LLMError:
        result, ok = {}, False
    return {"sec": sec, "in": u.get("prompt_tokens"), "out": u.get("completion_tokens"), "think": think,
            "usage": u, "result": result, "ok": ok}


def _avg(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return st.mean(xs) if xs else None


def _f(v, d=0):
    return "-" if v is None else f"{v:,.{d}f}"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--repeat", type=int, default=2)
    p.add_argument("--model", default=settings.chatkhu_model_extract)
    a = p.parse_args(argv)
    if not client.available():
        raise SystemExit("backend/.env 에 CHATKHU_API_KEY / CHATKHU_BASE_URL 이 필요해요.")
    notices = pick(a.n)
    if not notices:
        raise SystemExit("크롤링된 실제 공지가 없어요. live 모드로 크롤링부터: python -m app.crawler.run --limit 5")
    print(f"모델 {a.model} · 공지 {len(notices)}건 × {a.repeat}회 × 2(기본값/low) = AI 호출 {len(notices) * a.repeat * 2}번\n")

    runs: dict[str, list[dict]] = {lv: [] for lv, _ in LEVELS}
    per_notice = []
    for i, (n, body) in enumerate(notices, 1):
        print(f"[{i}] {n.title[:50]} ({len(body):,}자)")
        res = {lv: [] for lv, _ in LEVELS}
        for r in range(a.repeat):
            order = LEVELS if r % 2 == 0 else LEVELS[::-1]  # 순서 효과(서버 예열 등)를 줄이려고 번갈아
            for lv, name in order:
                try:
                    x = run_once(n, body, lv, a.model)
                except client.LLMError as e:
                    print(f"    {name}: 실패 {e}")
                    continue
                res[lv].append(x)
                runs[lv].append(x)
                print(f"    {name:4} {x['sec']:5.1f}초 · 입력 {_f(x['in'])} / 출력 {_f(x['out'])}"
                      + (f" (생각 {x['think']})" if x["think"] is not None else ""))
        same = bool(res[""] and res["low"]) and res[""][0]["result"] == res["low"][0]["result"]
        per_notice.append((n.title, res, same))
        if "reasoning_effort" in client._unsupported:
            print("\n게이트웨이가 reasoning_effort를 받지 않아요 → 비교 의미 없음. 중단합니다.")
            break

    lines = [f"# 생각 수준 비교 (모델 {a.model})", "",
             f"실제 공지 {len(per_notice)}건 × {a.repeat}회씩, 같은 지시문·입력·검증으로 추출", "",
             "| 설정 | 평균 시간 | 입력 토큰 | 출력 토큰 | 생각 토큰 | 출력+생각 (과금) |", "|---|---|---|---|---|---|"]
    summary = {}
    for lv, name in LEVELS:
        xs = runs[lv]
        s = {k: _avg([x[k] for x in xs]) for k in ("sec", "in", "out", "think")}
        s["bill"] = _avg([x["out"] + x["think"] for x in xs if x["out"] is not None and x["think"] is not None])
        summary[lv] = s
        lines.append(f"| {name} | {_f(s['sec'], 1)}초 | {_f(s['in'])} | {_f(s['out'])} | "
                     f"{_f(s['think']) if s['think'] is not None else '게이트웨이 미제공'} | {_f(s['bill'])} |")
    b, l = summary[""], summary["low"]
    lines.append("")
    for key, label in (("sec", "응답 시간"), ("out", "출력 토큰"), ("think", "생각 토큰"), ("bill", "출력+생각 토큰")):
        if b[key] and l[key] is not None:
            pct = (1 - l[key] / b[key]) * 100
            lines.append(f"- {label}: low가 {abs(pct):.0f}% {'적음' if pct >= 0 else '많음'}")
    if b["think"] is None and l["think"] is None:
        lines.append("- 게이트웨이가 Gemini의 생각 토큰 수를 알려 주지 않아 시간으로 비교했어요.")
    else:
        lines.append("- 생각 토큰 = total_tokens − 입력 − 출력 (게이트웨이가 따로 알려 주지 않을 때 계산)")
    n_same = sum(1 for *_, s in per_notice if s)
    lines.append(f"- 추출 결과(검증 후 마감일·조건) 같음: {n_same}/{len(per_notice)}건")
    lines += ["", "## 공지별", "", "| 공지 | 기본값 시간 | low 시간 | 결과 같음 |", "|---|---|---|---|"]
    for title, res, same in per_notice:
        lines.append(f"| {title[:40]} | {_f(_avg([x['sec'] for x in res['']]), 1)}초 | "
                     f"{_f(_avg([x['sec'] for x in res['low']]), 1)}초 | {'O' if same else 'X'} |")
    diff = [(t, r) for t, r, s in per_notice if not s and r[""] and r["low"]]
    if diff:
        lines += ["", "## 결과가 다른 공지 (첫 회 기준)"]
        for t, r in diff:
            lines += ["", f"- {t[:60]}", f"  - 기본값: {r[''][0]['result']}", f"  - low: {r['low'][0]['result']}"]
    first = next((x for xs in runs.values() for x in xs), None)
    if first:
        lines += ["", f"(참고: 게이트웨이 usage 원본 예시 `{first['usage']}`)"]

    text = "\n".join(lines)
    print("\n" + text)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text + "\n", encoding="utf-8")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
