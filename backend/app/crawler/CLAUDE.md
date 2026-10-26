# 크롤러 작업 규칙 (backend/app/crawler, backend/app/parsers)

이 폴더에서 작업하는 사람(과 Claude Code)이 지킬 규칙. 루트 CLAUDE.md의 절대 규칙도 그대로 적용된다.

## 작업 범위
- 수정해도 되는 곳: `backend/app/crawler/`, `backend/app/parsers/`, `backend/tests/test_crawler*.py`, `backend/requirements.txt`(의존성 추가만)
- 건드리지 않는 곳: `app/`(앱 화면), `backend/app/models.py`, `routers/`, `matching/`, `schemas.py`
  - 모델/API를 바꿔야 하면 직접 고치지 말고 팀에 먼저 말한다 (앱과 계약이 깨짐)

## 흐름
```
어댑터.fetch_list → 어댑터.fetch_detail → parsers(첨부 텍스트) → extract(조건 JSON) → store.upsert_notice
```
- 실행: `python -m app.crawler.run --source <키> --limit 3 --dry-run` 으로 먼저 확인 → `--dry-run` 빼고 저장
- 저장은 반드시 `store.upsert_notice()`만 사용. Notice를 직접 만들거나 지우지 않는다.

## 어댑터 (게시판 하나 = 파일 하나)
- `adapters/_template.py`를 복사해서 만든다. 예: `adapters/engineering.py`
- `adapters/__init__.py`의 `ADAPTERS`에 짧은 키로 등록 (`"eng"`, `"chemeng"`, `"main"`, `"intern"`, `"oia"`)
- 대상 5곳: 경희대 대표 홈페이지 공지, 공과대학, 화학공학과, 현장실습, 국제교류처 (서울·국제 캠퍼스 모두)
- CSS 선택자는 추측하지 말고 실제 HTML을 보고 정한다. 사이트 구조가 바뀌면 그 어댑터만 고친다.
- `ListItem.url`은 상세 페이지 **절대 URL**이고 공지의 고유 키다. 페이지 번호·세션 같은 쿼리는 빼서 같은 공지가 늘 같은 URL이 되게 한다.
- `name`은 앱에 그대로 보이는 출처명이다 (예: "공과대학").

## 예의·법적 규칙
- 로그인 없이 보이는 공개 페이지만. 로그인·학번이 필요한 곳은 수집하지 않는다.
- HTTP는 반드시 `PoliteClient` 사용 (robots.txt 확인, 같은 사이트 요청 간 2초).
- 하루 2회(14시, 20시 KST) 실행 기준. 테스트할 때도 `--limit`을 작게.
- 원문 전체를 앱에 복제하지 않는다. 앱은 요약·지원 자격·원문 링크만 보여준다.

## 첨부 파싱 (parsers/)
- 함수 하나 = 형식 하나: `parsers/hwp.py`(`hwp5txt`, 실패 시 HWPX는 zip 안 XML), `parsers/pdf.py`(PyMuPDF/pdfplumber), `parsers/image.py`(비전 모델)
- 시그니처: `def extract_text(data: bytes, filename: str) -> str` — 실패하면 예외 대신 빈 문자열
- 텍스트가 거의 없는 PDF는 스캔본으로 보고 이미지 경로로 넘긴다
- 결과는 `run.py`의 `attachment_texts[url] = text` 로 넘겨 저장한다

## 조건 추출 (extract.py)
- 출력은 `EMPTY_CRITERIA`와 같은 키. 공지에 없는 조건은 None/[] (추측 금지 — 앱이 "확인 필요"로 보여준다)
- 마감일 `deadline`은 KST 23:59를 naive UTC로 변환해 넣는다 (`app.clock.kst_deadline` 참고)
- `category`는 장학|현장실습|국제교류|공모전|근로|취업|비교과|학사 중 하나
- `topics`는 dev_it, ai_data, design, scholarship, startup, language_abroad, internship 중에서
- ChatKHU 연결: `extract_with_llm` 구현 → 실패하면 `extract_rule_based`로 폴백. 키/주소는 `.env`의 `CHATKHU_API_KEY`, `CHATKHU_BASE_URL`
- LLM은 조건을 뽑기만 한다. 학생 정보와 대조하는 건 `matching/engine.py`.

## 변경 감지
- `upsert_notice`가 `"new" | "changed" | "same"`을 돌려준다 (제목·마감일·조건 해시 비교)
- `changed`는 "공지가 변경됐어요" 알림 대상. 해시에 본문 전체는 넣지 않는다 (오타 수정마다 알림이 가지 않게)

## 완료 기준
- `python -m pytest -q` 전부 통과 (크롤러 테스트 포함)
- 각 어댑터를 `--dry-run --limit 3`으로 돌린 출력이 정상
- 어댑터마다 저장된 HTML 샘플로 테스트 하나씩 (네트워크 없이 도는 테스트) 권장
