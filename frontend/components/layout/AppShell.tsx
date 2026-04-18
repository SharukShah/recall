"use client";

import { useEffect, useState, useCallback } from "react";
import { DesktopSidebar } from "./DesktopSidebar";
import { MobileTabBar } from "./MobileTabBar";
import { Toaster } from "@/components/ui/toaster";
import { fetchDashboardStats } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [dueCount, setDueCount] = useState(0);

  const loadDueCount = useCallback(async () => {
    try {
      const stats = await fetchDashboardStats();
      setDueCount(stats.due_today);
    } catch {
      // Silently fail — badge just shows 0
    }
  }, []);

  useEffect(() => {
    loadDueCount();
    const interval = setInterval(loadDueCount, 60_000);
    return () => clearInterval(interval);
  }, [loadDueCount]);

  useEffect(() => {
    const onFocus = () => loadDueCount();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [loadDueCount]);

  return (
    <>
      <div className="flex min-h-screen">
        <DesktopSidebar dueCount={dueCount} />
        <main className="flex-1 pb-20 md:pb-0 md:ml-60">
          <div className="mx-auto max-w-2xl px-4 py-6 md:py-8">
            {children}
          </div>
        </main>
        <MobileTabBar dueCount={dueCount} />
      </div>
      <Toaster />
    </>
  );
}
