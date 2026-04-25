export interface PushSubscriptionKeys {
  p256dh: string;
  auth: string;
}

export interface PushSubscriptionData {
  endpoint: string;
  keys: PushSubscriptionKeys;
}

export interface NotificationSettings {
  enabled: boolean;
  review_reminder_time: string;
  timezone: string;
}

export interface NotificationSettingsResponse {
  enabled: boolean;
  review_reminder_time: string;
  timezone: string;
  subscription_active: boolean;
  vapid_public_key: string;
}
