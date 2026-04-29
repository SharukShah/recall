import { ReviewSession } from "@/components/review/ReviewSession";
import { Suspense } from "react";

export default function ReviewPage() {
  return (
    <Suspense>
      <ReviewSession />
    </Suspense>
  );
}
