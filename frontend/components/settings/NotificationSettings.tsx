"use client";

import { useState } from "react";
import { useNotifications } from "@/hooks/useNotifications";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Bell, BellOff, Send } from "lucide-react";

export function NotificationSettings() {
  const { settings, isSubscribed, loading, permissionState, subscribe, unsubscribe, updateSettings, sendTest } = useNotifications();
  const { toast } = useToast();
  const [reminderTime, setReminderTime] = useState(settings?.review_reminder_time || "09:00");

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  if (!settings) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-destructive">Failed to load settings</p>
        </CardContent>
      </Card>
    );
  }

  const handleToggleNotifications = async () => {
    try {
      if (isSubscribed) {
        await unsubscribe();
        toast({
          title: "Notifications disabled",
          description: "You will no longer receive push notifications",
        });
      } else {
        await subscribe();
        toast({
          title: "Notifications enabled",
          description: "You will receive daily review reminders",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to toggle notifications",
        variant: "destructive",
      });
    }
  };

  const handleUpdateTime = async () => {
    try {
      await updateSettings({
        enabled: settings.enabled,
        review_reminder_time: reminderTime,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      toast({
        title: "Settings updated",
        description: `Reminders will be sent at ${reminderTime}`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update settings",
        variant: "destructive",
      });
    }
  };

  const handleSendTest = async () => {
    try {
      await sendTest();
      toast({
        title: "Test sent",
        description: "Check your device for the notification",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send test notification",
        variant: "destructive",
      });
    }
  };

  const canEnable = permissionState === 'granted' || permissionState === 'default';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Push Notifications
        </CardTitle>
        <CardDescription>
          Get daily reminders when you have reviews due
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>Enable Notifications</Label>
            <p className="text-sm text-muted-foreground">
              {isSubscribed ? "Notifications are active" : "Subscribe to receive reminders"}
            </p>
          </div>
          <Switch
            checked={isSubscribed}
            onCheckedChange={handleToggleNotifications}
            disabled={!canEnable}
          />
        </div>

        {permissionState === 'denied' && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            Notification permission denied. Please enable in your browser settings.
          </div>
        )}

        {/* Reminder Time */}
        {isSubscribed && (
          <>
            <div className="space-y-2">
              <Label htmlFor="reminder-time">Reminder Time</Label>
              <div className="flex gap-2">
                <Input
                  id="reminder-time"
                  type="time"
                  value={reminderTime}
                  onChange={(e) => setReminderTime(e.target.value)}
                  className="max-w-[150px]"
                />
                <Button onClick={handleUpdateTime} variant="outline">
                  Update
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Your local time: {Intl.DateTimeFormat().resolvedOptions().timeZone}
              </p>
            </div>

            {/* Test Button */}
            <div>
              <Button onClick={handleSendTest} variant="outline" className="w-full">
                <Send className="mr-2 h-4 w-4" />
                Send Test Notification
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
