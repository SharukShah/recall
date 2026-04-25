"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { LociForm } from "@/components/loci/LociForm";
import { useRouter } from "next/navigation";
import { useToast } from "@/hooks/use-toast";
import type { LociCreateRequest } from "@/types/loci";

export default function CreateLociPage() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (data: LociCreateRequest) => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/loci/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Failed to create memory palace");
      }

      const result = await response.json();
      toast({
        title: "Memory palace created!",
        description: `${result.total_locations} items placed in ${result.palace_theme}`,
      });
      router.push(`/loci/${result.session_id}`);
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create memory palace",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <PageHeader title="Create Memory Palace" />
      <LociForm onSubmit={handleSubmit} disabled={loading} />
    </div>
  );
}
