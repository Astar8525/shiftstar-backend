from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type, timedelta
import json

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/history", tags=["history"])


def _entry_day(entry):
    try:
        return date_type.fromisoformat(str(entry.date)[:10])
    except Exception:
        return None


def _within_days(results, days):
    """Keep entries from the last `days` calendar days, counted back from the newest entry."""
    dated = [(e, _entry_day(e)) for e in results]
    found = [d for _, d in dated if d is not None]
    if not found:
        return list(results)
    cutoff = max(found) - timedelta(days=days - 1)
    return [e for e, d in dated if d is None or d >= cutoff]


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
    ).all()
    results = _within_days(results, range or 7)
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
    ).all()
    results = _within_days(results, range or 7)

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