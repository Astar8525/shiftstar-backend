from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter(prefix="/production", tags=["production"])

@router.post("/", response_model=schemas.ProductionOut)
def save_production(
    data: schemas.ProductionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if entry already exists for this shift and date
    existing = db.query(models.ProductionData).filter(
        models.ProductionData.company_id == current_user.company_id,
        models.ProductionData.shift_name == data.shift_name,
        models.ProductionData.date == data.date
    ).first()

    if existing:
        # Update existing entry
        existing.units_produced = data.units_produced
        existing.units_defect = data.units_defect
        existing.planned_time_min = data.planned_time_min
        existing.downtime_min = data.downtime_min
        existing.ideal_cycle_sec = data.ideal_cycle_sec
        db.commit()
        db.refresh(existing)
        return existing

    # Create new entry
    new_data = models.ProductionData(
        company_id=current_user.company_id,
        shift_name=data.shift_name,
        date=data.date,
        units_produced=data.units_produced,
        units_defect=data.units_defect,
        planned_time_min=data.planned_time_min,
        downtime_min=data.downtime_min,
        ideal_cycle_sec=data.ideal_cycle_sec
    )
    db.add(new_data)
    db.commit()
    db.refresh(new_data)
    return new_data

@router.get("/", response_model=List[schemas.ProductionOut])
def get_production(
    shift_name: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ProductionData).filter(
        models.ProductionData.company_id == current_user.company_id
    )
    if shift_name:
        query = query.filter(
            models.ProductionData.shift_name == shift_name
        )
    if date:
        query = query.filter(
            models.ProductionData.date == date
        )
    return query.order_by(models.ProductionData.date.desc()).all()

@router.delete("/{production_id}")
def delete_production(
    production_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entry = db.query(models.ProductionData).filter(
        models.ProductionData.id == production_id,
        models.ProductionData.company_id == current_user.company_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Production data not found")
    db.delete(entry)
    db.commit()
    return {"message": "Production data deleted"}