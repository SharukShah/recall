"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { MasteryDistribution } from "@/types/analytics";

interface MasteryDonutProps {
  data: MasteryDistribution;
}

const COLORS = {
  new: "#3b82f6",
  learning: "#f59e0b",
  review: "#10b981",
  relearning: "#ef4444",
};

const LABELS = {
  new: "New",
  learning: "Learning",
  review: "Mastered",
  relearning: "Relearning",
};

export function MasteryDonut({ data }: MasteryDonutProps) {
  const chartData = [
    { name: LABELS.new, value: data.new, color: COLORS.new },
    { name: LABELS.learning, value: data.learning, color: COLORS.learning },
    { name: LABELS.review, value: data.review, color: COLORS.review },
    { name: LABELS.relearning, value: data.relearning, color: COLORS.relearning },
  ].filter((item) => item.value > 0);

  const total = data.new + data.learning + data.review + data.relearning;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mastery Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              fill="#8884d8"
              paddingAngle={2}
              dataKey="value"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
        <div className="text-center mt-4">
          <p className="text-sm text-muted-foreground">
            Total Questions: <span className="font-semibold">{total}</span>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
