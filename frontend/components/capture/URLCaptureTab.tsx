"use client";

import { useState } from "react";
import { Globe, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { captureURL } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { CaptureResponse } from "@/types/api";
import { CaptureResult } from "./CaptureResult";

export function URLCaptureTab() {
  const [url, setUrl] = useState("");
  const [whyItMatters, setWhyItMatters] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CaptureResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || submitting) return;

    setSubmitting(true);
    try {
      const response = await captureURL({
        url: url.trim(),
        why_it_matters: whyItMatters || undefined,
      });
      setResult(response);
      setUrl("");
      setWhyItMatters("");
      if (response.status === "complete") {
        toast({ title: "Article captured!", variant: "success" });
      }
    } catch (err) {
      toast({
        title: "Failed to capture URL",
        description: err instanceof Error ? err.message : "Check the URL and try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return <CaptureResult result={result} onCaptureAnother={() => setResult(null)} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="url-input" className="text-sm font-medium">
          Article URL
        </label>
        <Input
          id="url-input"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article"
          disabled={submitting}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="url-why" className="text-sm font-medium">
          Why does this matter?{" "}
          <span className="text-muted-foreground font-normal">(optional)</span>
        </label>
        <Input
          id="url-why"
          value={whyItMatters}
          onChange={(e) => setWhyItMatters(e.target.value)}
          placeholder="e.g., Research for my project"
          disabled={submitting}
        />
      </div>

      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!url.trim() || submitting}
      >
        {submitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Fetching & extracting...
          </>
        ) : (
          <>
            <Globe className="mr-2 h-4 w-4" />
            Capture from URL
          </>
        )}
      </Button>
    </form>
  );
}
