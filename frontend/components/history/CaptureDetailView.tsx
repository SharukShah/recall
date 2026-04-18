"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getCaptureDetail } from "@/lib/api";
import type { CaptureDetail } from "@/types/api";
import { formatRelativeDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorState } from "@/components/shared/ErrorState";
import { FactItem } from "./FactItem";
import { QuestionItem } from "./QuestionItem";

interface CaptureDetailViewProps {
  captureId: string;
}

export function CaptureDetailView({ captureId }: CaptureDetailViewProps) {
  const router = useRouter();
  const [capture, setCapture] = useState<CaptureDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const goBack = useCallback(() => router.push("/history"), [router]);

  const load = () => {
    setLoading(true);
    setError(null);
    getCaptureDetail(captureId)
      .then(setCapture)
      .catch((err) => setError(err instanceof Error ? err.message : "Capture not found"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureId]);

  // Escape / Backspace to go back
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "Escape" || e.key === "Backspace") {
        e.preventDefault();
        goBack();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goBack]);

  if (loading) return <LoadingSpinner message="Loading capture..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!capture) return <ErrorState message="Capture not found" onRetry={() => router.push("/history")} />;

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        onClick={() => router.push("/history")}
        className="gap-2 -ml-2"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Button>

      <p className="text-sm text-muted-foreground">
        Captured {formatRelativeDate(capture.created_at)}
      </p>

      <Card>
        <CardContent className="pt-6">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{capture.raw_text}</p>
        </CardContent>
      </Card>

      {capture.why_it_matters && (
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">Why it matters:</p>
          <p className="text-sm italic">&ldquo;{capture.why_it_matters}&rdquo;</p>
        </div>
      )}

      <Separator />

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">
          Extracted Facts ({capture.facts.length})
        </h2>
        {capture.facts.length > 0 ? (
          <ul className="space-y-1">
            {capture.facts.map((fact) => (
              <FactItem key={fact.id} fact={fact} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No facts extracted.</p>
        )}
      </div>

      <Separator />

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">
          Generated Questions ({capture.questions.length})
        </h2>
        {capture.questions.length > 0 ? (
          <ul className="divide-y divide-border">
            {capture.questions.map((q, i) => (
              <QuestionItem key={q.id} question={q} index={i} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No questions generated.</p>
        )}
      </div>
    </div>
  );
}
