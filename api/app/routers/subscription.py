from fastapi import APIRouter, Depends, HTTPException, Request, Header, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import stripe
import logging
import json

from app.core.database import get_db, User, UserQuota, SubscriptionTier, get_or_create_quota
from app.core.config import get_settings
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/subscription", tags=["subscription"])

if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class CreateCheckoutSessionRequest(BaseModel):
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class SubscriptionStatus(BaseModel):
    tier: str
    price: float
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: Optional[str] = None
    current_period_end: Optional[int] = None


@router.post("/create-checkout-session")
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Optional[CreateCheckoutSessionRequest] = Body(default=None)
):
    if not settings.stripe_secret_key or not settings.stripe_pro_price_id:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    if current_user.subscription_tier == SubscriptionTier.PRO:
        raise HTTPException(status_code=400, detail="Already a PRO subscriber")
    
    success_url = (request.success_url if request else None) or f"{settings.frontend_url}/portal/?payment=success"
    cancel_url = (request.cancel_url if request else None) or f"{settings.frontend_url}/portal/?payment=canceled"
    
    try:
        customer = None
        if current_user.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
            except stripe.error.InvalidRequestError:
                pass
        
        if not customer:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={
                    "user_id": current_user.id,
                    "firebase_uid": current_user.firebase_uid
                }
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": settings.stripe_pro_price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user.id,
                "firebase_uid": current_user.firebase_uid
            }
        )
        
        return {
            "success": True,
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-portal-session")
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found")
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.frontend_url}/"
        )
        
        return {
            "success": True,
            "portal_url": portal_session.url
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.core.database import PRICING
    
    return SubscriptionStatus(
        tier=current_user.subscription_tier.value,
        price=PRICING[current_user.subscription_tier],
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        subscription_status=current_user.subscription_status,
        current_period_end=current_user.subscription_current_period_end
    )


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    
    try:
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        current_user.subscription_status = "canceling"
        db.commit()
        
        return {
            "success": True,
            "message": "Subscription will be canceled at the end of the billing period",
            "cancel_at": subscription.cancel_at
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    logger.info(f"Received Stripe webhook event: {event['type']}")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.subscription_tier = SubscriptionTier.PRO
                user.stripe_subscription_id = session.get("subscription")
                user.subscription_status = "active"
                db.commit()
                logger.info(f"User {user_id} upgraded to PRO")
    
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.stripe_subscription_id = subscription.id
            user.subscription_status = subscription.status
            
            if subscription.status == "active":
                user.subscription_tier = SubscriptionTier.PRO
            elif subscription.status in ["canceled", "unpaid"]:
                user.subscription_tier = SubscriptionTier.FREE
            
            if subscription.get("current_period_end"):
                user.subscription_current_period_end = subscription.get("current_period_end")
            
            db.commit()
            logger.info(f"Updated subscription for user {user.id}: {subscription.status}")
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = SubscriptionTier.FREE
            user.subscription_status = "canceled"
            user.stripe_subscription_id = None
            db.commit()
            logger.info(f"User {user.id} subscription canceled")
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "past_due"
            db.commit()
            logger.warning(f"Payment failed for user {user.id}")
    
    return {"success": True, "received": True}
