from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
import stripe
import os

stripe.api_key = "sk_test_51TeQXqAzzEsthod42fh8tirNHHO1Kb0rMiwBT4bM7QrJWFR8V8eZ3UhMtBpmBNKclIfEWlPZfxhppltIm6ufNUFp00uS2oqCWJ"

PRICES = {
    "pro": "price_pro_monthly",
    "team": "price_team_monthly"
}

router = APIRouter(prefix="/stripe", tags=["stripe"])

@router.post("/create-checkout-session")
def create_checkout_session(
    tier: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if tier not in ["pro", "team"]:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"ShiftStar {tier.capitalize()}",
                    },
                    "unit_amount": 4900 if tier == "pro" else 14900,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            success_url="http://127.0.0.1:8000/dashboard?payment=success",
            cancel_url="http://127.0.0.1:8000/dashboard?payment=cancelled",
            customer_email=current_user.email,
            metadata={"user_id": current_user.id, "tier": tier}
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/success")
def payment_success(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {"message": "Payment successful", "user": current_user.email}