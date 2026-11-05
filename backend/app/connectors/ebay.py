"""eBay 真实活连接器 — 包一层既有 app/ebay_service.py 的数据流。

复用情况（不重复造轮子）：
  - 授权连接：eBayConnection 表（OAuth，token 由 scheduler 自动刷新）
  - 消息流入：eBay webhook → handle_webhook_message → IncomingMessage 表
  - 回复发送：eBayService.send_reply（卖家确认后直发）

诚实声明：
  - fetch_buyer_messages 读取的是既有 IncomingMessage 数据流（webhook 已推入库的消息），
    不额外发起 eBay 轮询请求。
  - writeback_compliance_block 子能力当前为 pending：eBay Sell Inventory Item API
    直接改 listing Description 的写回尚未接入，合规块目前由 listing 文案生成环节产出、
    需卖家手动复制。不得伪造“已写回成功”。
"""
from typing import Any, Dict, List, Optional

from .base import ConnectorAdapter, NotConfiguredError
from ..database import SessionLocal, eBayConnection, IncomingMessage
from ..ebay_service import eBayService


class EbayConnector(ConnectorAdapter):
    platform = "ebay"
    display_name = "eBay"

    @property
    def state(self) -> str:
        return "active"

    def _user_id(self, user: Any) -> Optional[str]:
        user = user or self.user
        return getattr(user, "id", None) if user else None

    def is_configured(self, user: Any = None) -> bool:
        """连接存在且 token 未过期（留 5 分钟缓冲，与 eBayService 判定一致）。"""
        uid = self._user_id(user)
        if not uid:
            return False
        db = SessionLocal()
        try:
            conn = db.query(eBayConnection).filter_by(user_id=uid).first()
            if not conn:
                return False
            return eBayService._is_token_valid(conn)
        finally:
            db.close()

    async def fetch_buyer_messages(self, user: Any = None) -> List[Dict[str, Any]]:
        """拉取该用户 eBay 买家消息 — 读取既有 IncomingMessage 数据流。"""
        if not self.is_configured(user):
            raise NotConfiguredError(
                "eBay 未连接或 access_token 已过期，请先在工作台完成 eBay OAuth 授权"
            )
        uid = self._user_id(user)
        db = SessionLocal()
        try:
            rows = (
                db.query(IncomingMessage)
                .filter_by(user_id=uid, platform="ebay")
                .order_by(IncomingMessage.created_at.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "message_id": r.message_id,
                    "thread_id": r.thread_id,
                    "buyer_id": r.buyer_id,
                    "text": r.customer_message,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()

    async def writeback_compliance_block(
        self,
        user: Any = None,
        listing: Any = None,
        block: Optional[str] = None,
    ) -> Dict[str, Any]:
        """eBay 合规块写回 — 诚实标注子能力 pending（尚未接入 Sell Inventory Item API）。"""
        if not self.is_configured(user):
            raise NotConfiguredError(
                "eBay 未连接或 access_token 已过期，请先在工作台完成 eBay OAuth 授权"
            )
        return {
            "platform": "ebay",
            "success": False,
            "substate": "pending",
            "reason": (
                "eBay 商品合规块自动写回（Sell Inventory Item API 更新 Description）"
                "尚未接入；合规块当前由 listing 文案生成环节产出，需卖家手动复制到 eBay 后台。"
            ),
        }
