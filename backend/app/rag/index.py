"""공지 → 조각 색인 + 키워드(BM25) 검색.

캐시 3단계
1. DB 조각(notice_chunks): 공지 내용 해시(source_hash)가 그대로면 다시 자르지 않는다.
2. 메모리 색인(_INDEX): 조각 버전(개수·최대 id·해시 합)이 그대로면 다시 짓지 않는다.
3. 답변 캐시는 cache.py.

한국어는 형태소 분석기 없이 2글자 단위(바이그램)로 쪼갠다. '인정돼' / '인정됩니다' 가 '인정'으로 맞는다.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from .. import clock
from ..models import Notice, NoticeChunk

CHUNK_CHARS = 500
OVERLAP_CHARS = 100
K1, B = 1.5, 0.75
TITLE_BOOST = 2  # 제목 토큰은 조각마다 이만큼 더 센다


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for w in re.findall(r"[0-9a-z]+|[가-힣]+", text.lower()):
        if "가" <= w[0] <= "힣" and len(w) > 1:
            out += [w[i : i + 2] for i in range(len(w) - 1)]
        else:
            out.append(w)
    return out


def doc_text(n: Notice) -> str:
    """검색에 쓰는 공지 글: 요약·체크리스트·본문·첨부(이미지 OCR 포함)."""
    parts = [n.summary or "", *(n.summary_points or []), *(n.checklist or []), n.body_text or ""]
    parts += [a.extracted_text for a in n.attachments if a.extracted_text]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def split_chunks(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        while len(p) > CHUNK_CHARS:  # 아주 긴 문단은 잘라서
            head, p = p[:CHUNK_CHARS], p[CHUNK_CHARS - OVERLAP_CHARS :]
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(head)
        if len(cur) + len(p) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = cur[-OVERLAP_CHARS:] + "\n" + p
        else:
            cur = f"{cur}\n{p}" if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def sync(db: Session) -> int:
    """바뀐 공지만 조각을 다시 만든다. 다시 만든 공지 수를 돌려준다."""
    notices = db.query(Notice).options(selectinload(Notice.attachments)).all()
    have = dict(db.query(NoticeChunk.notice_id, NoticeChunk.source_hash).distinct().all())
    changed = 0
    alive = set()
    for n in notices:
        alive.add(n.id)
        text = doc_text(n)
        h = hashlib.sha256(f"{n.title}\n{text}".encode()).hexdigest()
        if have.get(n.id) == h:
            continue
        db.query(NoticeChunk).filter_by(notice_id=n.id).delete()
        for i, c in enumerate(split_chunks(text) or [""]):
            db.add(NoticeChunk(notice_id=n.id, seq=i, text=c, source_hash=h))
        changed += 1
    gone = set(have) - alive
    if gone:
        db.query(NoticeChunk).filter(NoticeChunk.notice_id.in_(gone)).delete(synchronize_session=False)
    if changed or gone:
        db.commit()
    return changed


@dataclass
class Hit:
    notice_id: int
    title: str
    text: str
    score: float
    coverage: float  # 질문 토큰 중 이 조각(제목 포함)에 있는 비율


class _Index:
    def __init__(self, version: tuple, rows: list[tuple[int, str, str]]):
        self.version = version
        self.rows = rows  # (notice_id, title, text)
        self.tf: list[Counter] = []
        self.df: Counter = Counter()
        for _, title, text in rows:
            c = Counter(tokens(text))
            for t in tokens(title):
                c[t] += TITLE_BOOST
            self.tf.append(c)
            self.df.update(c.keys())
        self.n = len(rows)
        self.avgdl = (sum(sum(c.values()) for c in self.tf) / self.n) if self.n else 0.0

    def search(self, query: str, k: int, allowed: set[int] | None) -> list[Hit]:
        q = list(dict.fromkeys(tokens(query)))
        if not q or not self.n:
            return []
        hits: list[Hit] = []
        for i, c in enumerate(self.tf):
            nid, title, text = self.rows[i]
            if allowed is not None and nid not in allowed:
                continue
            dl = sum(c.values()) or 1
            score = 0.0
            present = 0
            for t in q:
                f = c.get(t, 0)
                if not f:
                    continue
                present += 1
                idf = math.log(1 + (self.n - self.df[t] + 0.5) / (self.df[t] + 0.5))
                score += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avgdl))
            if score > 0:
                hits.append(Hit(nid, title, text, score, present / len(q)))
        hits.sort(key=lambda h: h.score, reverse=True)
        out: list[Hit] = []
        per: Counter = Counter()
        for h in hits:  # 한 공지에서 최대 2조각
            if per[h.notice_id] >= 2:
                continue
            per[h.notice_id] += 1
            out.append(h)
            if len(out) >= k:
                break
        return out


_INDEX: _Index | None = None


def version(db: Session) -> tuple:
    cnt, mx = db.query(func.count(NoticeChunk.id), func.max(NoticeChunk.id)).one()
    return (cnt or 0, mx or 0)


def get_index(db: Session) -> _Index:
    global _INDEX
    sync(db)
    v = version(db)
    if _INDEX is None or _INDEX.version != v:
        rows = (
            db.query(NoticeChunk.notice_id, Notice.title, NoticeChunk.text)
            .join(Notice, Notice.id == NoticeChunk.notice_id)
            .order_by(NoticeChunk.id)
            .all()
        )
        _INDEX = _Index(v, [tuple(r) for r in rows])
    return _INDEX


def search(db: Session, query: str, k: int = 5, include_expired: bool = False, min_coverage: float = 0.34) -> list[Hit]:
    idx = get_index(db)
    allowed = None
    if not include_expired:
        now = clock.now()
        allowed = {nid for (nid,) in db.query(Notice.id).filter((Notice.deadline.is_(None)) | (Notice.deadline >= now))}
    return [h for h in idx.search(query, k * 3, allowed) if h.coverage >= min_coverage][:k]
