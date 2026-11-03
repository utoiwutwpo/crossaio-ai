"""
欧盟授权代表（欧代）台账 — GPSR (EU 2023/988 Art.9) 强制要求。

为什么独立成模块：
- 合规块（gpsr.gpsr_block_text）与 Listing 文案此前用 [欧代公司名称] 占位符，
  卖家每次都要手动替换，体验差且易漏。
- 本模块把欧代集中管理（可多条、可设默认），并提供 render_rep_line()
  把"公司名 + 地址 + 邮箱"拼成可在合规块/Lising 直接粘贴的单行文本。

所有函数接收 SQLAlchemy Session，便于在 router 中复用现有依赖。
"""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..database import EuResponsiblePerson


def list_reps(db: Session, user_id: str) -> List[Dict]:
    """返回该用户全部欧代（默认排第一）。"""
    rows = (
        db.query(EuResponsiblePerson)
        .filter(EuResponsiblePerson.user_id == user_id)
        .order_by(EuResponsiblePerson.is_default.desc(),
                  EuResponsiblePerson.created_at.desc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def get_default_rep(db: Session, user_id: str) -> Optional[Dict]:
    """返回该用户的默认欧代；无默认则取最近添加的一条；都没有返回 None。"""
    rep = (
        db.query(EuResponsiblePerson)
        .filter(EuResponsiblePerson.user_id == user_id,
                EuResponsiblePerson.is_default.is_(True))
        .first()
    )
    if rep is None:
        rep = (
            db.query(EuResponsiblePerson)
            .filter(EuResponsiblePerson.user_id == user_id)
            .order_by(EuResponsiblePerson.created_at.desc())
            .first()
        )
    return _row_to_dict(rep) if rep else None


def get_rep(db: Session, user_id: str, rep_id: str) -> Optional[Dict]:
    rep = (
        db.query(EuResponsiblePerson)
        .filter(EuResponsiblePerson.id == rep_id,
                EuResponsiblePerson.user_id == user_id)
        .first()
    )
    return _row_to_dict(rep) if rep else None


def add_rep(db: Session, user_id: str, *, company_name: str, address: str,
            email: str = "", phone: str = "", website: str = "",
            contact_person: str = "", is_default: bool = False) -> Dict:
    """新增一条欧代。若 is_default=True，则把该用户其他欧代取消默认。"""
    if is_default:
        _clear_defaults(db, user_id)
    # 该用户尚无任何欧代时，强制设为默认（首条即默认）
    existing = db.query(EuResponsiblePerson).filter(
        EuResponsiblePerson.user_id == user_id).first()
    make_default = is_default or existing is None

    rep = EuResponsiblePerson(
        user_id=user_id,
        company_name=company_name,
        address=address,
        email=email,
        phone=phone,
        website=website,
        contact_person=contact_person,
        is_default=make_default,
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return _row_to_dict(rep)


def set_default(db: Session, user_id: str, rep_id: str) -> Dict:
    """把指定欧代设为默认，其余取消。"""
    rep = (
        db.query(EuResponsiblePerson)
        .filter(EuResponsiblePerson.id == rep_id,
                EuResponsiblePerson.user_id == user_id)
        .first()
    )
    if rep is None:
        raise KeyError("欧代不存在或不属于该用户")
    _clear_defaults(db, user_id)
    rep.is_default = True
    db.commit()
    db.refresh(rep)
    return _row_to_dict(rep)


def delete_rep(db: Session, user_id: str, rep_id: str) -> None:
    rep = (
        db.query(EuResponsiblePerson)
        .filter(EuResponsiblePerson.id == rep_id,
                EuResponsiblePerson.user_id == user_id)
        .first()
    )
    if rep is None:
        raise KeyError("欧代不存在或不属于该用户")
    was_default = rep.is_default
    db.delete(rep)
    db.commit()
    # 删掉的是默认、且还有剩余 → 把剩余第一条提升为默认
    if was_default:
        remaining = (
            db.query(EuResponsiblePerson)
            .filter(EuResponsiblePerson.user_id == user_id)
            .order_by(EuResponsiblePerson.created_at.desc())
            .first()
        )
        if remaining:
            remaining.is_default = True
            db.commit()


def render_rep_line(rep: Optional[Dict]) -> str:
    """把欧代拼成合规块可用的一行文本：公司名, 地址, 邮箱。

    无欧代时返回占位符（保持向后兼容：未配置时卖家仍需手动填）。
    """
    if not rep:
        return "[欧代公司名称], [欧代地址], [联系邮箱]"
    parts = [rep["company_name"], rep["address"]]
    if rep.get("email"):
        parts.append(rep["email"])
    if rep.get("phone"):
        parts.append(f"Tel: {rep['phone']}")
    if rep.get("website"):
        parts.append(rep["website"])
    return ", ".join(p for p in parts if p)


def _clear_defaults(db: Session, user_id: str) -> None:
    db.query(EuResponsiblePerson).filter(
        EuResponsiblePerson.user_id == user_id,
        EuResponsiblePerson.is_default.is_(True),
    ).update({EuResponsiblePerson.is_default: False})
    db.commit()


def _row_to_dict(r: EuResponsiblePerson) -> Dict:
    return {
        "id": r.id,
        "company_name": r.company_name,
        "address": r.address,
        "email": r.email,
        "phone": r.phone,
        "website": r.website,
        "contact_person": r.contact_person,
        "is_default": r.is_default,
        "created_at": r.created_at,
    }
