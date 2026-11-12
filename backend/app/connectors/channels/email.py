"""C 档邮件通道：IMAP 监听平台通知邮件 → 解析成会话。

平台（OTTO / Kaufland / Cdiscount / eMAG / Zalando / Fruugo）不提供卖家消息
API，但会把买家咨询与订单通知发到卖家邮箱；本通道只读邮件、不猜数据。
"""
import asyncio
import imaplib
import email as _email
import re
from email.header import decode_header, make_header
from typing import List

from .base import CapabilityNotSupported, ChannelAdapter


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _body_text(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


class EmailChannel(ChannelAdapter):
    mode = "email"
    tier = "C"

    def __init__(self, platform: str, payload=None, client=None):
        super().__init__(payload, client)
        self.platform = platform

    def _cfg(self):
        self.need("imap_host", "imap_user", "imap_password")
        return {
            "host": self.payload["imap_host"].strip(),
            "port": int(self.payload.get("imap_port") or 993),
            "user": self.payload["imap_user"].strip(),
            "password": self.payload["imap_password"],
        }

    def _fetch_blocking(self, limit: int) -> List[dict]:
        cfg = self._cfg()
        out: List[dict] = []
        conn = imaplib.IMAP4_SSL(cfg["host"], cfg["port"])
        try:
            conn.login(cfg["user"], cfg["password"])
            conn.select("INBOX")
            typ, data = conn.search(None, "UNSEEN")
            if typ != "OK":
                return []
            ids = (data[0] or b"").split()[-limit:]
            for mid in ids:
                typ, raw = conn.fetch(mid, "(RFC822)")
                if typ != "OK" or not raw:
                    continue
                msg = _email.message_from_bytes(raw[0][1])
                subject = _decode(msg.get("Subject", ""))
                sender = _decode(msg.get("From", ""))
                text = _body_text(msg)
                # 邮件线程用 Message-ID 归并
                thread = (msg.get("Message-ID") or f"email-{mid.decode()}").strip()
                out.append({
                    "platform": self.platform,
                    "external_thread_id": thread,
                    "external_message_id": thread,
                    "buyer_id": sender,
                    "subject": subject,
                    "body": text.strip()[:4000],
                    "direction": "incoming",
                    "created_at": _decode(msg.get("Date", "")),
                })
        finally:
            try:
                conn.logout()
            except Exception:
                pass
        return out

    async def fetch_messages(self, since: str | None = None) -> List[dict]:
        return await asyncio.to_thread(self._fetch_blocking, 20)

    async def send_message(self, thread_id: str, text: str) -> dict:
        raise CapabilityNotSupported(
            self.platform, "send_message", "platform_unsupported",
            f"{self.platform} 邮件通道只读；回复请在邮件客户端发送，系统已生成草稿")
