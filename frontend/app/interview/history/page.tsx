import { PageHeader } from "@/components/shared/PageHeader";
import { InterviewHistory } from "@/components/interview/InterviewHistory";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function InterviewHistoryPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Interview History" />
        <Link href="/interview">
          <Button variant="ghost" size="sm">← Back</Button>
        </Link>
      </div>
      <InterviewHistory />
    </div>
  );
}
