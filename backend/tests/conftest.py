import os
from pathlib import Path

os.environ["APP_MODE"] = "demo"
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
Path("test_api.db").unlink(missing_ok=True)
