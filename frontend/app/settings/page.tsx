import { NotificationSettings } from "@/components/settings/NotificationSettings";
import { ExportData } from "@/components/settings/ExportData";
import { ThemeToggle } from "@/components/settings/ThemeToggle";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your preferences and data
        </p>
      </div>

      <ThemeToggle />
      <NotificationSettings />
      <ExportData />
    </div>
  );
}
