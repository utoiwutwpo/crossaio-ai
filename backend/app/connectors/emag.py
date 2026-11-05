"""eMAG（罗马尼亚/中东欧）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：eMAG Marketplace API，https://marketplace.emag.ro/
  - 授权：API Key（Seller Center 发放）
  - 商品：/offers / /products；消息：Orders 会话接口
  - 写回：Offer 描述更新接口
  当前状态：本地无 eMAG API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class EmagConnector(PendingConnector):
    platform = "emag"
    display_name = "eMAG"
    reason = "待凭据启用（本地未配置 eMAG Marketplace API 凭证）"
