# Khuration — 경희대 공지 큐레이션 앱

경희대 학사·장학·공모전 공지를 수집해 학생 조건에 맞게 걸러주는 모바일 앱. 대회 시연용 MVP (스토어 출시 안 함).

## 구조
- /backend: FastAPI + SQLAlchemy (로컬 SQLite, 배포 Postgres)
- /web/index.html: 앱 화면 전체 (HTML/CSS/JS 한 파일). 디자인 기준은 이 HTML이다 (Figma 시안은 더 이상 기준 아님)
  - 백엔드가 `/web/` 으로 내려준다 (backend/app/main.py). 폰 브라우저로 `http://<PC IP>:8000/web/` 을 열어도 된다
  - `?mock=1` 을 붙이면 서버 없이 목업 데이터로 동작 (화면 확인용)
- /app: Expo Go 껍데기. `src/app/index.tsx` 가 WebView로 `/web/` 을 띄우고, 원문·신청 링크는 기기 브라우저로 연다
  - 서버 주소는 `app/.env` 의 `EXPO_PUBLIC_API_BASE_URL` 한 곳에서만 바꾼다
  - 예전 Expo 화면(src/app/onboarding.tsx, (tabs)/ 등)은 팀 결정 전까지 지우지 않는다

## 절대 규칙
- 이름·학번·정확한 학점은 서버/DB에 저장하지 않는다. 서버는 푸시 토큰 + 익명 조건 태그만 받는다.
- 매칭(지원 자격 판정)은 코드가 한다(`matching/engine.py`). LLM은 판정하지 않는다. LLM 용도는 세 가지뿐:
  1) 공지 → 조건·마감일·요약 JSON 추출(`crawler/extract_llm.py`) 2) 이미지·스캔 PDF 글자 읽기(`llm/ocr.py`)
  3) KHU AI 답변 문장 쓰기(`llm/chat.py`, 검색으로 찾은 근거와 코드가 낸 판정만 보고 쓴다)
- 조건 판정은 일치/불일치/알 수 없음 3상태. 알 수 없음은 "확인 필요"로 노출한다.
  - 조건이 하나도 없는 공지는 "확인 필요"다(조건을 못 찾은 것과 조건이 없는 것은 다르다).
    공지에 "누구나/제한 없음"이 명시돼 `criteria.open_to_all=true`일 때만 "지원 가능".
- 로그인 없이 접근 가능한 공개 페이지만 크롤링한다. 요청 간 간격을 둔다.
- APP_MODE=demo|live. demo 전용 엔드포인트는 /demo/* 에만 두고 demo 모드에서만 등록한다.
  - live는 크롤링 공지(is_demo=False)만, demo는 시연 공지(is_demo=True, 시드)만 보여준다 (`routers/feed.py`의 `visible_notices`)
  - demo 모드면 앱 홈 상단 시계 버튼 → 시연 패널(시계 앞당기기·알림 보내 보기·공지 변경·시연 공지 초기화)
  - 앱의 D-day·마감 알림은 서버 `/health`의 `today`(시연 시계 반영) 기준으로 계산한다
- 키/토큰은 .env로만. 커밋 금지.
- 앱에서는 공지 원문을 복제하지 않고 요약+지원자격만 보여주고 원문은 링크로 이동. 학교 로고만 사용.

## 크롤링 대상
대표 홈페이지, 공과대학, 화학공학과, 알라딘(aladdin.khu.ac.kr), 국제교류처. 현장실습은 로그인이 필요해 제외. 하루 2회(14시, 20시 KST).
첨부: HWP/HWPX, DOCX, PDF, 이미지(비전 모델로 읽기). 본문 포스터 이미지도 OCR해서 저장(글자를 읽은 것만).

## LLM 조건 추출 스키마
{deadline, campuses[], colleges[], departments[], grades[], min_gpa, gpa_basis, min_credits, income_max,
 requires_lang_score, open_to_all, apply_url} — 모르면 null (추측 금지)
- ChatKHU API(OpenAI 호환). 키·base_url·모델명은 backend/.env로 분리 (CHATKHU_MODEL_EXTRACT/VISION/CHAT).
- TODO: 신뢰도 낮으면 고성능 모델로 재시도 (아직 없음).

## KHU AI 검색(RAG)
- `app/rag/index.py`: 공지(요약·체크리스트·본문·첨부·포스터 OCR) → 500자 조각 → 키워드(BM25, 한글 2글자 단위) 검색.
  내용이 바뀐 공지만 다시 자르고, 메모리 색인은 조각이 바뀔 때만 다시 만든다. 마감 지난 공지는 검색 제외.
- `app/rag/cache.py`: 답변 캐시 6시간. 키는 (질문+조건 태그+색인 버전+날짜+모델) 해시 → 질문 원문 미저장.
- LLM에는 질문, 관심 분야 이름, 찾은 조각, 공지 제목·마감·판정만 보낸다(조건 태그 값은 보내지 않는다).

## 중복 알림
- (device, notice, kind, content_hash) 유니크. 제목/마감일/조건이 바뀌면 "변경됨" 알림 1회 추가.

## 작업 방식
- 기능 하나씩(시드/API → 크롤러 → 파서 → 추출 → 매칭 → 푸시) 구현하고 테스트 후 다음으로.
- 실행: cd backend && uvicorn app.main:app --reload --host 0.0.0.0

## 앱 ↔ 서버 계약 (web/index.html 기준)
화면 코드는 `window.KhuApi` 만 부른다. 서버용 구현은 index.html 안의 "KHURATION API 클라이언트 — 우리 FastAPI 서버용" 스크립트.
앱(기기 localStorage)에만 저장: 이름, 정확한 평균 학점/직전 평점/취득 학점, '하고 싶은 활동' 원문,
북마크, 캘린더에 저장한 공지, 체크리스트, 마감 알림 설정, KHU AI 대화 기록.
기기 토큰은 `web-<uuid>` (Expo 푸시 토큰 아님 → 원격 푸시 없음. 시연 알림은 앱 안 종 아이콘: 저장한 공지 중 마감 3일 이내).
서버로 보내는 태그 (`POST /devices`, 헤더 없이 body로 push_token + tags):
- campus: "seoul" | "global"
- college, dept: 학과 선택 값 (college는 선택)
- grade: 1~6
- gpa_floor / last_gpa_floor: 0.5 단위 내림 (3.87 → 3.5, 4.02 → 4.0)
- credits_floor: 10 단위 내림 (78 → 70)
- income_band: 1~10
- interests: dev_it, ai_data, design, scholarship, startup, language_abroad, internship
- has_lang_score: 선택 (지금 HTML 온보딩에는 없어서 생략 → 어학 필요 공지는 "확인 필요")
이후 모든 호출은 헤더 `X-Device-Token: <push_token>`.
- `POST /devices/intent` {text}: 문장 → 키워드만 저장, 원문 미저장
- `GET /health`: 모드·오늘 날짜(시연 시계 반영)
- `GET /feed`: 일치 → 확인 필요 순 (불일치는 `?include_mismatch=true`)
- `GET /notices?q=&category=&sort=latest|deadline|ai`: 공지사항 탭 (헤더 있으면 판정 포함)
- `GET /notices/{id}`: 요약·지원 자격·원문 링크
- `POST /ai/chat` {message}: KHU AI. 응답 {answer, items, sources, evidence[{notice_id,title,snippet}], engine, cached}
- `DELETE /devices`: 내 데이터 삭제
- demo 전용: `/demo/advance-clock`, `/demo/reset-clock`, `/demo/reseed`, `/demo/change-notice`, `/demo/fire-push`
- 시드 공지 제목은 `[데모]`로 시작하며 url은 example.com 플레이스홀더. 실제 공지로 오인되게 하지 않는다.

## 크롤러
- 크롤러·첨부 파싱 작업 규칙은 `backend/app/crawler/CLAUDE.md`를 따른다.
- 크롤러는 `crawler/store.upsert_notice()`로만 저장한다. 시드 공지는 `is_demo=True`, 크롤링 공지는 `is_demo=False`.
