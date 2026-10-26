# 크롤러 작업 규칙 (backend/app/crawler)

이 폴더에서 작업하는 사람(과 Claude Code)이 지킬 규칙. 루트 CLAUDE.md의 절대 규칙도 그대로 적용된다.

## 작업 범위
- 수정해도 되는 곳: `backend/app/crawler/adapters/`, `backend/tests/test_crawler_*.py`, `backend/tests/fixtures/crawler/`, `backend/scripts/`, 이 문서
- 건드리지 않는 곳: `web/`, `app/`, `backend/app/llm/`, `rag/`, `matching/`, `routers/`, `models.py`, `schemas.py`, `main.py`, `config.py`, `seed_loader.py`,
  `crawler/store.py`·`run.py`·`extract.py`·`extract_llm.py`·`base.py`, 루트 `CLAUDE.md`, `requirements.txt`
  - 모델/API를 바꿔야 하면 직접 고치지 말고 팀에 먼저 말한다 (앱과 계약이 깨짐)

## 흐름
```
어댑터.fetch_list → 어댑터.fetch_detail → parsers(첨부 텍스트) → extract(조건 JSON) → store.upsert_notice
```
- 실행: `python -m app.crawler.run --source <키> --limit 3 --dry-run` 으로 먼저 확인 → `--dry-run` 빼고 저장
- 저장은 반드시 `store.upsert_notice()`만 사용. Notice를 직접 만들거나 지우지 않는다.

## 어댑터 (게시판 하나 = 파일 하나)
- `adapters/_template.py`를 복사해서 만든다. 예: `adapters/engineering.py`
- `adapters/__init__.py`의 `ADAPTERS`에 짧은 키로 등록 (`"eng"`, `"chemeng"`, `"main"`, `"oia"`, `"aladdin"`)
  - 한 사이트에 게시판이 여럿이면 `main_academic`, `oia_outgoing`처럼 키를 나눈다
- 대상 5곳: 경희대 대표 홈페이지 공지, 공과대학, 화학공학과, 국제교류처, 알라딘 비교과 (서울·국제 캠퍼스 모두)
  - 현장실습 사이트는 로그인이 필요해서 제외 (알라딘 비교과로 대체)
- 학교 공통 CMS(`.../user/bbs/BMSR00040/list.do?menuNo=`)를 쓰는 게시판은 `adapters/khu_cms.py`의 `KhuCmsAdapter`를 상속해 사이트·menuNo만 바꾼다
- CSS 선택자는 추측하지 말고 실제 HTML을 보고 정한다. 사이트 구조가 바뀌면 그 어댑터만 고친다.
- `ListItem.url`은 상세 페이지 **절대 URL**이고 공지의 고유 키다. 페이지 번호·세션 같은 쿼리는 빼서 같은 공지가 늘 같은 URL이 되게 한다.
- `name`은 앱에 그대로 보이는 출처명이다 (예: "공과대학").

## 예의·법적 규칙
- 로그인 없이 보이는 공개 페이지만. 로그인·학번이 필요한 곳은 수집하지 않는다.
- HTTP는 반드시 `PoliteClient` 사용 (robots.txt 확인, 같은 사이트 요청 간 2초).
- 하루 2회(14시, 20시 KST) 실행 기준. 테스트할 때도 `--limit`을 작게.
- 원문 전체를 앱에 복제하지 않는다. 앱은 요약·지원 자격·원문 링크만 보여준다.

## 알라딘 요령 (aladdin.khu.ac.kr 교내비교과, 키 `aladdin`)
- 목록: `/portfolio/ptfol/imng/icmpNsbjtPgm/findIcmpNsbjtPgmList.do?sort=0001&paginationInfo.currentPageNo=N` (최신 등록순, 페이지당 10개)
  - 화면 주소에 `#`이 붙지만 목록은 JSON/AJAX가 아니라 이 HTML에 바로 들어 있다: `div.lica_wrap > ul > li`
- 상세: `findIcmpNsbjtPgmInfo.do?encSddpbSeq=<값>`. 값은 목록 항목 `a.detailBtn`의 `data-params`(JSON)에 있다
  - `encSddpbSeq`는 세션이 바뀌어도 같은 값이라 공지 고유 키로 쓴다. `paginationInfo.*`는 URL에서 뺀다
- SSO 확인: `ssoReChk=ok` 없이 요청하면 매번 sso.khu.ac.kr → `ksign/login_stand.jsp`(SsoChk.do 자동 제출)로 넘어갔다가
  같은 주소에 `ssoReChk=ok`를 붙여 돌아온다. 로그인 안 한 브라우저도 이 과정을 거쳐 같은 공개 화면을 본다
  - 그래서 **요청할 때만** `ssoReChk=ok`를 붙이고, 저장 URL(`ListItem.url`)에는 넣지 않는다
  - 로그인 쿠키는 쓰지 않는다. 응답 주소가 `/ksign/`이나 로그인 페이지(`login`, `SsoLogin`)면 그 자리에서 멈춘다 (`PermissionError`)
- 첨부(`/portfolio/common/cmnFile/download.do`)는 `ssoReChk=ok`를 붙여도 로그인 페이지(`ptfolSsoLogin.do`)로 간다 → 수집하지 않는다
  - `RawAttachment`로 넣으면 `run.py`가 내려받으려 하므로 넣지 않고, 파일 이름만 본문에 "첨부파일(로그인 필요)"로 남긴다
- 본문 이미지(`/portfolio/comm/cmfile/image.do?encSvrFileNm=`)는 로그인·`ssoReChk` 없이 열린다 → `image_urls`에 그대로. 한 장이 수 MB일 수 있다
- 게시일 칸이 없다 → 목록의 신청기간 시작일을 `posted_at`으로 쓴다
- 캠퍼스·신청대상·신청조건·신청학년은 목록 카드에만 있고 상세에는 없다 → 목록 카드 내용을 본문 앞에 붙인다 (조건 추출용)
- robots.txt 없음 (404)

## 목록 거르기·URL 규칙 (어댑터 공통)
- 게시일이 90일보다 오래된 글은 고정 글이어도 목록에서 뺀다 (`khu_cms.MAX_AGE_DAYS`, 알라딘은 신청 시작일 기준). 게시일을 모르면 남긴다
- robots.txt가 막는 경로(예: `com.khu.ac.kr/upload/`)의 본문 이미지는 `image_urls`에 넣지 않는다 (`drop_disallowed_images`, 판정은 `PoliteClient`)
- 공지 URL은 `adapters/urls.normalize_url`을 거친다: `ssoReChk`·세션·추적(utm 등)·페이지·검색 파라미터와 빈 값, `#조각`을 뺀다. 파라미터 순서는 바꾸지 않는다 (바꾸면 저장된 URL이 전부 달라져 중복 저장)
- 대표 홈페이지는 탭이 달라도 같은 `boardId`면 같은 글이라 상세 URL을 일반 탭(`menuNo=200316`)으로 통일한다. 국제교류처는 다른 menuNo로 열면 빈 화면이라 통일하지 않는다

## 테스트
- 오프라인: `tests/fixtures/crawler/<키>_list.html`, `<키>_view.html`, `manifest.json` (게시판마다 실제 HTML) → `tests/test_crawler_fixtures.py`
  - 사이트 구조가 바뀌어 픽스처를 새로 받으면 manifest.json의 `fixture_day`와 첫 글·상세 글 정보도 같이 바꾼다
- 실제 사이트 검사(게시판당 목록 1번 요청)는 평소 skip. 직접 확인할 때만 `backend`에서:
  `$env:KHU_LIVE='1'; .venv\Scripts\python.exe -m pytest -q tests/test_crawler_fixtures.py -k live`

## 자동 실행 (하루 2회, 14:00·20:00 KST)
- 스크립트: `backend/scripts/crawl.ps1` — 크롤링 1회(`run.py --limit 20`, 저장) 후 로그를 `backend/logs/YYYY-MM-DD.log`에 이어 붙인다
  - 로그는 `*.log`라 `.gitignore`에 이미 걸린다 (커밋 안 됨). 30일 지난 로그는 스크립트가 지운다
  - 시험: `backend` 폴더 위(레포 루트)에서 `powershell -NoProfile -ExecutionPolicy Bypass -File backend\scripts\crawl.ps1 -DryRun -Limit 1`
- 작업 스케줄러 등록 (크롤링을 돌릴 PC에서 PowerShell로 한 번만, `<레포>`는 Khuration 폴더 전체 경로):
  ```powershell
  $script = "<레포>\backend\scripts\crawl.ps1"
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
  $triggers = @((New-ScheduledTaskTrigger -Daily -At 14:00), (New-ScheduledTaskTrigger -Daily -At 20:00))
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
  Register-ScheduledTask -TaskName "Khuration Crawl" -Action $action -Trigger $triggers -Settings $settings -Description "Khuration 공지 크롤링 (14:00, 20:00)"
  ```
  - `-StartWhenAvailable`: PC가 꺼져 있어 놓친 실행은 켜진 뒤 한 번 돈다. 기본값은 "로그온했을 때만 실행"
  - PC 시간대가 한국 표준시(KST)여야 14:00·20:00이 KST다
- 확인·지금 한 번 돌리기·삭제:
  ```powershell
  Get-ScheduledTask -TaskName "Khuration Crawl" | Get-ScheduledTaskInfo   # 마지막 실행 시각, 결과(0 = 정상), 다음 실행
  Start-ScheduledTask -TaskName "Khuration Crawl"
  Unregister-ScheduledTask -TaskName "Khuration Crawl" -Confirm:$false
  ```

## 첨부 파싱 (parsers/) — 구현 완료, 크롤러 담당은 수정하지 않음
- `parse_attachment(data, filename)` → `ParseResult(text, method, needs_ocr, note)`. 형식은 매직 바이트로 판별
- HWP 5.0: 자체 구현(olefile + 레코드 해석). 배포용·암호 문서는 빈 텍스트 + note
- HWPX: zip 안 Contents/sectionN.xml. PDF: PyMuPDF, 페이지당 글자 40자 미만이면 스캔본(needs_ocr)
- 이미지·스캔본은 needs_ocr=True만 표시 (ChatKHU 비전 연결 후 처리)
- `run.py`의 `read_attachments()`가 첨부를 내려받아 자동으로 읽는다. 어댑터는 `RawAttachment` 링크만 채우면 됨
- 로컬 파일 시험: `python -m app.parsers 공고문.hwp`
- 실제 공고 파일을 `tests/fixtures/`에 넣으면 `test_real_fixtures_parse`가 자동 검사

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
