"use client";

import { PageHeader } from "@/components/shared/PageHeader";
import { SearchBar } from "@/components/search/SearchBar";
import { SearchResults } from "@/components/search/SearchResults";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { useKnowledgeSearch } from "@/hooks/useKnowledgeSearch";
import { Search } from "lucide-react";

export default function SearchPage() {
  const { data, isLoading, error, search, reset } = useKnowledgeSearch();

  return (
    <div className="space-y-6">
      <PageHeader title="Search Knowledge" />
      <SearchBar onSearch={search} isLoading={isLoading} />

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      )}

      {error && <ErrorState message={error} onRetry={reset} />}

      {data && <SearchResults data={data} />}

      {!data && !isLoading && !error && (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center text-muted-foreground">
          <Search className="h-10 w-10 opacity-40" />
          <p className="text-sm">
            Search your captured knowledge using natural language.
          </p>
        </div>
      )}
    </div>
  );
}
