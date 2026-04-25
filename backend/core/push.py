"""
Push notification support using Web Push API with VAPID keys.
VAPID keys MUST be configured via environment variables for security.
"""
import json
import logging
from pywebpush import webpush, WebPushException

from config import settings

logger = logging.getLogger(__name__)


def ensure_vapid_keys() -> tuple[str, str]:
    private_key = settings.VAPID_PRIVATE_KEY
    public_key = settings.VAPID_PUBLIC_KEY
    
    if not private_key or not public_key:
        raise ValueError("VAPID keys not configured. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY in environment.")
    
    logger.info("VAPID keys loaded from environment")
    return private_key, public_key


def send_push_notification(subscription_info: dict, title: str, body: str, url: str = "/") -> bool:
    private_key, _ = ensure_vapid_keys()
    
    payload = json.dumps({"title": title, "body": body, "url": url})
    vapid_claims = {"sub": f"mailto:{settings.VAPID_SUBJECT or 'admin@recall.local'}"}
    
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=vapid_claims,
            ttl=86400,
        )
        return True
    except WebPushException as e:
        logger.error(f"Push notification failed: {e}")
        if e.response and e.response.status_code == 410:
            logger.info("Subscription is gone (410), should be deleted")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push: {e}")
        return False
