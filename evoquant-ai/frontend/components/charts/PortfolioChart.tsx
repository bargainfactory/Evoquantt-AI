"use client";

import dynamic from "next/dynamic";
import type { Data, Layout } from "plotly.js";
import { usePortfolioHistory } from "@/hooks/usePortfolio";
import { formatCurrency } from "@/lib/utils";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface PortfolioChartProps {
  days?: number;
  height?: number;
}

export function PortfolioChart({ days = 30, height = 200 }: PortfolioChartProps) {
  const { data, isLoading } = usePortfolioHistory(days);

  if (isLoading) {
    return (
      <div style={{ height }} className="flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-muted-foreground text-sm">
        No portfolio history yet
      </div>
    );
  }

  const timestamps = data.map((d: { timestamp: string }) => d.timestamp);
  const values = data.map((d: { total_value: number }) => d.total_value);
  const startVal = values[0];
  const isPositive = values[values.length - 1] >= startVal;

  const chartData: Data[] = [
    {
      type: "scatter",
      mode: "lines",
      x: timestamps,
      y: values,
      fill: "tozeroy",
      fillcolor: isPositive ? "rgba(0,208,156,0.08)" : "rgba(255,75,75,0.08)",
      line: { color: isPositive ? "#00D09C" : "#FF4B4B", width: 2 },
      hovertemplate: "%{x}<br>%{y:$,.2f}<extra></extra>",
    },
  ];

  const layout: Partial<Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#8B949E", size: 10 },
    xaxis: { showgrid: false, zeroline: false, showticklabels: false },
    yaxis: { showgrid: false, zeroline: false, tickformat: "$,.0f" },
    margin: { t: 5, r: 5, b: 5, l: 50 },
    height,
    hovermode: "x unified",
  };

  return (
    <Plot
      data={chartData}
      layout={layout}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: "100%" }}
    />
  );
}

// Allocation donut chart
export function AllocationChart({ allocations }: { allocations: Array<{ symbol: string; weight: number; value: number }> }) {
  if (!allocations?.length) return null;

  const data: Data[] = [
    {
      type: "pie",
      labels: allocations.map((a) => a.symbol),
      values: allocations.map((a) => a.value),
      hole: 0.6,
      textinfo: "label+percent",
      textfont: { color: "#8B949E", size: 10 },
      marker: {
        colors: ["#00D09C", "#4A9EFF", "#8B5CF6", "#F59E0B", "#EC4899", "#10B981", "#6366F1"],
        line: { color: "#0D1117", width: 2 },
      },
    },
  ];

  const layout: Partial<Layout> = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#8B949E" },
    margin: { t: 20, r: 20, b: 20, l: 20 },
    height: 240,
    showlegend: false,
  };

  return (
    <Plot data={data} layout={layout} config={{ responsive: true, displayModeBar: false }} style={{ width: "100%" }} />
  );
}
