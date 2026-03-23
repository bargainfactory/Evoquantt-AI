"use client";

import { useEffect, useRef, useState } from "react";
import { useOHLCV, useIndicators } from "@/hooks/useMarketData";
import { cn } from "@/lib/utils";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1wk"];
const PERIOD_MAP: Record<string, string> = {
  "1m": "5d", "5m": "1mo", "15m": "3mo", "1h": "6mo", "4h": "1y", "1d": "2y", "1wk": "5y",
};

interface TradingViewChartProps {
  symbol: string;
  height?: number;
  showIndicators?: boolean;
}

export function TradingViewChart({ symbol, height = 450, showIndicators = true }: TradingViewChartProps) {
  const [interval, setInterval] = useState("1d");
  const [chartType, setChartType] = useState<"candlestick" | "line">("candlestick");
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<unknown>(null);
  const seriesRef = useRef<unknown>(null);
  const period = PERIOD_MAP[interval] || "1y";

  const { data: ohlcv, isLoading } = useOHLCV(symbol, period, interval);
  const { data: indicators } = useIndicators(symbol, period);

  useEffect(() => {
    if (!chartRef.current || typeof window === "undefined") return;
    import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode }) => {
      if (chartInstance.current) {
        (chartInstance.current as { remove: () => void }).remove();
      }
      const chart = createChart(chartRef.current!, {
        width: chartRef.current!.offsetWidth,
        height,
        layout: {
          background: { type: ColorType.Solid, color: "#0D1117" },
          textColor: "#8B949E",
        },
        grid: {
          vertLines: { color: "#161B22" },
          horzLines: { color: "#161B22" },
        },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderColor: "#30363D" },
        timeScale: { borderColor: "#30363D", timeVisible: true },
      });
      chartInstance.current = chart;

      if (chartType === "candlestick") {
        seriesRef.current = chart.addCandlestickSeries({
          upColor: "#00D09C",
          downColor: "#FF4B4B",
          borderVisible: false,
          wickUpColor: "#00D09C",
          wickDownColor: "#FF4B4B",
        });
      } else {
        seriesRef.current = chart.addLineSeries({ color: "#00D09C", lineWidth: 2 });
      }

      // Resize observer
      const ro = new ResizeObserver(() => {
        if (chartRef.current) chart.applyOptions({ width: chartRef.current.offsetWidth });
      });
      ro.observe(chartRef.current!);
      return () => ro.disconnect();
    });
  }, [chartType, height]);

  useEffect(() => {
    if (!ohlcv || !seriesRef.current) return;
    import("lightweight-charts").then(() => {
      const data = ohlcv.timestamps.map((t: string, i: number) => {
        const timestamp = Math.floor(new Date(t).getTime() / 1000);
        if (chartType === "candlestick") {
          return {
            time: timestamp,
            open: ohlcv.open[i],
            high: ohlcv.high[i],
            low: ohlcv.low[i],
            close: ohlcv.close[i],
          };
        }
        return { time: timestamp, value: ohlcv.close[i] };
      }).filter((d: { open?: number; value?: number; close?: number }) =>
        chartType === "candlestick" ? d.open != null : d.value != null
      );

      (seriesRef.current as { setData: (d: unknown[]) => void }).setData(data);

      // Add EMA overlays
      if (showIndicators && indicators?.history?.ema_21 && chartInstance.current) {
        import("lightweight-charts").then(({ createChart }) => {
          const ema20Data = ohlcv.timestamps
            .map((t: string, i: number) => ({ time: Math.floor(new Date(t).getTime() / 1000), value: indicators.history.ema_21[i] }))
            .filter((d: { value: number | null }) => d.value != null);

          if (ema20Data.length > 0) {
            const emaSeries = (chartInstance.current as { addLineSeries: (opts: unknown) => { setData: (d: unknown[]) => void } }).addLineSeries({
              color: "#4A9EFF",
              lineWidth: 1,
              priceLineVisible: false,
            });
            emaSeries.setData(ema20Data);
          }
        });
      }
    });
  }, [ohlcv, indicators, chartType, showIndicators]);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1.5 border-b border-evo-border bg-evo-surface/50">
        <div className="flex gap-1">
          {INTERVALS.map((iv) => (
            <button
              key={iv}
              onClick={() => setInterval(iv)}
              className={cn(
                "px-2 py-0.5 text-xs rounded transition-colors",
                interval === iv ? "bg-evo-green/10 text-evo-green border border-evo-green/20" : "text-muted-foreground hover:text-white"
              )}
            >
              {iv}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex gap-1">
          {(["candlestick", "line"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setChartType(t)}
              className={cn(
                "px-2 py-0.5 text-xs rounded transition-colors capitalize",
                chartType === t ? "bg-white/10 text-white" : "text-muted-foreground hover:text-white"
              )}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-evo-dark/80 z-10">
            <div className="w-5 h-5 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <div ref={chartRef} className="w-full h-full" />
      </div>
    </div>
  );
}
