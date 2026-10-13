import json
import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/stripe", tags=["stripe"])

PLAN_TIERS = ("pro", "team")


@router.post("/create-checkout-session")
def create_checkout_session(
    tier: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="Payments are not configured yet")

    stripe.api_key = key

    if tier not in ["pro", "team"]:
        raise HTTPException(status_code=400, detail="Invalid tier")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_collection="if_required",
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
            subscription_data={
                "trial_period_days": 14,
                "trial_settings": {
                    "end_behavior": {"missing_payment_method": "cancel"}
                },
                "metadata": {"user_id": str(current_user.id), "tier": tier},
            },
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


def _company_from_user_id(db, user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        return None
    return db.query(models.Company).filter(models.Company.id == user.company_id).first()


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        stripe.Webhook.construct_event(payload, sig, secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = json.loads(payload)
    etype = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        meta = obj.get("metadata") or {}
        company = _company_from_user_id(db, meta.get("user_id"))
        tier = meta.get("tier")
        if company is not None and tier in PLAN_TIERS:
            company.plan = tier
            company.subscription_status = "trialing"
            company.stripe_customer_id = obj.get("customer")
            company.stripe_subscription_id = obj.get("subscription")
            db.commit()

    elif etype in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        sub_id = obj.get("id")
        status = obj.get("status")
        meta = obj.get("metadata") or {}
        company = db.query(models.Company).filter(
            models.Company.stripe_subscription_id == sub_id
        ).first()
        if company is None:
            company = _company_from_user_id(db, meta.get("user_id"))
        if company is not None:
            current = company.stripe_subscription_id
            if current and current != sub_id:
                return {"received": True}
            company.stripe_subscription_id = sub_id
            company.stripe_customer_id = obj.get("customer")
            company.subscription_status = status
            tier = meta.get("tier")
            if status in ("trialing", "active", "past_due") and tier in PLAN_TIERS:
                company.plan = tier
            elif status in ("canceled", "unpaid", "incomplete_expired"):
                company.plan = "starter"
            db.commit()

    return {"received": True}