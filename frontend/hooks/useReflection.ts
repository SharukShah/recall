"use client";

import { useState, useEffect, useCallback } from "react";
import { submitReflection, getReflectionStatus } from "@/lib/api";
import type { ReflectionResponse, ReflectionStatusResponse } from "@/types/api";

export function useReflection() {
  const [status, setStatus] = useState<ReflectionStatusResponse | null>(null);
  const [result, setResult] = useState<ReflectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getReflectionStatus();
      setStatus(s);
    } catch {
      // Non-fatal — status is optional
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const submit = useCallback(async (content: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitReflection(content);
      setResult(res);
      setStatus((s) => s ? { ...s, completed_today: true, streak_days: res.streak_days } : s);
    } catch (err) {
      if (err instanceof Error && err.message.includes("409")) {
        setError("You've already reflected today. Come back tomorrow!");
      } else {
        setError(err instanceof Error ? err.message : "Failed to submit reflection.");
      }
    } finally {
      setSubmitting(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { status, result, loading, submitting, error, submit, reset };
}
