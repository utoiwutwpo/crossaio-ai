"""Zalando（德国/欧洲时尚）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：Zalando Partner API，https://api.north.developers.zalando.com/
  - 授权：OAuth2 Client Credentials
  - 商品：/products；消息：Customer 会话相关端点
  - 写回：Product 描述更新接口
  当前状态：本地无 Zalando Partner API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class ZalandoConnector(PendingConnector):
    platform = "zalando"
    display_name = "Zalando"
    reason = "待凭据启用（本地未配置 Zalando Partner API 凭证）"
