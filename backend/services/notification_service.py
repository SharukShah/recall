"""
Notification service - push subscription management and sending.
"""
import asyncio
import logging
from datetime import datetime, timezone
import asyncpg

from core.push import send_push_notification, ensure_vapid_keys
from models.notification_models import PushSubscription, NotificationSettings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def subscribe(self, subscription: PushSubscription) -> None:
        """Store a push subscription."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO notification_subscriptions (endpoint, p256dh_key, auth_key)
                VALUES ($1, $2, $3)
                ON CONFLICT (endpoint) DO UPDATE
                SET p256dh_key = EXCLUDED.p256dh_key,
                    auth_key = EXCLUDED.auth_key
                """,
                subscription.endpoint,
                subscription.keys.p256dh,
                subscription.keys.auth,
            )

    async def unsubscribe(self, endpoint: str) -> None:
        """Remove a push subscription."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM notification_subscriptions WHERE endpoint = $1",
                endpoint,
            )

    async def get_settings(self) -> NotificationSettings | None:
        """Get notification settings (single-user)."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM notification_settings LIMIT 1")
            if not row:
                return None
            return NotificationSettings(
                enabled=row["enabled"],
                review_reminder_time=row["review_reminder_time"],
                timezone=row["timezone"],
            )

    async def update_settings(self, settings: NotificationSettings) -> None:
        """Update notification settings."""
        async with self.db_pool.acquire() as conn:
            # Check if settings exist
            existing = await conn.fetchrow("SELECT id FROM notification_settings LIMIT 1")
            
            if existing:
                await conn.execute(
                    """
                    UPDATE notification_settings
                    SET enabled = $1,
                        review_reminder_time = $2,
                        timezone = $3,
                        updated_at = NOW()
                    WHERE id = $4
                    """,
                    settings.enabled,
                    settings.review_reminder_time,
                    settings.timezone,
                    existing["id"],
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO notification_settings (enabled, review_reminder_time, timezone)
                    VALUES ($1, $2, $3)
                    """,
                    settings.enabled,
                    settings.review_reminder_time,
                    settings.timezone,
                )

    async def has_active_subscription(self) -> bool:
        """Check if there's at least one subscription."""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM notification_subscriptions"
            )
            return count > 0

    async def send_test_notification(self) -> int:
        """Send a test notification to all subscriptions. Returns count sent."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM notification_subscriptions")
        
        if not rows:
            return 0
        
        sent_count = 0
        for row in rows:
            subscription_info = {
                "endpoint": row["endpoint"],
                "keys": {
                    "p256dh": row["p256dh_key"],
                    "auth": row["auth_key"]
                }
            }
            
            success = send_push_notification(
                subscription_info,
                "ReCall Test",
                "This is a test notification from ReCall!",
                "/review"
            )
            
            if success:
                sent_count += 1
            else:
                # If send failed with 410, delete the subscription
                logger.info(f"Deleting failed subscription: {row['endpoint']}")
                await self.unsubscribe(row["endpoint"])
        
        return sent_count

    async def send_review_reminder(self, due_count: int) -> int:
        """Send review reminder to all subscriptions. Returns count sent."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM notification_subscriptions")
        
        if not rows:
            return 0
        
        body = f"You have {due_count} item{'s' if due_count != 1 else ''} to review."
        sent_count = 0
        
        for row in rows:
            subscription_info = {
                "endpoint": row["endpoint"],
                "keys": {
                    "p256dh": row["p256dh_key"],
                    "auth": row["auth_key"]
                }
            }
            
            success = send_push_notification(
                subscription_info,
                "ReCall Reminder",
                body,
                "/review"
            )
            
            if success:
                sent_count += 1
            else:
                # Clean up failed subscriptions
                await self.unsubscribe(row["endpoint"])
        
        return sent_count

    async def update_last_sent(self) -> None:
        """Update the last_sent_at timestamp."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notification_settings
                SET last_sent_at = NOW()
                WHERE id IN (SELECT id FROM notification_settings LIMIT 1)
                """
            )

    async def atomic_check_and_mark_sent(self) -> bool:
        """
        Atomically check if notification can be sent and mark as sent.
        Returns True if notification should be sent, False if already sent today.
        This prevents race conditions in multi-instance deployments.
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                UPDATE notification_settings
                SET last_sent_at = NOW()
                WHERE (last_sent_at IS NULL OR last_sent_at::date < CURRENT_DATE)
                  AND id = (SELECT id FROM notification_settings ORDER BY id LIMIT 1)
                RETURNING id
                """
            )
            return result is not None
