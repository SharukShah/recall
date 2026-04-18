"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { CheckCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { CaptureResponse } from "@/types/api";

interface CaptureResultProps {
  result: CaptureResponse;
  onCaptureAnother: () => void;
}

export function CaptureResult({ result, onCaptureAnother }: CaptureResultProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const isSuccess = result.status === "complete";
  const isNoFacts = result.status === "no_facts";

  useEffect(() => {
    cardRef.current?.focus();
  }, []);

  return (
    <Card
      ref={cardRef}
      tabIndex={-1}
      className={`outline-none animate-in fade-in slide-in-from-top-2 duration-200 ${isSuccess ? "border-green-200 dark:border-green-800" : "border-yellow-200 dark:border-yellow-800"}`}
    >
      <CardContent className="pt-6 space-y-4">
        <div className="flex items-center gap-3">
          {isSuccess ? (
            <CheckCircle className="h-6 w-6 text-green-600" />
          ) : (
            <AlertTriangle className="h-6 w-6 text-yellow-600" />
          )}
          <p className="text-lg font-semibold">
            {isSuccess
              ? "Captured successfully!"
              : isNoFacts
              ? "No reviewable facts found"
              : "Saved but extraction failed"}
          </p>
        </div>

        {isSuccess && (
          <div className="space-y-1 text-sm">
            <p>{result.facts_count} facts extracted</p>
            <p>{result.questions_count} questions generated</p>
            <p className="text-muted-foreground">
              Processing time: {(result.processing_time_ms / 1000).toFixed(1)}s
            </p>
          </div>
        )}

        {isNoFacts && (
          <p className="text-sm text-muted-foreground">
            Try being more specific or adding more detail.
          </p>
        )}

        {result.status === "extraction_failed" && (
          <p className="text-sm text-muted-foreground">
            Your text was saved. Extraction will be retried.
          </p>
        )}

        {result.message && (
          <p className="text-sm text-muted-foreground">{result.message}</p>
        )}

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Button variant="outline" onClick={onCaptureAnother} className="flex-1">
            Capture Another
          </Button>
          <Button asChild className="flex-1">
            <Link href="/review">Start Review</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
