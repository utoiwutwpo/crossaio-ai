"""
pytest 公共夹具
- 测试前设置独立 SQLite 测试库（D 盘项目内，不碰 C 盘）
- Mock 模式运行（不依赖任何外部 LLM API）
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DB = BACKEND_DIR / "tests" / "_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["JWT_SECRET"] = "test-secret"
# 测试环境强制 Google OAuth 视为未配置（真实凭据在 backend/.env，避免测试依赖外部 Google 服务）
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["LLM_API_KEY"] = ""  # 空值覆盖 .env 真实 Key，强制 Mock 模式（不依赖外部 LLM API）

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402


@pytest.fixture(scope="session")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def register_and_login(client: TestClient, email: str) -> dict:
    """注册并返回 {'headers': ..., 'user': ...}"""
    r = client.post("/api/v1/users/register", json={
        "email": email, "password": "Passw0rd!123",
    })
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
