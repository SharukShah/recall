"use client";

import { useState, useCallback } from "react";
import { searchKnowledge } from "@/lib/api";
import type { SearchResponse } from "@/types/api";

export function useKnowledgeSearch() {
  const [data, setData] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await searchKnowledge({ query: query.trim(), limit: 5 });
      setData(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Search failed. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, isLoading, error, search, reset };
}
