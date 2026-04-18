import { PageHeader } from "@/components/shared/PageHeader";
import { CaptureForm } from "@/components/capture/CaptureForm";

export default function CapturePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Capture" />
      <CaptureForm />
    </div>
  );
}
