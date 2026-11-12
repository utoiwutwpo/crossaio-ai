"""双闸接口：动作放行判定 + 12 平台能力×套餐矩阵。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db, User
from ..entitlements import matrix_for_user, can_act, REASONS

router = APIRouter()


@router.get("/check", summary="动作放行判定（套餐闸 × 平台能力闸）")
def check(
    platform: str = Query(..., description="12 平台之一"),
    action: str = Query(..., description="read_messages/send_message/auto_send/write_listing/..."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回 allowed 与四种修复原因之一。

    前端用法：进入页面时批量调一次，据此把不支持的按钮置灰并显示 hint，
    而不是等用户点击后才报错。
    """
    return can_act(db, user, platform, action)


@router.get("/matrix", summary="当前套餐下 12 平台各动作放行矩阵")
def matrix(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return matrix_for_user(db, user)


@router.get("/reasons", summary="拒绝码字典（前端文案映射）")
def reasons():
    return {"reasons": list(REASONS)}
