"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonCard } from "@/components/shared/SkeletonCard";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { Plus, Brain, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { LociListItem } from "@/types/loci";

export default function LociPage() {
  const [sessions, setSessions] = useState<LociListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/loci/`);
      if (!response.ok) throw new Error("Failed to fetch sessions");
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Memory Palace" />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Memory Palace" />
        <ErrorState message={error} onRetry={fetchSessions} />
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="Memory Palace" />
        <EmptyState
          message="No memory palaces yet"
          subMessage="Create your first memory palace to memorize ordered lists using vivid mental imagery."
          cta={{
            label: "Create Memory Palace",
            href: "/loci/create"
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Memory Palace" />
        <Link href="/loci/create">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Create New
          </Button>
        </Link>
      </div>

      <div className="grid gap-4">
        {sessions.map((session) => (
          <Card
            key={session.session_id}
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => router.push(`/loci/${session.session_id}`)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <CardTitle>{session.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {session.palace_theme} • {session.total_locations} items
                  </p>
                </div>
                {session.last_recall_score !== null && (
                  <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    <span className="text-sm font-semibold text-primary">
                      {Math.round((session.last_recall_score / session.total_locations) * 100)}%
                    </span>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Created {new Date(session.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
