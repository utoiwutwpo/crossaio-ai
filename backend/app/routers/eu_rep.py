"""欧盟授权代表（欧代）台账 CRUD — GPSR 合规块的欧代数据源。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db, User
from ..schemas import EuRepCreate, EuRepOut, EuRepSetDefault
from ..auth import get_current_user
from ..experts import eu_rep as eu_rep_svc

router = APIRouter()


@router.get("", response_model=list[EuRepOut], summary="列出当前用户的全部欧代")
def list_reps(user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return eu_rep_svc.list_reps(db, user.id)


@router.post("", response_model=EuRepOut, summary="新增欧代")
def add_rep(req: EuRepCreate, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    return eu_rep_svc.add_rep(
        db, user.id,
        company_name=req.company_name, address=req.address, email=req.email,
        phone=req.phone, website=req.website, contact_person=req.contact_person,
        is_default=req.is_default,
    )


@router.post("/default", response_model=EuRepOut, summary="设置默认欧代")
def set_default(req: EuRepSetDefault, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    try:
        return eu_rep_svc.set_default(db, user.id, req.rep_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="欧代不存在或不属于该用户")


@router.delete("/{rep_id}", summary="删除欧代")
def delete_rep(rep_id: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    try:
        eu_rep_svc.delete_rep(db, user.id, rep_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="欧代不存在或不属于该用户")
    return {"ok": True}
