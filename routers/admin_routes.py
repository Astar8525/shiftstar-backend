from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    total_users = db.query(models.User).count()
    total_companies = db.query(models.Company).count()
    total_events = db.query(models.Event).count()
    total_history = db.query(models.ShiftHistory).count()
    return {
        "total_users": total_users,
        "total_companies": total_companies,
        "total_events": total_events,
        "total_shift_history": total_history
    }

@router.get("/companies")
def get_companies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    companies = db.query(models.Company).all()
    result = []
    for company in companies:
        users = db.query(models.User).filter(models.User.company_id == company.id).all()
        events = db.query(models.Event).filter(models.Event.company_id == company.id).count()
        result.append({
            "id": company.id,
            "name": company.name,
            "created_at": str(company.created_at),
            "user_count": len(users),
            "event_count": events,
            "users": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "created_at": str(u.created_at)} for u in users]
        })
    return result

@router.get("/serve")
def serve_admin(current_user: models.User = Depends(require_admin)):
    from fastapi.responses import FileResponse
    return FileResponse("admin.html")
