import { PageHeader } from "@/components/shared/PageHeader";
import { CaptureList } from "@/components/history/CaptureList";

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="History" />
      <CaptureList />
    </div>
  );
}
