"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Trash2, FileText, Mic, Link as LinkIcon } from "lucide-react";
import { getCaptureDetail, deleteCapture } from "@/lib/api";
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

const sourceConfig: Record<string, { label: string; icon: typeof FileText }> = {
  text: { label: "Text", icon: FileText },
  voice: { label: "Voice", icon: Mic },
  url: { label: "URL", icon: LinkIcon },
};

export function CaptureDetailView({ captureId }: CaptureDetailViewProps) {
  const router = useRouter();
  const [capture, setCapture] = useState<CaptureDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const goBack = useCallback(() => router.push("/history"), [router]);

  const load = () => {
    setLoading(true);
    setError(null);
    getCaptureDetail(captureId)
      .then(setCapture)
      .catch((err) => setError(err instanceof Error ? err.message : "Capture not found"))
      .finally(() => setLoading(false));
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteCapture(captureId);
      router.push("/history");
    } catch (err) {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captureId]);

  // Escape / Backspace to go back
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (showDeleteConfirm) return;
      if (e.key === "Escape" || e.key === "Backspace") {
        e.preventDefault();
        goBack();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goBack, showDeleteConfirm]);

  if (loading) return <LoadingSpinner message="Loading capture..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!capture) return <ErrorState message="Capture not found" onRetry={() => router.push("/history")} />;

  const source = sourceConfig[capture.source_type] || sourceConfig.text;
  const SourceIcon = source.icon;

  return (
    <div className="space-y-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={goBack}
          className="gap-2 -ml-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowDeleteConfirm(true)}
          className="gap-1.5 text-muted-foreground hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </Button>
      </div>

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-3">
          <p className="text-sm font-medium">Delete this capture?</p>
          <p className="text-xs text-muted-foreground">
            This will permanently remove the capture, all extracted facts ({capture.facts.length}), and all generated questions ({capture.questions.length}).
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Yes, delete"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Meta info */}
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium">
          <SourceIcon className="h-3 w-3" />
          {source.label}
        </span>
        <span>Captured {formatRelativeDate(capture.created_at)}</span>
      </div>

      {/* Raw text */}
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{capture.raw_text}</p>
        </CardContent>
      </Card>

      {capture.why_it_matters && (
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Why it matters</p>
          <p className="text-sm italic">&ldquo;{capture.why_it_matters}&rdquo;</p>
        </div>
      )}

      <Separator />

      {/* Facts */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
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

      {/* Questions */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
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
