"use client";

import { useState, type RefObject } from "react";
import { Lightbulb, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import type { ReviewQuestion } from "@/types/api";

interface QuestionCardProps {
  question: ReviewQuestion;
  answer: string;
  onAnswerChange: (answer: string) => void;
  onCheckAnswer: () => void;
  isEvaluating: boolean;
  answerRef?: RefObject<HTMLTextAreaElement>;
}

export function QuestionCard({
  question,
  answer,
  onAnswerChange,
  onCheckAnswer,
  isEvaluating,
  answerRef,
}: QuestionCardProps) {
  const [showHint, setShowHint] = useState(false);

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6 space-y-4">
          <Badge variant="secondary" className="uppercase text-xs">
            {question.question_type}
          </Badge>
          <p className="text-base font-medium leading-relaxed">
            {question.question_text}
          </p>
          {question.mnemonic_hint && (
            <div>
              <button
                onClick={() => setShowHint(!showHint)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Lightbulb className="h-4 w-4" />
                <span>Hint</span>
                {showHint ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
              {showHint && (
                <p className="mt-2 text-sm text-muted-foreground pl-6">
                  {question.mnemonic_hint}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <label htmlFor="answer" className="text-sm font-medium">
          Your answer
        </label>
        <Textarea
          id="answer"
          ref={answerRef}
          value={answer}
          onChange={(e) => onAnswerChange(e.target.value)}
          placeholder="Type your answer..."
          rows={3}
          disabled={isEvaluating}
        />
        <Button
          onClick={onCheckAnswer}
          disabled={!answer.trim() || isEvaluating}
          className="w-full"
          size="lg"
        >
          {isEvaluating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Evaluating...
            </>
          ) : (
            "Check Answer"
          )}
        </Button>
      </div>
    </div>
  );
}
