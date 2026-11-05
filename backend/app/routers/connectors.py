"""连接器状态路由 — GET /connectors（公开只读，无需登录）。

由 main.py 以 prefix="/api/v1/platforms" 挂载后，完整路径为：
    GET /api/v1/platforms/connectors

契约：
    {"connectors": [
        {"platform": "ebay",      "state": "active",  "reason": ""},
        {"platform": "allegro",   "state": "pending", "reason": "待凭据启用（本地未配置 Allegro API 凭证）"},
        ...
    ]}
"""
from fastapi import APIRouter

from ..connectors import connector_states

router = APIRouter()


@router.get("/connectors", summary="全平台连接器状态矩阵")
def list_connectors() -> dict:
    return {"connectors": connector_states()}
