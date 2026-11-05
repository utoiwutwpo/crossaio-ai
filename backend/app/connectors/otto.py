"""Otto Market（德国）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：Otto Market API，https://api.otto.market/
  - 授权：Client Credentials（Client ID/Secret，bearer token）
  - 商品：/v2/products 提交与更新；消息：Returns / Customer Messages 端点
  - 写回：通过产品导入接口覆盖短/长描述
  当前状态：本地无 Otto Market API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class OttoConnector(PendingConnector):
    platform = "otto"
    display_name = "Otto Market"
    reason = "待凭据启用（本地未配置 Otto Market API 凭证）"
