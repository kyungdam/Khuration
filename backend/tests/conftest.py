import os
from pathlib import Path

os.environ["APP_MODE"] = "demo"
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
# 테스트는 실제 ChatKHU를 부르지 않는다 (크레딧·네트워크). .env 에 키가 있어도 환경변수가 우선.
os.environ["CHATKHU_API_KEY"] = ""
os.environ["CHATKHU_BASE_URL"] = ""
Path("test_api.db").unlink(missing_ok=True)
