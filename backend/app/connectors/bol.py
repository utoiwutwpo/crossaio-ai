"""bol.com（荷兰/比利时）连接器骨架 — 待凭据启用。

官方 API 文档要点（接入时参照）：
  - 开放平台：bol.com 零售者 API（Retailer API），https://api.bol.com/
  - 授权：OAuth2 Client Credentials（Client ID/Secret）
  - 商品：/retailer/endpoints（offers / products）；消息：Open Orders / 服务消息
  - 写回：通过 UP 稿件（Product Content）接口更新描述
  当前状态：本地无 bol.com Retailer API 凭证 —— 不调用真实 API，不伪造数据。
"""
from .base import PendingConnector


class BolConnector(PendingConnector):
    platform = "bol"
    display_name = "bol.com"
    reason = "待凭据启用（本地未配置 bol.com 零售者 API 凭证）"
