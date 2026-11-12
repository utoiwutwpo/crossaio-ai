"""真实连通性探测：发一次真请求，按结果给 live 判定。

与"填了字段就算 connected"不同，这里必须拿到 2xx 才返回 live=True；
401/403 归 auth，网络错误归 unreachable，缺凭证归 not_connected。
"""
from .channels.base import CapabilityNotSupported
from .channels.registry import adapter_for


async def probe_platform(platform: str, payload: dict | None) -> dict:
    payload = payload or {}
    if not payload:
        return {"platform": platform, "live": False, "status": "not_connected",
                "hint": "先保存该平台凭证，再做真连通探测"}
    adapter = adapter_for(platform, payload)
    try:
        orders = await adapter.fetch_orders()
        return {"platform": platform, "live": True, "status": "connected",
                "probe": "read_orders", "orders_preview": len(orders),
                "base_url": getattr(adapter, "_base", lambda: "")()}
    except CapabilityNotSupported as e:
        return {"platform": platform, "live": False, "status": e.reason,
                "hint": e.fix_hint, "action": e.action}
    except Exception as e:      # 网络/解析异常也算未连通，但要暴露真实类型
        return {"platform": platform, "live": False, "status": "unreachable",
                "hint": f"{type(e).__name__}: {str(e)[:120]}"}
