"use client";

import { Pencil, Trash2, CalendarClock } from "lucide-react";
import { deleteQuestion, rescheduleQuestion } from "@/lib/api";
import type { QuestionListItem } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useState } from "react";

interface QuestionRowProps {
  question: QuestionListItem;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  onClickDetail: (id: string) => void;
  onDeleted: () => void;
}

const typeColors: Record<string, string> = {
  recall: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  explain_back: "bg-purple-500/15 text-purple-600 dark:text-purple-400",
  explain: "bg-green-500/15 text-green-600 dark:text-green-400",
  apply: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  connect: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
};

const stateConfig: Record<number, { label: string; className: string }> = {
  0: { label: "New", className: "bg-gray-500/15 text-gray-600 dark:text-gray-400" },
  1: { label: "Learning", className: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400" },
  2: { label: "Review", className: "bg-blue-500/15 text-blue-600 dark:text-blue-400" },
  3: { label: "Relearning", className: "bg-red-500/15 text-red-600 dark:text-red-400" },
};

const ratingColors: Record<number, string> = {
  1: "text-rating-again",
  2: "text-rating-hard",
  3: "text-rating-good",
  4: "text-rating-easy",
};

function formatDueRelative(dateString: string): { text: string; className: string } {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.round(diffMs / 86400000);

  if (diffDays < -1) return { text: `Overdue ${Math.abs(diffDays)}d`, className: "text-destructive" };
  if (diffDays < 0) return { text: "Overdue", className: "text-destructive" };
  if (diffDays === 0) return { text: "Due now", className: "text-yellow-600 dark:text-yellow-400" };
  if (diffDays === 1) return { text: "Due tomorrow", className: "text-muted-foreground" };
  if (diffDays < 7) return { text: `Due in ${diffDays}d`, className: "text-muted-foreground" };
  if (diffDays < 30) return { text: `Due in ${Math.floor(diffDays / 7)}w`, className: "text-muted-foreground" };
  return { text: `Due in ${Math.floor(diffDays / 30)}mo`, className: "text-muted-foreground" };
}

export function QuestionRow({ question, selected, onToggleSelect, onClickDetail, onDeleted }: QuestionRowProps) {
  const { toast } = useToast();
  const [deleting, setDeleting] = useState(false);

  const typeColor = typeColors[question.question_type] || typeColors.recall;
  const state = stateConfig[question.state] || stateConfig[0];
  const due = formatDueRelative(question.due);
  const ratingColor = question.last_rating ? ratingColors[question.last_rating] || "" : "";

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this question? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deleteQuestion(question.id);
      toast({ title: "Question deleted", variant: "success" as never });
      onDeleted();
    } catch {
      toast({ title: "Failed to delete question", variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div
      className="group flex items-start gap-3 rounded-xl border border-border bg-card p-4 hover:border-primary/30 hover:shadow-sm transition-all cursor-pointer"
      onClick={() => onClickDetail(question.id)}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={(e) => {
          e.stopPropagation();
          onToggleSelect(question.id);
        }}
        onClick={(e) => e.stopPropagation()}
        className="h-4 w-4 rounded border-input shrink-0 mt-1"
      />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-relaxed line-clamp-2">
          {question.question_text}
        </p>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold border-0 ${typeColor}`}>
            {question.question_type === "explain_back" ? "explain back" : question.question_type}
          </span>
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold border-0 ${state.className}`}>
            {state.label}
          </span>
        </div>

        {/* Schedule & Performance row */}
        <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
          <span className={due.className}>
            <CalendarClock className="inline h-3 w-3 mr-0.5 -mt-0.5" />
            {due.text}
          </span>
          <span>{question.review_count} review{question.review_count !== 1 ? "s" : ""}</span>
          {question.last_rating && (
            <span className={`font-medium ${ratingColor}`}>
              Last: {["", "Again", "Hard", "Good", "Easy"][question.last_rating]}
            </span>
          )}
          {question.stability !== undefined && question.stability !== null && (
            <span>Stability: {question.stability < 1 ? `${Math.round(question.stability * 24)}h` : `${Math.round(question.stability)}d`}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => { e.stopPropagation(); onClickDetail(question.id); }}
          className="rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          title="Edit"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="rounded-md p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
