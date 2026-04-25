"use client";

import { useEffect } from "react";
import { registerServiceWorker } from "@/lib/pwa";

export function PWARegistration() {
  useEffect(() => {
    // Register service worker on mount
    registerServiceWorker();
  }, []);

  return null;
}
