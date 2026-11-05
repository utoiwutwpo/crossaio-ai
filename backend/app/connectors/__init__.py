"""统一连接器适配器框架 — 全平台实时同步 P1。

注册表 REGISTRY：每个平台一条目 {module, display_name, state, reason}。
  state = "active"  真实可用（当前仅 eBay）
  state = "pending" 骨架就绪、待凭据/待实现 —— 诚实状态，不伪装成功。

用法：
  from app.connectors import get_connector, connector_states
  ad = get_connector("ebay")
  msgs = await ad.fetch_buyer_messages(user)
"""
from typing import Dict, List

from .base import ConnectorAdapter, NotConfiguredError  # noqa: F401
from .ebay import EbayConnector
from .allegro import AllegroConnector
from .otto import OttoConnector
from .cdiscount import CdiscountConnector
from .emag import EmagConnector
from .bol import BolConnector
from .kaufland import KauflandConnector
from .zalando import ZalandoConnector

REGISTRY: Dict[str, Dict[str, str]] = {
    "ebay": {
        "module": "ebay",
        "display_name": "eBay",
        "state": "active",
        "reason": "eBay OAuth 实时消息同步已接入",
    },
    "allegro": {
        "module": "allegro",
        "display_name": "Allegro",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 Allegro API 凭证）",
    },
    "otto": {
        "module": "otto",
        "display_name": "Otto Market",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 Otto Market API 凭证）",
    },
    "cdiscount": {
        "module": "cdiscount",
        "display_name": "Cdiscount",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 Cdiscount API 凭证）",
    },
    "emag": {
        "module": "emag",
        "display_name": "eMAG",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 eMAG Marketplace API 凭证）",
    },
    "bol": {
        "module": "bol",
        "display_name": "bol.com",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 bol.com 零售者 API 凭证）",
    },
    "kaufland": {
        "module": "kaufland",
        "display_name": "Kaufland",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 Kaufland Marketplace API 凭证）",
    },
    "zalando": {
        "module": "zalando",
        "display_name": "Zalando",
        "state": "pending",
        "reason": "待凭据启用（本地未配置 Zalando Partner API 凭证）",
    },
}

_ADAPTER_CLASSES: Dict[str, type] = {
    "ebay": EbayConnector,
    "allegro": AllegroConnector,
    "otto": OttoConnector,
    "cdiscount": CdiscountConnector,
    "emag": EmagConnector,
    "bol": BolConnector,
    "kaufland": KauflandConnector,
    "zalando": ZalandoConnector,
}


def get_connector(platform: str) -> ConnectorAdapter:
    """按平台名返回适配器实例。未知平台抛 KeyError（诚实，不兜底伪造）。"""
    if platform not in REGISTRY:
        raise KeyError(f"未知平台连接器: {platform}（已注册: {sorted(REGISTRY)}）")
    return _ADAPTER_CLASSES[platform]()


def connector_states() -> List[Dict[str, str]]:
    """返回全部平台状态矩阵（供 API 与工作台状态矩阵只读引用）。"""
    return [
        {"platform": p, "state": info["state"], "reason": info["reason"]}
        for p, info in REGISTRY.items()
    ]
