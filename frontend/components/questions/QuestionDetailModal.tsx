"use client";

import { useState, useEffect, useCallback } from "react";
import { X, Save, Trash2, RotateCcw, Play, Clock, ChevronDown } from "lucide-react";
import { getQuestionDetail, updateQuestion, deleteQuestion, rescheduleQuestion } from "@/lib/api";
import type { QuestionDetail } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { useToast } from "@/hooks/use-toast";
import { formatRelativeDate } from "@/lib/utils";

interface QuestionDetailModalProps {
  questionId: string;
  onClose: () => void;
  onUpdated: () => void;
}

const typeOptions = ["recall", "cloze", "explain", "connection"];

const typeColors: Record<string, string> = {
  recall: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  cloze: "bg-purple-500/15 text-purple-600 dark:text-purple-400",
  explain: "bg-green-500/15 text-green-600 dark:text-green-400",
  connection: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
};

const stateLabels: Record<number, string> = {
  0: "New",
  1: "Learning",
  2: "Review",
  3: "Relearning",
};

const ratingLabels: Record<number, { label: string; className: string }> = {
  1: { label: "Again", className: "text-rating-again" },
  2: { label: "Hard", className: "text-rating-hard" },
  3: { label: "Good", className: "text-rating-good" },
  4: { label: "Easy", className: "text-rating-easy" },
};

export function QuestionDetailModal({ questionId, onClose, onUpdated }: QuestionDetailModalProps) {
  const { toast } = useToast();
  const [detail, setDetail] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Editable fields
  const [questionText, setQuestionText] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [mnemonicHint, setMnemonicHint] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [dirty, setDirty] = useState(false);

  // Reschedule
  const [showReschedule, setShowReschedule] = useState(false);
  const [postponeDays, setPostponeDays] = useState(3);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await getQuestionDetail(questionId);
      setDetail(d);
      setQuestionText(d.question_text);
      setAnswerText(d.answer_text);
      setMnemonicHint(d.mnemonic_hint || "");
      setQuestionType(d.question_type);
      setDirty(false);
    } catch {
      toast({ title: "Failed to load question details", variant: "destructive" });
      onClose();
    } finally {
      setLoading(false);
    }
  }, [questionId, toast, onClose]);

  useEffect(() => {
    load();
  }, [load]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const markDirty = () => setDirty(true);

  const handleSave = async () => {
    if (!dirty) return;
    setSaving(true);
    try {
      await updateQuestion(questionId, {
        question_text: questionText,
        answer_text: answerText,
        mnemonic_hint: mnemonicHint || undefined,
        question_type: questionType,
      });
      toast({ title: "Question updated", variant: "success" as never });
      setDirty(false);
      onUpdated();
      load();
    } catch {
      toast({ title: "Failed to update question", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this question? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deleteQuestion(questionId);
      toast({ title: "Question deleted", variant: "success" as never });
      onUpdated();
      onClose();
    } catch {
      toast({ title: "Failed to delete question", variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const handleReschedule = async (action: string, days?: number) => {
    try {
      await rescheduleQuestion(questionId, action, days);
      toast({ title: `Question ${action === "reset" ? "reset" : action === "review_now" ? "scheduled for now" : `postponed ${days}d`}`, variant: "success" as never });
      setShowReschedule(false);
      onUpdated();
      load();
    } catch {
      toast({ title: "Failed to reschedule", variant: "destructive" });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="relative h-full w-full max-w-lg overflow-y-auto bg-background border-l border-border shadow-xl animate-in slide-in-from-right-5 duration-200">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background px-4 py-3">
          <h2 className="text-lg font-semibold">Question Details</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading ? (
          <LoadingSpinner message="Loading details..." />
        ) : detail ? (
          <div className="p-4 space-y-5">
            {/* Question text */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Question</label>
              <textarea
                value={questionText}
                onChange={(e) => { setQuestionText(e.target.value); markDirty(); }}
                rows={3}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
            </div>

            {/* Answer text */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Answer</label>
              <textarea
                value={answerText}
                onChange={(e) => { setAnswerText(e.target.value); markDirty(); }}
                rows={3}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
            </div>

            {/* Mnemonic hint */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Mnemonic Hint</label>
              <input
                type="text"
                value={mnemonicHint}
                onChange={(e) => { setMnemonicHint(e.target.value); markDirty(); }}
                placeholder="Optional memory aid..."
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Question type */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Type</label>
              <select
                value={questionType}
                onChange={(e) => { setQuestionType(e.target.value); markDirty(); }}
                className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {typeOptions.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>

            {/* Save button */}
            {dirty && (
              <Button onClick={handleSave} disabled={saving} className="gap-1.5 w-full">
                <Save className="h-4 w-4" />
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            )}

            <Separator />

            {/* FSRS Info */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Scheduling Info</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-lg bg-secondary/50 p-2.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">State</p>
                  <p className="font-medium">{stateLabels[detail.state] ?? detail.state}</p>
                </div>
                <div className="rounded-lg bg-secondary/50 p-2.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Due</p>
                  <p className="font-medium">{new Date(detail.due).toLocaleDateString()}</p>
                </div>
                {detail.stability !== undefined && detail.stability !== null && (
                  <div className="rounded-lg bg-secondary/50 p-2.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Stability</p>
                    <p className="font-medium">{detail.stability.toFixed(1)}d</p>
                  </div>
                )}
                {detail.difficulty !== undefined && detail.difficulty !== null && (
                  <div className="rounded-lg bg-secondary/50 p-2.5">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Difficulty</p>
                    <p className="font-medium">{detail.difficulty.toFixed(2)}</p>
                  </div>
                )}
              </div>

              {detail.accuracy_rate !== undefined && detail.accuracy_rate !== null && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Accuracy Rate</span>
                    <span className="font-medium">{(detail.accuracy_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-secondary overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${detail.accuracy_rate * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <Separator />

            {/* Reschedule */}
            <div className="space-y-2">
              <button
                onClick={() => setShowReschedule(!showReschedule)}
                className="flex items-center gap-1.5 text-sm font-semibold"
              >
                <Clock className="h-4 w-4" />
                Reschedule
                <ChevronDown className={`h-3.5 w-3.5 transition-transform ${showReschedule ? "rotate-180" : ""}`} />
              </button>
              {showReschedule && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleReschedule("reset")} className="gap-1">
                    <RotateCcw className="h-3.5 w-3.5" />
                    Reset
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleReschedule("review_now")} className="gap-1">
                    <Play className="h-3.5 w-3.5" />
                    Review Now
                  </Button>
                  <div className="flex items-center gap-1.5">
                    <Button size="sm" variant="outline" onClick={() => handleReschedule("postpone", postponeDays)}>
                      Postpone
                    </Button>
                    <input
                      type="number"
                      min={1}
                      max={365}
                      value={postponeDays}
                      onChange={(e) => setPostponeDays(Number(e.target.value))}
                      className="w-16 rounded-lg border border-input bg-background px-2 py-1 text-sm text-center focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <span className="text-xs text-muted-foreground">days</span>
                  </div>
                </div>
              )}
            </div>

            {/* Source context */}
            {(detail.extracted_point_content || detail.capture_raw_text) && (
              <>
                <Separator />
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Source Context</h3>
                  {detail.extracted_point_content && (
                    <div className="rounded-lg bg-secondary/50 p-3">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Extracted Point</p>
                      <p className="text-sm text-muted-foreground">{detail.extracted_point_content}</p>
                    </div>
                  )}
                  {detail.capture_raw_text && (
                    <div className="rounded-lg bg-secondary/50 p-3">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Original Capture</p>
                      <p className="text-sm text-muted-foreground line-clamp-6">{detail.capture_raw_text}</p>
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Review history */}
            {detail.review_logs.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Review History ({detail.review_logs.length})</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {detail.review_logs.map((log, i) => {
                      const r = ratingLabels[log.rating] || { label: `${log.rating}`, className: "" };
                      return (
                        <div key={i} className="rounded-lg border border-border p-3 text-sm space-y-1">
                          <div className="flex items-center justify-between">
                            <span className={`font-medium ${r.className}`}>{r.label}</span>
                            <span className="text-xs text-muted-foreground">{formatRelativeDate(log.reviewed_at)}</span>
                          </div>
                          {log.user_answer && (
                            <p className="text-xs"><span className="text-muted-foreground">Answer:</span> {log.user_answer}</p>
                          )}
                          {log.ai_feedback && (
                            <p className="text-xs"><span className="text-muted-foreground">Feedback:</span> {log.ai_feedback}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}

            <Separator />

            {/* Delete */}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
              className="gap-1.5 w-full"
            >
              <Trash2 className="h-4 w-4" />
              {deleting ? "Deleting..." : "Delete Question"}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
