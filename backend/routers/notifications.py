"""Notification endpoints - push subscriptions and settings."""
from fastapi import APIRouter, Request, HTTPException, Depends
import logging
from urllib.parse import urlparse

from models.notification_models import (
    PushSubscription,
    NotificationSettings,
    NotificationSettingsResponse,
    TestNotificationRequest,
)
from services.notification_service import NotificationService
from core.push import ensure_vapid_keys
from core.rate_limiter import rate_limit
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def get_notification_service(request: Request) -> NotificationService:
    """Dependency injection for NotificationService."""
    return NotificationService(request.app.state.db_pool)


@router.post("/subscribe", dependencies=[Depends(rate_limit(5, 300))])  # 5 per 5 minutes
async def subscribe_push(
    subscription: PushSubscription,
    service: NotificationService = Depends(get_notification_service),
    user = Depends(get_current_user),
):
    """Store a push notification subscription."""
    try:
        # Validate endpoint URL
        parsed = urlparse(subscription.endpoint)
        if parsed.scheme != "https":
            raise HTTPException(status_code=400, detail="Endpoint must use HTTPS")
        
        # Validate known push providers
        allowed_domains = [
            "fcm.googleapis.com",
            "notify.windows.com", 
            "push.apple.com",
            "updates.push.services.mozilla.com",
            "web.push.apple.com",
        ]
        if not any(domain in parsed.netloc for domain in allowed_domains):
            logger.warning(f"Unknown push provider: {parsed.netloc}")
            # Allow but log warning for unknown providers
        
        await service.subscribe(subscription)
        return {"message": "Subscribed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscribe failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@router.delete("/subscribe")
async def unsubscribe_push(
    subscription: PushSubscription,
    service: NotificationService = Depends(get_notification_service),
    user = Depends(get_current_user),
):
    """Remove a push notification subscription."""
    try:
        await service.unsubscribe(subscription.endpoint)
        return {"message": "Unsubscribed successfully"}
    except Exception as e:
        logger.error(f"Unsubscribe failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")


@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    service: NotificationService = Depends(get_notification_service),
    user = Depends(get_current_user),
):
    """Get notification settings."""
    settings = await service.get_settings()
    has_subscription = await service.has_active_subscription()
    
    # Get VAPID key if configured, otherwise use empty string
    try:
        _, public_key = ensure_vapid_keys()
    except ValueError:
        public_key = ""  # VAPID not configured - push notifications unavailable
    
    if not settings:
        # Return defaults if no settings exist yet
        settings = NotificationSettings()
    
    return NotificationSettingsResponse(
        enabled=settings.enabled,
        review_reminder_time=settings.review_reminder_time,
        timezone=settings.timezone,
        subscription_active=has_subscription,
        vapid_public_key=public_key,
    )


@router.put("/settings")
async def update_notification_settings(
    settings: NotificationSettings,
    service: NotificationService = Depends(get_notification_service),
    user = Depends(get_current_user),
):
    """Update notification settings."""
    try:
        await service.update_settings(settings)
        return {"message": "Settings updated"}
    except Exception as e:
        logger.error(f"Settings update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.post("/test", dependencies=[Depends(rate_limit(5, 3600))])  # 5 per hour
async def send_test_notification(
    request: TestNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
    user = Depends(get_current_user),
):
    """Send a test notification to all subscriptions."""
    try:
        sent_count = await service.send_test_notification()
        return {"message": f"Test notification sent to {sent_count} device(s)"}
    except Exception as e:
        logger.error(f"Test notification failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test notification")
