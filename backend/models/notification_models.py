"""Pydantic models for notification endpoints."""
from pydantic import BaseModel, Field


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscription(BaseModel):
    endpoint: str = Field(..., max_length=2000)
    keys: PushSubscriptionKeys


class NotificationSettings(BaseModel):
    enabled: bool = True
    review_reminder_time: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    timezone: str = "UTC"


class NotificationSettingsResponse(BaseModel):
    enabled: bool
    review_reminder_time: str
    timezone: str
    subscription_active: bool
    vapid_public_key: str


class TestNotificationRequest(BaseModel):
    pass  # Empty body for POST request
