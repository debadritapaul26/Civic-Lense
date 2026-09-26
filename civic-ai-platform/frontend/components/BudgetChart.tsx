"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_COLORS } from "@/lib/chartColors";

export type BudgetAllocation = {
  label: string;
  amount: number;
};

type BudgetChartProps = {
  allocations: BudgetAllocation[];
};

export default function BudgetChart({ allocations }: BudgetChartProps) {
  if (!allocations.length) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl bg-mist text-sm text-slate-500">
        No location allocations were returned.
      </div>
    );
  }

  return (
    <div className="h-80 w-full animate-rise-in">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={allocations}
          margin={{ top: 12, right: 12, left: 0, bottom: allocations.length > 5 ? 56 : 8 }}
        >
          <defs>
            <linearGradient id="allocationBarGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#23aaa4" />
              <stop offset="100%" stopColor={CHART_COLORS.teal} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART_COLORS.grid} vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            interval={0}
            angle={allocations.length > 5 ? -35 : 0}
            textAnchor={allocations.length > 5 ? "end" : "middle"}
            height={allocations.length > 5 ? 64 : 24}
            tickFormatter={(label: string) => label.length > 34 ? `${label.slice(0, 31)}…` : label}
            tick={{ fill: CHART_COLORS.ink, fontSize: 11 }}
          />
          <YAxis axisLine={false} tickLine={false} width={48} />
          <Tooltip
            cursor={{ fill: "rgba(17, 125, 120, 0.08)" }}
            contentStyle={{ border: "1px solid rgba(17, 125, 120, 0.16)", borderRadius: 14, boxShadow: "0 12px 32px rgba(18, 36, 58, 0.14)", padding: "10px 14px" }}
            labelStyle={{ color: CHART_COLORS.ink, fontWeight: 700, marginBottom: 4 }}
            itemStyle={{ color: CHART_COLORS.teal, fontWeight: 700 }}
            formatter={(value: number) => [`₹${value.toFixed(2)} cr`, "Allocated"]}
          />
          <Bar
            dataKey="amount"
            fill="url(#allocationBarGradient)"
            radius={[10, 10, 2, 2]}
            isAnimationActive
            animationBegin={160}
            animationDuration={1250}
            animationEasing="ease-out"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
