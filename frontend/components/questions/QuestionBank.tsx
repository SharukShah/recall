"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, ChevronLeft, ChevronRight, Trash2, RotateCcw } from "lucide-react";
import { listQuestions, getQuestionStats, bulkDeleteQuestions } from "@/lib/api";
import type { QuestionListItem, QuestionStatsSummary, QuestionDetail } from "@/types/api";
import { QuestionRow } from "./QuestionRow";
import { QuestionDetailModal } from "./QuestionDetailModal";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/hooks/use-toast";

const PAGE_SIZE = 20;

const typeFilters = [
  { key: "", label: "All" },
  { key: "recall", label: "Recall" },
  { key: "cloze", label: "Cloze" },
  { key: "explain", label: "Explain" },
  { key: "connection", label: "Connection" },
] as const;

const stateFilters = [
  { key: -1, label: "All" },
  { key: 0, label: "New" },
  { key: 1, label: "Learning" },
  { key: 2, label: "Review" },
  { key: 3, label: "Relearning" },
] as const;

const sortOptions = [
  { key: "created_at", order: "desc", label: "Newest first" },
  { key: "due", order: "asc", label: "Due soonest" },
  { key: "difficulty", order: "desc", label: "Hardest first" },
  { key: "stability", order: "asc", label: "Lowest stability" },
] as const;

const stateLabels: Record<number, string> = {
  0: "New",
  1: "Learning",
  2: "Review",
  3: "Relearning",
};

export function QuestionBank() {
  const { toast } = useToast();
  const [questions, setQuestions] = useState<QuestionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<QuestionStatsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [stateFilter, setStateFilter] = useState(-1);
  const [sortIdx, setSortIdx] = useState(0);

  // Selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Detail modal
  const [detailId, setDetailId] = useState<string | null>(null);

  // Debounce search
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    debounceRef.current = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(debounceRef.current);
  }, [searchQuery]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
    setSelected(new Set());
  }, [debouncedSearch, typeFilter, stateFilter, sortIdx]);

  const fetchQuestions = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const sort = sortOptions[sortIdx];
      const data = await listQuestions({
        limit: PAGE_SIZE,
        offset,
        search: debouncedSearch || undefined,
        question_type: typeFilter || undefined,
        state: stateFilter >= 0 ? stateFilter : undefined,
        sort: sort.key,
        order: sort.order,
      });
      setQuestions(data.questions);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load questions");
    } finally {
      setLoading(false);
    }
  }, [offset, debouncedSearch, typeFilter, stateFilter, sortIdx]);

  const fetchStats = useCallback(async () => {
    try {
      const s = await getQuestionStats();
      setStats(s);
    } catch {
      // Stats are non-critical
    }
  }, []);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === questions.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(questions.map((q) => q.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} question${selected.size > 1 ? "s" : ""}? This cannot be undone.`)) return;
    setBulkDeleting(true);
    try {
      const result = await bulkDeleteQuestions(Array.from(selected));
      toast({ title: `Deleted ${result.deleted_count} question${result.deleted_count !== 1 ? "s" : ""}`, variant: "success" as never });
      setSelected(new Set());
      fetchQuestions();
      fetchStats();
    } catch {
      toast({ title: "Failed to delete questions", variant: "destructive" });
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleQuestionUpdated = () => {
    fetchQuestions();
    fetchStats();
  };

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const showingFrom = total > 0 ? offset + 1 : 0;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  if (error && questions.length === 0) {
    return <ErrorState message={error} onRetry={fetchQuestions} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Question Bank" />

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="rounded-lg border border-border bg-card p-3">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-xl font-semibold">{stats.total_questions}</p>
          </div>
          {stats.by_state.map((s) => (
            <div key={s.state} className="rounded-lg border border-border bg-card p-3">
              <p className="text-xs text-muted-foreground">{stateLabels[s.state] ?? `State ${s.state}`}</p>
              <p className="text-xl font-semibold">{s.count}</p>
            </div>
          ))}
          {stats.avg_difficulty !== undefined && stats.avg_difficulty !== null && (
            <div className="rounded-lg border border-border bg-card p-3">
              <p className="text-xs text-muted-foreground">Avg Difficulty</p>
              <p className="text-xl font-semibold">{stats.avg_difficulty.toFixed(2)}</p>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search questions..."
            className="w-full rounded-lg border border-input bg-background pl-9 pr-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground mr-1">Type:</span>
          {typeFilters.map((f) => (
            <button
              key={f.key}
              onClick={() => setTypeFilter(f.key)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                typeFilter === f.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground mr-1">State:</span>
          {stateFilters.map((f) => (
            <button
              key={f.key}
              onClick={() => setStateFilter(f.key)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                stateFilter === f.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.label}
            </button>
          ))}

          <select
            value={sortIdx}
            onChange={(e) => setSortIdx(Number(e.target.value))}
            className="ml-auto rounded-lg border border-input bg-background px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {sortOptions.map((s, i) => (
              <option key={s.key} value={i}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleBulkDelete}
            disabled={bulkDeleting}
            className="gap-1.5"
          >
            <Trash2 className="h-3.5 w-3.5" />
            {bulkDeleting ? "Deleting..." : "Delete Selected"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelected(new Set())}
          >
            Clear
          </Button>
        </div>
      )}

      {/* Results */}
      {loading ? (
        <LoadingSpinner message="Loading questions..." />
      ) : total === 0 ? (
        debouncedSearch || typeFilter || stateFilter >= 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No questions match your filters.
          </div>
        ) : (
          <EmptyState
            message="No questions yet"
            subMessage="Start by capturing some knowledge!"
            cta={{ label: "Capture Knowledge", href: "/capture" }}
          />
        )
      ) : (
        <>
          {/* Select all header */}
          <div className="flex items-center gap-3 px-1">
            <input
              type="checkbox"
              checked={selected.size === questions.length && questions.length > 0}
              onChange={toggleSelectAll}
              className="h-4 w-4 rounded border-input"
            />
            <span className="text-xs text-muted-foreground">
              Showing {showingFrom}–{showingTo} of {total}
            </span>
          </div>

          <div className="space-y-2">
            {questions.map((q) => (
              <QuestionRow
                key={q.id}
                question={q}
                selected={selected.has(q.id)}
                onToggleSelect={toggleSelect}
                onClickDetail={setDetailId}
                onDeleted={handleQuestionUpdated}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                className="gap-1"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset((o) => o + PAGE_SIZE)}
                className="gap-1"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      )}

      {/* Detail modal */}
      {detailId && (
        <QuestionDetailModal
          questionId={detailId}
          onClose={() => setDetailId(null)}
          onUpdated={handleQuestionUpdated}
        />
      )}
    </div>
  );
}
