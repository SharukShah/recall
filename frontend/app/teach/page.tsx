import { PageHeader } from "@/components/shared/PageHeader";
import { TeachSession } from "@/components/teach/TeachSession";

export default function TeachPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Teach Me" />
      <TeachSession />
    </div>
  );
}
