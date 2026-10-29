# KHURATION — 경희대 맞춤형 학사 정보 큐레이션 앱

> 흩어진 교내 공지를 모아, 나에게 맞는 것만 먼저.
> 팀 **아잉(Aing)** · AI 문제해결 솔루션 부문 · 작품 형태: 앱

학사·장학·공모전·현장실습·비교과 공지는 대표 홈페이지, 단과대·학과 게시판, 국제교류처, 알라딘 등 여러 곳에 흩어져 있습니다.
KHURATION은 이 게시판들을 자동으로 수집하고, AI가 공지에서 **지원 조건과 마감일을 원문 근거와 함께** 뽑은 뒤,
학생이 입력한 정보와 **코드로** 비교해 *지원 가능 / 확인 필요 / 조건 안 맞음*을 알려 줍니다.

## 주요 기능

| 화면 | 기능 |
|---|---|
| 정보 입력 | 학년·캠퍼스·학과·평균/직전 학점·취득 학점·소득분위·관심 분야·하고 싶은 활동(문장), 출생 연도(선택). 이름·정확한 학점은 폰에만 저장 |
| 홈 · AI 맞춤 공지 | 1순위 추천 공지와 추천 이유, 나에게 맞는 공지 목록 |
| 홈 · 마감 임박 | 마감 순 정렬, "지원 가능한 공지만" 보기 |
| 공지사항 | 9개 게시판 통합, 분류 칩·검색, 최신/마감 임박/AI 추천순 정렬 |
| 공지 상세 | AI 요약, 나와의 적합성(조건별 충족·확인 필요·미충족 + 원문 근거), 원문·신청 링크, 북마크 |
| 캘린더 · 체크리스트 | 월간 캘린더에 마감 저장, 공지별 준비 체크리스트, 마감 3일·1일 전 알림 설정, 폰 캘린더 저장(D-3 알림) |
| KHU AI | 질문하면 관련 공지를 찾아 판정과 함께 답함(출처 공지 표시), 대화 목록은 폰에만 저장 |
| 알림함 · 위젯 미리보기 | 저장한 공지 중 마감 3일 이내 알림, 홈 화면 위젯 모양 미리보기 |
| 시연 패널 (demo 모드) | 가상 시계 앞당기기, 마감 알림 보내 보기, 공지 변경 알림, 시연 공지 초기화 |

## 구조

```
backend/            FastAPI 서버 (Python, SQLAlchemy, SQLite / Postgres)
  app/main.py         서버 · /web/ 으로 앱 화면 제공 · /meta · 시작 시 자동 수집
  app/crawler/        게시판 수집(adapters/), AI 추출(extract_llm.py), 원문 근거 검증(verify.py),
                      저장(store.py), 자동 수집(auto.py), 정확도 측정(eval_extract.py)
  app/parsers/        첨부 읽기: HWP · HWPX · PDF · DOCX
  app/llm/            ChatKHU 호출(client.py), 포스터 OCR(ocr.py), KHU AI(chat.py)
  app/matching/       조건 판정(engine.py) — AI가 아니라 코드
  app/rag/            KHU AI 검색(한글 2글자 단위 BM25) · 답변 캐시
  app/routers/        feed · notices · devices · ai · demo API
  app/taxonomy.json   학과·분류·관심 분야 목록(단일 출처)
  seed/notices.json   시연용 가상 공지 25건 ([데모] 표기)
  scripts/crawl.ps1   하루 2회 자동 수집용 스크립트
  tests/              pytest (실제 게시판 HTML을 저장해 네트워크 없이 검사)
  eval/               자동 검증 통계 · 생각 수준 비교 결과
web/index.html      앱 화면 전체 (HTML/CSS/JS 한 파일)
app/                Expo Go 껍데기 — WebView로 /web/ 를 띄우고 원문 링크·폰 캘린더 연동
```

## 실행 방법

필요한 것: Python 3.11 이상, Node.js(앱을 폰으로 볼 때), Git

### 1. 서버

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # 필요한 값만 채우기 (아래 참고)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000/web/` 을 열면 앱 화면이 나옵니다.
서버 없이 화면만 보려면 `web/index.html` 파일을 더블클릭해 열면 됩니다 (자동으로 목업 데이터, 서버 주소로 열 때는 `?mock=1`).

`.env` 주요 값 (`backend/.env.example` 참고, 키는 커밋하지 않음)

| 값 | 설명 |
|---|---|
| `APP_MODE` | `demo`: 시연용 [데모] 공지 + 시연 패널 / `live`: 실제 수집한 공지만 |
| `CHATKHU_API_KEY`, `CHATKHU_BASE_URL` | AI 추출·OCR·KHU AI 답변용. 비우면 규칙 기반으로 자동 전환 |
| `CHATKHU_MODEL_*` | 용도별 모델 (추출 · 상위 재추출 · 이미지 · 대화 · 연결 테스트) |
| `AUTO_CRAWL` | live 모드에서 서버를 켤 때 마지막 수집이 오래됐으면 자동 수집 |

### 2. 공지 수집

```powershell
cd backend
python -m app.crawler.run --list                      # 게시판 목록
python -m app.crawler.run --source eng --limit 3 --dry-run   # 저장 없이 확인
python -m app.crawler.run --limit 5                   # 수집 후 저장
```

### 3. 폰에서 보기 (Expo Go)

```powershell
cd app
npm install
# app/.env 에 EXPO_PUBLIC_API_BASE_URL=http://<PC의 IP>:8000
npx expo start
```

### 4. 테스트 · 측정

```powershell
cd backend
python -m pytest -q                          # 실제 사이트 접속 검사는 기본 skip
python -m app.crawler.eval_extract stats     # 자동 검증 통계 (추가 크레딧 없음)
```

## 정확도 원칙

AI는 조건마다 **원문 근거 문장**을 함께 내고, 코드가 그 문장이 원문에 실제로 있는지(85% 유사 허용),
근거 안에 그 값이 들어 있는지, 마감일이 원문 날짜 후보와 맞는지 검사합니다.
확인 못 한 값은 상위 모델로 한 번 더 추출하고, 그래도 불확실하면 비워 둡니다(앱에서 '확인 필요').
**틀린 조건을 확정하는 것을 가장 위험한 오류로 보고 정밀도를 우선합니다.** 자격 판정은 AI가 아니라 `matching/engine.py`가 합니다.

자동 검증 결과(`backend/eval/stats.md`, 실제 공지 54건): AI가 낸 값 118개 중 106개 원문 근거 확인, 12개 자동 차단,
상위 모델 재추출 11건 → 최종 110개, 마감일 36/36 원문 일치. (근거 확인률이며 정답률은 아닙니다.)

## 개인정보

- 이름·학번·정확한 학점·출생 연도는 **폰에만** 저장합니다. 서버는 익명 기기 토큰과 구간화한 조건 태그(예: 학점 0.5 단위 내림)만 받습니다.
- 출생 연도 조건은 서버가 공지 쪽 조건만 내려 주고 앱이 폰 안에서 판정합니다.
- KHU AI에는 질문·관심 분야 이름·공지 내용만 보내고, 질문 원문은 저장하지 않습니다(캐시 키는 해시).
- 앱의 '내 데이터 삭제'로 서버의 태그도 지웁니다.

## 수집 원칙

로그인 없이 공개된 페이지만, `robots.txt` 확인, 같은 사이트 요청 간격 2초 이상, 공지 원문은 앱에 복제하지 않고 요약·지원 자격·원문 링크만 보여 줍니다.
수집 대상: 경희대 대표 홈페이지(일반·학사·장학·근로), 공과대학, 화학공학과, 국제교류처(공지·파견), 알라딘 교내비교과.

## 라이선스 참고

사용한 오픈소스는 MIT · BSD · Apache-2.0 · LGPL 라이선스이며, PDF 읽기에 쓰는 **PyMuPDF는 AGPL-3.0 또는 상용(이중 라이선스)** 입니다.
앱 첫 화면의 경희대학교 사자 심볼은 경희대학교의 저작물입니다.
