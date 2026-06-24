from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
import stripe
import os

router = APIRouter(prefix="/stripe", tags=["stripe"])

@router.post("/create-checkout-session")
def create_checkout_session(
    tier: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="Stripe not configured - key: " + str(os.environ.keys()))
    
    stripe.api_key = key
    
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
            success_url="https://web-production-f21c8.up.railway.app/dashboard?payment=success",
            cancel_url="https://web-production-f21c8.up.railway.app/dashboard?payment=cancelled",
            customer_email=current_user.email,
            metadata={"user_id": str(current_user.id), "tier": tier}
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