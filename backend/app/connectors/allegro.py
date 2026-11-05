"""Allegro（波兰）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：Allegro REST API，https://developer.allegro.pl/documentation/
  - 授权：OAuth2（Client Credentials / Authorization Code）
  - 买家消息：/messages（会话线程）系列端点
  - 写回：/sale/offers/{offerId} 更新 Offer 描述
  当前状态：本地无 Allegro client_id/client_secret —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class AllegroConnector(PendingConnector):
    platform = "allegro"
    display_name = "Allegro"
    reason = "待凭据启用（本地未配置 Allegro API 凭证）"
