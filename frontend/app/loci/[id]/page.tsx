"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { PageHeader } from "@/components/shared/PageHeader";
import { WalkthroughPlayer } from "@/components/loci/WalkthroughPlayer";
import { RecallTest } from "@/components/loci/RecallTest";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { LociCreateResponse, LociRecallResponse } from "@/types/loci";

export default function LociSessionPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const [session, setSession] = useState<LociCreateResponse | null>(null);
  const [recallResult, setRecallResult] = useState<LociRecallResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  const fetchSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/loci/${sessionId}`);
      if (!response.ok) throw new Error("Failed to fetch session");
      const data = await response.json();
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session");
    } finally {
      setLoading(false);
    }
  };

  const handleRecallSubmit = async (items: string[]) => {
    setSubmitting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/loci/${sessionId}/recall`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recalled_items: items }),
      });
      if (!response.ok) throw new Error("Failed to submit recall");
      const result = await response.json();
      setRecallResult(result);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to submit recall");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Memory Palace" />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="space-y-6">
        <PageHeader title="Memory Palace" />
        <ErrorState message={error || "Session not found"} onRetry={fetchSession} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title={session.title} />

      <Tabs defaultValue="walkthrough" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="walkthrough">Walkthrough</TabsTrigger>
          <TabsTrigger value="recall">Test Recall</TabsTrigger>
        </TabsList>
        <TabsContent value="walkthrough" className="space-y-4">
          <WalkthroughPlayer
            walkthrough={session.walkthrough}
            fullNarration={session.full_narration}
          />
        </TabsContent>
        <TabsContent value="recall" className="space-y-4">
          <RecallTest
            totalItems={session.total_locations}
            onSubmit={handleRecallSubmit}
            result={recallResult || undefined}
            disabled={submitting}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
