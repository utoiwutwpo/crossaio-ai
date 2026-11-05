"""Kaufland Marketplace（德国/欧洲）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：Kaufland Marketplace Seller API，https://sellerapi.kaufland.com/
  - 授权：API Key（Seller 后台发放，X-API-KEY header）
  - 商品：/categories / /offers；消息：/messages 会话线程
  - 写回：Offer 描述（短描述/长描述）更新接口
  当前状态：本地无 Kaufland Marketplace API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class KauflandConnector(PendingConnector):
    platform = "kaufland"
    display_name = "Kaufland"
    reason = "待凭据启用（本地未配置 Kaufland Marketplace API 凭证）"
