"use client";

import { useState, type RefObject } from "react";
import { Lightbulb, ChevronDown, ChevronUp, Mic, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import type { ReviewQuestion } from "@/types/api";

interface QuestionCardProps {
  question: ReviewQuestion;
  answer: string;
  onAnswerChange: (answer: string) => void;
  onCheckAnswer: () => void;
  isEvaluating: boolean;
  answerRef?: RefObject<HTMLTextAreaElement>;
  onVoiceAnswer?: () => void;
  isRecording?: boolean;
}

export function QuestionCard({
  question,
  answer,
  onAnswerChange,
  onCheckAnswer,
  isEvaluating,
  answerRef,
  onVoiceAnswer,
  isRecording,
}: QuestionCardProps) {
  const [showHint, setShowHint] = useState(false);

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="uppercase text-xs">
              {question.question_type === "explain_back" ? "explain" : question.question_type}
            </Badge>
            {question.question_type === "connection" && (
              <Badge variant="outline" className="text-xs text-primary border-primary">
                Connection
              </Badge>
            )}
          </div>
          <p className="text-base font-medium leading-relaxed">
            {question.question_text}
          </p>
          {question.mnemonic_hint && (
            <div>
              <button
                onClick={() => setShowHint(!showHint)}
                className="flex items-center gap-2 text-sm text-primary/70 hover:text-primary transition-colors"
              >
                <Lightbulb className="h-4 w-4" />
                <span>{showHint ? "Hide hint" : "Show hint"}</span>
                {showHint ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
              {showHint && (
                <p className="mt-2 text-sm text-muted-foreground pl-6 border-l-2 border-primary/20">
                  {question.mnemonic_hint}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label htmlFor="answer" className="text-sm font-medium">
            {question.question_type === "explain_back" ? "Explain in your own words" : "Your answer"}
          </label>
          <span className="text-[11px] text-muted-foreground">
            {answer.length > 0 ? `${answer.length} chars` : question.question_type === "explain_back" ? "2–3 sentences ideal" : "1–2 sentences"}
          </span>
        </div>
        <Textarea
          id="answer"
          ref={answerRef}
          value={answer}
          onChange={(e) => onAnswerChange(e.target.value)}
          placeholder={question.question_type === "explain_back" ? "Explain the concept as if teaching someone else..." : "Type your answer..."}
          rows={question.question_type === "explain_back" ? 5 : 3}
          disabled={isEvaluating}
        />
        <div className="flex gap-2">
          {onVoiceAnswer && (
            <Button
              type="button"
              variant={isRecording ? "destructive" : "outline"}
              onClick={onVoiceAnswer}
              disabled={isEvaluating}
              className="gap-1.5"
              aria-label={isRecording ? "Recording..." : "Speak your answer"}
            >
              <Mic className={`h-4 w-4 ${isRecording ? "animate-pulse" : ""}`} />
              {isRecording ? "Listening..." : "Speak"}
            </Button>
          )}
          <Button
            onClick={onCheckAnswer}
            disabled={!answer.trim() || isEvaluating}
            className="flex-1"
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
    </div>
  );
}
