"use client";

import { useState } from "react";
import { Loader2, Sunset } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ReflectionFormProps {
  onSubmit: (content: string) => void;
  isSubmitting: boolean;
}

export function ReflectionForm({ onSubmit, isSubmitting }: ReflectionFormProps) {
  const [content, setContent] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || isSubmitting) return;
    onSubmit(content.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="reflection" className="text-sm font-medium">
          What did you learn today?
        </label>
        <Textarea
          id="reflection"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Today I learned that..."
          rows={6}
          disabled={isSubmitting}
          className="resize-y min-h-[150px]"
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
              e.preventDefault();
              handleSubmit(e as unknown as React.FormEvent);
            }
          }}
        />
        <p className="text-xs text-muted-foreground text-right">
          {content.length.toLocaleString()} / 10,000
        </p>
      </div>
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!content.trim() || isSubmitting}
      >
        {isSubmitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing reflection...
          </>
        ) : (
          <>
            <Sunset className="mr-2 h-4 w-4" />
            Submit Reflection
          </>
        )}
      </Button>
    </form>
  );
}
