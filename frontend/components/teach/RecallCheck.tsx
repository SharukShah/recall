"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";

interface RecallCheckProps {
  question: string;
  onSubmit: (answer: string) => void;
  isLoading: boolean;
}

export function RecallCheck({ question, onSubmit, isLoading }: RecallCheckProps) {
  const [answer, setAnswer] = useState("");

  const handleSubmit = () => {
    if (!answer.trim() || isLoading) return;
    onSubmit(answer);
    setAnswer("");
  };

  return (
    <div className="space-y-3 p-4 bg-muted/50 rounded-lg border">
      <p className="text-sm font-medium">Recall Check</p>
      <p className="text-sm">{question}</p>
      <Textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Type your answer..."
        rows={3}
        disabled={isLoading}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            handleSubmit();
          }
        }}
      />
      <Button
        onClick={handleSubmit}
        disabled={!answer.trim() || isLoading}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Evaluating...
          </>
        ) : (
          "Submit Answer"
        )}
      </Button>
    </div>
  );
}
