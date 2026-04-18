import { Badge } from "@/components/ui/badge";
import { formatDueDate } from "@/lib/utils";
import type { Question } from "@/types/api";

interface QuestionItemProps {
  question: Question;
  index: number;
}

export function QuestionItem({ question, index }: QuestionItemProps) {
  return (
    <li className="py-3 space-y-1.5">
      <p className="text-sm">
        <span className="text-muted-foreground mr-1">{index + 1}.</span>
        {question.question_text}
      </p>
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-xs">
          {question.question_type}
        </Badge>
        <span className="text-xs text-muted-foreground">
          Due: {formatDueDate(question.due)}
        </span>
      </div>
    </li>
  );
}
