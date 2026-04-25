"use client";

import { useState, useEffect } from "react";
import { requestNotificationPermission, subscribeToPush, unsubscribeFromPush, getExistingSubscription } from "@/lib/push";
import {
  getNotificationSettings,
  subscribeToNotifications,
  unsubscribeFromNotifications,
  updateNotificationSettings,
  sendTestNotification,
} from "@/lib/api";
import type { NotificationSettings, NotificationSettingsResponse } from "@/types/notification";

export function useNotifications() {
  const [settings, setSettings] = useState<NotificationSettingsResponse | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [permissionState, setPermissionState] = useState<NotificationPermission>("default");

  const loadSettings = async () => {
    try {
      const data = await getNotificationSettings();
      setSettings(data);
      setIsSubscribed(data.subscription_active);
      
      if ('Notification' in window) {
        setPermissionState(Notification.permission);
      }
    } catch (error) {
      console.error("Failed to load notification settings:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const subscribe = async () => {
    if (!settings) return;

    try {
      // Request permission
      const permission = await requestNotificationPermission();
      setPermissionState(permission);
      
      if (permission !== 'granted') {
        throw new Error('Notification permission denied');
      }

      // Subscribe to push
      const subscription = await subscribeToPush(settings.vapid_public_key);
      
      // Convert subscription to API format
      const subscriptionJson = subscription.toJSON();
      const subscriptionData = {
        endpoint: subscriptionJson.endpoint!,
        keys: {
          p256dh: subscriptionJson.keys!.p256dh!,
          auth: subscriptionJson.keys!.auth!,
        },
      };

      // Send to backend
      await subscribeToNotifications(subscriptionData);
      setIsSubscribed(true);
      await loadSettings();
    } catch (error) {
      console.error("Failed to subscribe:", error);
      throw error;
    }
  };

  const unsubscribe = async () => {
    try {
      const subscription = await getExistingSubscription();
      if (subscription) {
        const subscriptionJson = subscription.toJSON();
        await unsubscribeFromNotifications({
          endpoint: subscriptionJson.endpoint!,
          keys: {
            p256dh: subscriptionJson.keys!.p256dh!,
            auth: subscriptionJson.keys!.auth!,
          },
        });
      }
      
      await unsubscribeFromPush();
      setIsSubscribed(false);
      await loadSettings();
    } catch (error) {
      console.error("Failed to unsubscribe:", error);
      throw error;
    }
  };

  const updateSettings = async (newSettings: NotificationSettings) => {
    try {
      await updateNotificationSettings(newSettings);
      await loadSettings();
    } catch (error) {
      console.error("Failed to update settings:", error);
      throw error;
    }
  };

  const sendTest = async () => {
    try {
      await sendTestNotification();
    } catch (error) {
      console.error("Failed to send test notification:", error);
      throw error;
    }
  };

  return {
    settings,
    isSubscribed,
    loading,
    permissionState,
    subscribe,
    unsubscribe,
    updateSettings,
    sendTest,
    reload: loadSettings,
  };
}
