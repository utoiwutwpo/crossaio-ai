"""【P0】轻量内存事件队列 — 按订阅自动化的"事件触发"通道。

设计（诚实边界）：
- 单进程内存 dict，不引入 Redis/消息队列；APScheduler 每 2 分钟 drain 一次。
  多实例部署时需替换为外部队列（当前 Railway 单实例 lifespan 调度，OK）。
- 事件类型：
  - new_buyer_message：买家新消息 → 触发 AI 客服自动回复环节（仅 Pro+ 且已接入平台）
  - new_watch_listing：新 listing 入监控 → 立即对该条跑一次 check_one
  - new_risk：体检发现新风险 → 生成合规块并写 Notification
"""
import logging
import threading
from collections import defaultdict
from typing import Dict, List, Set

log = logging.getLogger("crossaio.automation_events")

# user_id -> {"events": {event_type: count}, "payloads": [(event_type, payload), ...]}
_queue: Dict[str, Dict] = defaultdict(
    lambda: {"counts": defaultdict(int), "payloads": []})
_lock = threading.Lock()

EVENT_TYPES = {"new_buyer_message", "new_watch_listing", "new_risk"}


def enqueue(user_id: str, event_type: str, payload: dict | None = None) -> None:
    """把一个事件塞进该用户的内存队列。未知事件类型直接忽略并记 warning。"""
    if not user_id:
        return
    if event_type not in EVENT_TYPES:
        log.warning("未知自动化事件类型：%s（忽略）", event_type)
        return
    with _lock:
        bucket = _queue[user_id]
        bucket["counts"][event_type] += 1
        bucket["payloads"].append((event_type, payload or {}))
    log.info("事件入队 user=%s type=%s total=%d",
             user_id, event_type, len(bucket["payloads"]))


def drain(user_id: str) -> List:
    """取出并清空该用户当前所有待处理事件，返回 [(event_type, payload), ...]。
    无事件返回空列表。"""
    with _lock:
        bucket = _queue.pop(user_id, None)
    if not bucket:
        return []
    payloads = bucket["payloads"]
    log.info("事件出队 user=%s count=%d", user_id, len(payloads))
    return payloads


def pending_users() -> List[str]:
    """返回当前有待处理事件的全部 user_id（快照）。"""
    with _lock:
        return [uid for uid, b in _queue.items() if b["payloads"]]
