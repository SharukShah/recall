"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Search, FileText, Mic, Link as LinkIcon, SlidersHorizontal, Tag } from "lucide-react";
import { listCaptures, getAllTags } from "@/lib/api";
import type { CaptureListItem, TagItem } from "@/types/api";
import { CaptureCard } from "@/components/history/CaptureCard";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/PageHeader";

const PAGE_SIZE = 20;

const sourceFilters = [
  { key: "all", label: "All", icon: null },
  { key: "text", label: "Text", icon: FileText },
  { key: "voice", label: "Voice", icon: Mic },
  { key: "url", label: "URL", icon: LinkIcon },
] as const;

type SourceFilter = (typeof sourceFilters)[number]["key"];

export default function HistoryPage() {
  const [captures, setCaptures] = useState<CaptureListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [allTags, setAllTags] = useState<TagItem[]>([]);

  const load = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const [data, tags] = await Promise.all([listCaptures(100, 0), getAllTags()]);
      setCaptures(data);
      setAllTags(tags);
      setHasMore(data.length === 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load captures");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const data = await listCaptures(100, captures.length);
      setCaptures((prev) => [...prev, ...data]);
      setHasMore(data.length === 100);
    } catch {
      // Silently fail on load more
    } finally {
      setLoadingMore(false);
    }
  };

  const filtered = useMemo(() => {
    let result = captures;
    if (sourceFilter !== "all") {
      result = result.filter((c) => c.source_type === sourceFilter);
    }
    if (tagFilter) {
      result = result.filter((c) => c.tags?.includes(tagFilter));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((c) => c.raw_text.toLowerCase().includes(q));
    }
    return result;
  }, [captures, sourceFilter, tagFilter, searchQuery]);

  if (loading) return <LoadingSpinner message="Loading captures..." />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <PageHeader title="History" />

      {/* Search + Filter bar */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search captures..."
            className="w-full rounded-lg border border-input bg-background pl-9 pr-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex items-center gap-1.5">
          {sourceFilters.map((f) => (
            <button
              key={f.key}
              onClick={() => setSourceFilter(f.key)}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                sourceFilter === f.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {f.icon && <f.icon className="h-3 w-3" />}
              {f.label}
            </button>
          ))}
          <span className="ml-auto text-xs text-muted-foreground">
            {filtered.length} capture{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {allTags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <Tag className="h-3 w-3 text-muted-foreground" />
            <button
              onClick={() => setTagFilter(null)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                !tagFilter
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              All
            </button>
            {allTags.map((t) => (
              <button
                key={t.name}
                onClick={() => setTagFilter(tagFilter === t.name ? null : t.name)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  tagFilter === t.name
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground"
                }`}
              >
                {t.name} ({t.count})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      {captures.length === 0 ? (
        <EmptyState
          message="No captures yet"
          subMessage="Start by capturing something you learned!"
          cta={{ label: "Capture Knowledge", href: "/capture" }}
        />
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          No captures match your search.
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((capture) => (
            <CaptureCard key={capture.id} capture={capture} />
          ))}
          {hasMore && !searchQuery && sourceFilter === "all" && (
            <div className="flex justify-center pt-4">
              <Button variant="outline" size="sm" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Load more"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
