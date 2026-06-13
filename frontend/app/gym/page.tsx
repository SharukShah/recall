import { PageHeader } from "@/components/shared/PageHeader";
import { MemoryGym } from "@/components/gym/MemoryGym";

export default function GymPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Memory Gym" />
      <MemoryGym />
    </div>
  );
}
