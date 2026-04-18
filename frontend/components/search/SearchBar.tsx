"use client";

import { useState, useRef, type FormEvent } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What did I learn about..."
          className="pl-9"
          maxLength={2000}
          disabled={isLoading}
          autoFocus
        />
      </div>
      <Button type="submit" disabled={!query.trim() || isLoading}>
        {isLoading ? "Searching..." : "Search"}
      </Button>
    </form>
  );
}
