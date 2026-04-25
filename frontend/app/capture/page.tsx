import { PageHeader } from "@/components/shared/PageHeader";
import { CaptureForm } from "@/components/capture/CaptureForm";

export default function CapturePage() {
  return (
    <div className="space-y-4">
      <div>
        <PageHeader title="Capture" />
        <p className="text-sm text-muted-foreground mt-1">Paste, type, or speak what you learned. AI extracts key facts and creates review questions.</p>
      </div>
      <CaptureForm />
    </div>
  );
}
