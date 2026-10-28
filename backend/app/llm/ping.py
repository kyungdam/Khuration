"""ChatKHU 연결 테스트.

    python -m app.llm.ping                      # 텍스트 + JSON 테스트
    python -m app.llm.ping 이미지파일.png        # + 이미지 읽기 테스트
    python -m app.llm.ping 이미지파일.png --models gemini-3.8-flash gemini-3.5-flash
    python -m app.llm.ping --effort ""                # 생각 토큰 비교: 모델 기본값 vs 기본(low)
"""
import mimetypes
import sys
import time
from pathlib import Path

from ..config import settings
from . import client


def _run(name, fn):
    t = time.time()
    try:
        out = fn()
        u = client.last_usage or {}
        think = client.think_tokens(u)
        tok = f" · 토큰 입력 {u.get('prompt_tokens', '?')} / 출력 {u.get('completion_tokens', '?')}" + (f" (생각 {think})" if think is not None else "")
        print(f"  OK  {name} ({time.time() - t:.1f}s{tok})\n      {str(out)[:300]!r}")
        return True
    except client.LLMError as e:
        print(f"  FAIL {name}: {e}")
        return False


def main(argv):
    if not client.available():
        print(".env 에 CHATKHU_API_KEY / CHATKHU_BASE_URL 이 없습니다.")
        return 1
    if "--effort" in argv:  # 생각 토큰 비교용: --effort low / --effort "" (모델 기본값)
        i = argv.index("--effort")
        settings.chatkhu_reasoning_effort = argv[i + 1] if i + 1 < len(argv) else ""
        argv = argv[:i] + argv[i + 2 :]
    print("생각 수준(reasoning_effort):", settings.chatkhu_reasoning_effort or "(모델 기본값)")
    models = None
    if "--models" in argv:
        i = argv.index("--models")
        models, argv = argv[i + 1 :], argv[:i]
    image = Path(argv[0]) if argv else None
    models = models or sorted(
        {
            settings.chatkhu_model_extract,
            settings.chatkhu_model_vision,
            settings.chatkhu_model_chat,
            settings.chatkhu_model_dev,
        }
    )
    print("Base URL:", settings.chatkhu_base_url)
    for m in models:
        print(f"\n[{m}]")
        _run(
            "텍스트",
            lambda: client.chat([{"role": "user", "content": "한 문장으로 인사해 줘."}], m, max_tokens=500),
        )
        _run(
            "JSON",
            lambda: client.parse_json(
                client.chat(
                    [
                        {
                            "role": "user",
                            "content": '다음 문장에서 JSON만 출력: {"deadline":"YYYY-MM-DD","min_gpa":number}\n'
                            "문장: 신청 마감은 2026년 11월 9일이며 평점 3.0 이상만 지원 가능합니다.",
                        }
                    ],
                    m,
                )
            ),
        )
        if image:
            mime = mimetypes.guess_type(image.name)[0] or "image/png"
            _run(
                "이미지",
                lambda: client.chat(
                    [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "이 이미지의 글자를 그대로 읽어서 적어 줘."},
                                client.image_part(image.read_bytes(), mime),
                            ],
                        }
                    ],
                    m,
                    max_tokens=4000,
                ),
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
