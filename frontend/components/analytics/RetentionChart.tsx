"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { RetentionCurveResponse } from "@/types/analytics";

interface RetentionChartProps {
  data: RetentionCurveResponse;
}

export function RetentionChart({ data }: RetentionChartProps) {
  const chartData = data.data_points.map((point) => ({
    week: new Date(point.week_start).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    retention: (point.retention_rate * 100).toFixed(1),
    reviews: point.total_reviews,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Retention Curve</CardTitle>
        <p className="text-sm text-muted-foreground">
          Percentage of reviews rated Good or Easy over time
        </p>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="week" />
            <YAxis label={{ value: "Retention %", angle: -90, position: "insideLeft" }} />
            <Tooltip
              formatter={(value: any, name: string) => [
                name === "retention" ? `${value}%` : value,
                name === "retention" ? "Retention" : "Reviews",
              ]}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="retention"
              stroke="#10b981"
              strokeWidth={2}
              name="Retention %"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
