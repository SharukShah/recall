"use client";

import { useState } from "react";
import { Brain, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { createCapture } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type { CaptureResponse } from "@/types/api";
import { CaptureResult } from "./CaptureResult";
import { VoiceCaptureButton } from "./VoiceCaptureButton";

export function CaptureForm() {
  const [rawText, setRawText] = useState("");
  const [whyItMatters, setWhyItMatters] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CaptureResponse | null>(null);
  const [sourceType, setSourceType] = useState<"text" | "voice">("text");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim() || submitting) return;

    setSubmitting(true);
    try {
      const response = await createCapture({
        raw_text: rawText.slice(0, 50_000),
        source_type: sourceType,
        why_it_matters: whyItMatters || undefined,
      });
      setResult(response);
      setRawText("");
      setWhyItMatters("");
      setSourceType("text");
      if (response.status === "complete") {
        toast({ title: "Knowledge captured!", variant: "success" });
      }
    } catch (err) {
      toast({
        title: "Failed to capture",
        description: err instanceof Error ? err.message : "Check your connection.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCaptureAnother = () => {
    setResult(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  if (result) {
    return <CaptureResult result={result} onCaptureAnother={handleCaptureAnother} />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="raw-text" className="text-sm font-medium">
          What did you learn?
        </label>
        <Textarea
          id="raw-text"
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Paste or type what you learned..."
          rows={6}
          disabled={submitting}
          aria-label="What did you learn? Enter the text you want to capture."
          className="resize-y min-h-[150px]"
        />
        <div className="flex items-center justify-between">
          <VoiceCaptureButton
            onTranscript={(text) => {
              setRawText((prev) => (prev ? prev + " " + text : text));
              setSourceType("voice");
            }}
            disabled={submitting}
          />
          <p className="text-xs text-muted-foreground">
            {rawText.length.toLocaleString()} / 50,000 characters
          </p>
        </div>
        {rawText.length > 0 && rawText.length < 10 && (
          <p className="text-xs text-yellow-600">
            That&apos;s very short. Add more detail for better extraction.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="why-it-matters" className="text-sm font-medium">
          Why does this matter to you?{" "}
          <span className="text-muted-foreground font-normal">(optional)</span>
        </label>
        <Input
          id="why-it-matters"
          value={whyItMatters}
          onChange={(e) => setWhyItMatters(e.target.value)}
          placeholder="e.g., Needed for the project I'm building"
          disabled={submitting}
          aria-label="Why does this matter to you? Optional."
        />
      </div>

      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!rawText.trim() || submitting}
        aria-busy={submitting}
      >
        {submitting ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Extracting knowledge...
          </>
        ) : (
          <>
            <Brain className="mr-2 h-4 w-4" />
            Capture Knowledge
          </>
        )}
      </Button>
    </form>
  );
}
