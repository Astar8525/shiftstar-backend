import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from auth import hash_password, verify_password, create_access_token, get_current_user
from notify import send_signup_alert
import models
import schemas

router = APIRouter(prefix="/auth", tags=["auth"])

_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_CHARS) for _ in range(8))
        taken = db.query(models.Company).filter(models.Company.invite_code == code).first()
        if not taken:
            return code


def _require_admin(user: models.User):
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only a company admin can manage the invite code")


SEAT_LIMITS = {"starter": 1, "pro": 3, "team": 10}


def _seat_limit(company):
    plan = ((company.plan if company is not None else None) or "starter").lower()
    if plan == "plant":
        return 10 ** 9
    return SEAT_LIMITS.get(plan, 1)


def _active_count(db, company_id):
    members = db.query(models.User).filter(models.User.company_id == company_id).all()
    return sum(1 for m in members if m.is_active is not False)


@router.post("/register", response_model=schemas.Token)
def register(user_data: schemas.UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if len(user_data.password or "") < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(user_data.password) > 128:
        raise HTTPException(status_code=400, detail="Password is too long")
    existing = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    company_name = (user_data.company_name or "").strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name is required")

    company = db.query(models.Company).filter(
        func.lower(models.Company.name) == company_name.lower()
    ).first()

    if company:
        supplied = (user_data.invite_code or "").strip().upper()
        valid = bool(company.invite_code) and bool(supplied) and secrets.compare_digest(
            supplied.encode(), company.invite_code.encode()
        )
        if not valid:
            raise HTTPException(
                status_code=403,
                detail="A company with that name already exists. To join it, enter the invite code from your company admin. Otherwise, choose a different company name."
            )
        if _active_count(db, company.id) >= _seat_limit(company):
            raise HTTPException(status_code=403, detail="This company has reached the user limit for its plan. Ask your company admin to upgrade.")
        role = "supervisor"
    else:
        company = models.Company(name=company_name, invite_code=_new_invite_code(db))
        db.add(company)
        db.commit()
        db.refresh(company)
        role = "admin"

    user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=role,
        company_id=company.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    background_tasks.add_task(send_signup_alert, user.name, user.email, company.name, user.role)

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()
    if not user or not verify_password(credentials.password, user.password_hash) or user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/invite-code")
def get_invite_code(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.invite_code:
        company.invite_code = _new_invite_code(db)
        db.commit()
    return {"company": company.name, "invite_code": company.invite_code}


@router.post("/invite-code/reset")
def reset_invite_code(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.invite_code = _new_invite_code(db)
    db.commit()
    return {"company": company.name, "invite_code": company.invite_code}

@router.get("/team")
def list_team(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    members = db.query(models.User).filter(
        models.User.company_id == current_user.company_id
    ).order_by(models.User.id).all()
    return [
        {"id": m.id, "name": m.name, "email": m.email, "role": m.role, "is_active": m.is_active is not False}
        for m in members
    ]


def _team_member(user_id: int, current_user: models.User, db: Session) -> models.User:
    member = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.company_id == current_user.company_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.post("/team/{user_id}/remove")
def remove_member(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    member = _team_member(user_id, current_user, db)
    member.is_active = False
    db.commit()
    return {"removed": member.id}


@router.post("/team/{user_id}/restore")
def restore_member(user_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_admin(current_user)
    member = _team_member(user_id, current_user, db)
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    if member.is_active is False and _active_count(db, current_user.company_id) >= _seat_limit(company):
        raise HTTPException(status_code=400, detail="User limit reached for your plan. Upgrade to restore this member.")
    member.is_active = True
    db.commit()
    return {"restored": member.id}


from pydantic import BaseModel


class RoleChange(BaseModel):
    role: str


VALID_ROLES = ("supervisor", "manager", "admin")


@router.post("/team/{user_id}/role")
def change_member_role(user_id: int, body: RoleChange, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if (current_user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only a company admin can change roles")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You can't change your own role. Ask another admin.")
    new_role = (body.role or "").strip().lower()
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    member = _team_member(user_id, current_user, db)
    member.role = new_role
    db.commit()
    return {"id": member.id, "role": member.role}