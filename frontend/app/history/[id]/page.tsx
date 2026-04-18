import { CaptureDetailView } from "@/components/history/CaptureDetailView";

interface CaptureDetailPageProps {
  params: { id: string };
}

export default function CaptureDetailPage({ params }: CaptureDetailPageProps) {
  return <CaptureDetailView captureId={params.id} />;
}
