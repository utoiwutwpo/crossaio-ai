"""连接器适配器抽象基类 — 全平台实时同步 P1 的统一契约。

设计原则：诚实状态。
  - state = "active"  仅当该平台具备真实、可运行的 API 接入能力。
  - state = "pending" 表示骨架已就绪、等待凭证/等待实现；
    此时 fetch/writeback 必须抛 NotConfiguredError，不得伪造数据、不得模拟成功。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class NotConfiguredError(Exception):
    """平台连接器未配置（缺凭证 / 未授权 / 子能力待实现）时抛出的统一异常。

    调用方必须捕获并向用户展示“待启用”，严禁吞掉后伪装成成功。
    """


class ConnectorAdapter(ABC):
    """统一连接器适配器接口。

    每个平台一个子类，接口签名完全一致：
      - fetch_buyer_messages(user)          拉取新买家消息，返回消息 dict 列表
      - writeback_compliance_block(user, listing, block)  把合规块写回平台 listing
      - is_configured(user) -> bool         当前用户是否已配置该平台
    """

    platform: str = ""
    display_name: str = ""

    def __init__(self, user: Any = None) -> None:
        self.user = user

    @property
    def state(self) -> str:
        """注册表级状态：active=真实可用；pending=待凭据/待实现。"""
        return "pending"

    @abstractmethod
    def is_configured(self, user: Any = None) -> bool:
        """当前用户是否已完成该平台授权/凭证配置。"""

    @abstractmethod
    async def fetch_buyer_messages(self, user: Any = None) -> List[Dict[str, Any]]:
        """拉取该平台的新买家消息。未配置时必须抛 NotConfiguredError。"""

    @abstractmethod
    async def writeback_compliance_block(
        self,
        user: Any = None,
        listing: Any = None,
        block: Optional[str] = None,
    ) -> Dict[str, Any]:
        """把生成好的合规块写回平台 listing 描述。未配置时必须抛 NotConfiguredError。"""


class PendingConnector(ConnectorAdapter):
    """待凭据平台骨架 — 接口签名齐全，但一律诚实失败。

    子类只需填 platform / display_name / reason 三个类属性。
    严禁在子类里伪造数据或调用真实 API。
    """

    reason: str = "待凭据启用"

    @property
    def state(self) -> str:
        return "pending"

    def is_configured(self, user: Any = None) -> bool:
        return False

    async def fetch_buyer_messages(self, user: Any = None) -> List[Dict[str, Any]]:
        raise NotConfiguredError(f"{self.display_name}：{self.reason}")

    async def writeback_compliance_block(
        self,
        user: Any = None,
        listing: Any = None,
        block: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotConfiguredError(f"{self.display_name}：{self.reason}")
