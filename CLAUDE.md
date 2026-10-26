# Khuration — 경희대 공지 큐레이션 앱

경희대 학사·장학·공모전 공지를 수집해 학생 조건에 맞게 걸러주는 모바일 앱. 대회 시연용 MVP (스토어 출시 안 함).

## 구조
- /backend: FastAPI + SQLAlchemy (로컬 SQLite, 배포 Postgres)
- /app: Expo (React Native, TypeScript). UI는 Figma 디자인을 구현

## 절대 규칙
- 이름·학번·정확한 학점은 서버/DB에 저장하지 않는다. 서버는 푸시 토큰 + 익명 조건 태그만 받는다.
- 매칭은 코드가 한다. LLM은 공지에서 조건을 JSON으로 추출하는 용도로만 쓴다.
- 조건 판정은 일치/불일치/알 수 없음 3상태. 알 수 없음은 "확인 필요"로 노출한다.
- 로그인 없이 접근 가능한 공개 페이지만 크롤링한다. 요청 간 간격을 둔다.
- APP_MODE=demo|live. demo 전용 엔드포인트는 /demo/* 에만 두고 demo 모드에서만 등록한다.
- 키/토큰은 .env로만. 커밋 금지.
- 앱에서는 공지 원문을 복제하지 않고 요약+지원자격만 보여주고 원문은 링크로 이동. 학교 로고만 사용.

## 크롤링 대상
대표 홈페이지, 공과대학, 화학공학과, 현장실습, 국제교류처 (서울/국제 캠퍼스 모두). 하루 2회(14시, 20시 KST).
첨부: HWP/HWPX, PDF, 이미지(비전 모델로 읽기).

## LLM 조건 추출 스키마
{deadline, campuses[], colleges[], departments[], grades[], min_gpa, income_max,
 requires_lang_score, apply_url} — 모르면 null
- ChatKHU API 사용. 모델명/base_url은 env로 분리. 신뢰도 낮으면 고성능 모델로 재시도.

## 중복 알림
- (device, notice, kind, content_hash) 유니크. 제목/마감일/조건이 바뀌면 "변경됨" 알림 1회 추가.

## 작업 방식
- 기능 하나씩(시드/API → 크롤러 → 파서 → 추출 → 매칭 → 푸시) 구현하고 테스트 후 다음으로.
- 실행: cd backend && uvicorn app.main:app --reload --host 0.0.0.0
