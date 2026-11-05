"""Cdiscount（法国）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：Cdiscount Open API，https://seller.cdiscount.com/
  - 授权：API Token（ Seller 后台申请）
  - 商品：/order / /offer 系列；消息：Customer Service 会话接口
  - 写回：商品描述更新接口
  当前状态：本地无 Cdiscount API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class CdiscountConnector(PendingConnector):
    platform = "cdiscount"
    display_name = "Cdiscount"
    reason = "待凭据启用（本地未配置 Cdiscount API 凭证）"
