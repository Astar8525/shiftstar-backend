from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/", response_model=List[schemas.ShiftHistoryOut])
def get_history(
    range: Optional[int] = Query(7),
    shift_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ShiftHistory).filter(
        models.ShiftHistory.company_id == current_user.company_id
    )
    if shift_name:
        query = query.filter(
            models.ShiftHistory.shift_name == shift_name
        )
    results = query.order_by(
        models.ShiftHistory.date.desc()
    ).limit(range).all()
    return list(reversed(results))

@router.post("/", response_model=schemas.ShiftHistoryOut)
def save_history(
    data: schemas.ShiftHistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Update if entry exists for same shift and date
    existing = db.query(models.ShiftHistory).filter(
        models.ShiftHistory.company_id == current_user.company_id,
        models.ShiftHistory.shift_name == data.shift_name,
        models.ShiftHistory.date == data.date
    ).first()

    if existing:
        existing.oee = data.oee
        existing.good_units = data.good_units
        existing.defects = data.defects
        existing.total_downtime = data.total_downtime
        existing.cause_totals_json = data.cause_totals_json
        db.commit()
        db.refresh(existing)
        return existing

    new_entry = models.ShiftHistory(
        company_id=current_user.company_id,
        shift_name=data.shift_name,
        date=data.date,
        oee=data.oee,
        good_units=data.good_units,
        defects=data.defects,
        total_downtime=data.total_downtime,
        cause_totals_json=data.cause_totals_json
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

@router.get("/pareto")
def get_pareto(
    range: Optional[int] = Query(7),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    results = db.query(models.ShiftHistory).filter(
        models.ShiftHistory.company_id == current_user.company_id
    ).order_by(
        models.ShiftHistory.date.desc()
    ).limit(range).all()

    # Aggregate cause totals across all shifts
    totals = {}
    for entry in results:
        try:
            causes = json.loads(entry.cause_totals_json)
            for cause, minutes in causes.items():
                totals[cause] = totals.get(cause, 0) + minutes
        except Exception:
            pass

    # Sort by total minutes descending
    sorted_totals = sorted(
        totals.items(),
        key=lambda x: x[1],
        reverse=True
    )

    grand_total = sum(v for _, v in sorted_totals)
    cumulative = 0
    pareto = []
    for cause, minutes in sorted_totals:
        cumulative += minutes
        pareto.append({
            "cause": cause,
            "minutes": minutes,
            "cumulative_pct": round(cumulative / grand_total * 100) if grand_total else 0
        })

    return {"pareto": pareto, "total_minutes": grand_total}