"""统一平台接入串联层 — 一次授权，全站复用。

所有功能（产品描述/客服/广告/差评/Listing 监控）不再各自判断"有没有凭证"，
统一调 get_connected_platforms() 获取已接入平台集合，自动解锁对应平台能力。

数据源：
  - eBayConnection 表（OAuth 授权，token 自动刷新）
  - PlatformCredential 表（自助粘贴 API 凭证，AES-256 加密）
"""
from typing import Set, Dict, List
from sqlalchemy.orm import Session

from .database import eBayConnection, PlatformCredential
from .experts.platform_credentials import PLATFORM_CRED_REGISTRY, cred_guide


def get_connected_platforms(db: Session, user_id: str) -> Set[str]:
    """返回当前用户已接入的平台集合（eBay OAuth + 自助凭证合并）。

    所有功能入口统一调此函数：
        connected = get_connected_platforms(db, user.id)
        if "ebay" in connected:
            # 解锁 eBay 消息实时同步 + AI 回复直发
    """
    creds = {r.platform for r in
             db.query(PlatformCredential.platform)
             .filter(PlatformCredential.user_id == user_id).all()}
    if db.query(eBayConnection).filter(
            eBayConnection.user_id == user_id).first():
        creds.add("ebay")
    return creds


def get_platform_unlocks(platform: str) -> Dict:
    """返回该平台接入后解锁的功能说明（用于前端展示）。"""
    guide = cred_guide(platform)
    if not guide:
        return {}
    return {
        "label": guide["label"],
        "unlocks": guide["unlocks"],
        "oauth": guide.get("oauth", False),
        "apply_url": guide["apply_url"],
    }


def list_all_platforms_status(db: Session, user_id: str) -> List[Dict]:
    """列出全部 12 平台的接入状态（用于凭证中心渲染）。"""
    connected = get_connected_platforms(db, user_id)
    result = []
    for pkey, cfg in PLATFORM_CRED_REGISTRY.items():
        result.append({
            "platform": pkey,
            "label": cfg["label"],
            "connected": pkey in connected,
            "oauth": cfg.get("oauth", False),
            "apply_url": cfg["apply_url"],
            "apply_note": cfg["apply_note"],
            "fields": [{"key": k, "label": l, "secret": s, "hint": h}
                       for k, l, s, h in cfg["fields"]],
            "unlocks": cfg["unlocks"],
        })
    return result


def features_for_platforms(connected: Set[str]) -> Dict[str, bool]:
    """根据已接入平台集合，返回各功能模块是否自动解锁。

    任何功能入口调此函数判断是否能启用对应自动化能力。
    """
    return {
        # eBay 实时消息同步
        "ebay_webhook_sync": "ebay" in connected,
        # 任何平台已接入 → 自动解锁消息导入队列
        "message_import_queue": len(connected) > 0,
        # 已接入平台 → 自动写回合规块
        "auto_writeback": len(connected) > 0,
        # eBay 接入 → 解锁差评自动拉取
        "review_pull": "ebay" in connected,
        # 已接入 ≥1 平台 → 解锁多平台 Listing 监控
        "multi_platform_watch": len(connected) > 0,
        # 已接入 ≥3 平台 → 解锁跨平台对比
        "cross_platform_compare": len(connected) >= 3,
    }
