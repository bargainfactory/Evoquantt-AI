"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { Bell, Plus, Trash2, CheckCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

type AlertType = "price_above" | "price_below" | "pct_change" | "volume_spike" | "rsi_overbought" | "rsi_oversold";
type Channel = "email" | "push" | "webhook";

interface Alert {
  id: string;
  symbol: string;
  alert_type: AlertType;
  threshold: number;
  channels: Channel[];
  is_active: boolean;
  triggered_at?: string;
  created_at: string;
  message?: string;
}

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  price_above: "Price Above",
  price_below: "Price Below",
  pct_change: "% Change",
  volume_spike: "Volume Spike",
  rsi_overbought: "RSI Overbought",
  rsi_oversold: "RSI Oversold",
};

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<{
    symbol: string;
    alert_type: AlertType;
    threshold: number;
    channels: Channel[];
    message: string;
  }>({
    symbol: "AAPL",
    alert_type: "price_above",
    threshold: 200,
    channels: ["email"],
    message: "",
  });

  const { data: alerts } = useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: () => api.getAlerts().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { mutate: createAlert, isPending: creating } = useMutation({
    mutationFn: () => api.createAlert(form),
    onSuccess: () => {
      toast.success("Alert created!");
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setShowForm(false);
      setForm({ symbol: "AAPL", alert_type: "price_above", threshold: 200, channels: ["email"], message: "" });
    },
    onError: () => toast.error("Failed to create alert"),
  });

  const { mutate: deleteAlert } = useMutation({
    mutationFn: (id: string) => api.deleteAlert(id),
    onSuccess: () => {
      toast.success("Alert deleted");
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const toggleChannel = (ch: Channel) => {
    setForm((f) => ({
      ...f,
      channels: f.channels.includes(ch) ? f.channels.filter((c) => c !== ch) : [...f.channels, ch],
    }));
  };

  const activeAlerts = alerts?.filter((a) => a.is_active && !a.triggered_at) ?? [];
  const triggeredAlerts = alerts?.filter((a) => a.triggered_at) ?? [];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-4xl mx-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <Bell className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Alerts</h1>
                  <p className="text-sm text-muted-foreground">Price, volume, and indicator alerts</p>
                </div>
              </div>
              <button
                onClick={() => setShowForm((v) => !v)}
                className="flex items-center gap-2 px-4 py-2 bg-evo-green text-black rounded-md text-sm font-semibold hover:bg-evo-green/90"
              >
                <Plus className="w-4 h-4" />
                New Alert
              </button>
            </div>

            {/* Create form */}
            {showForm && (
              <div className="evo-card space-y-4">
                <div className="text-sm font-semibold text-white">Create Alert</div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Symbol</label>
                    <input
                      value={form.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value.toUpperCase() }))}
                      className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white font-mono focus:outline-none focus:border-evo-green/50"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Alert Type</label>
                    <select
                      value={form.alert_type}
                      onChange={(e) => setForm((f) => ({ ...f, alert_type: e.target.value as AlertType }))}
                      className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white focus:outline-none"
                    >
                      {Object.entries(ALERT_TYPE_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Threshold</label>
                    <input
                      type="number"
                      value={form.threshold}
                      onChange={(e) => setForm((f) => ({ ...f, threshold: parseFloat(e.target.value) }))}
                      className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm font-mono text-white focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-2 block">Channels</label>
                  <div className="flex gap-2">
                    {(["email", "push", "webhook"] as Channel[]).map((ch) => (
                      <button
                        key={ch}
                        onClick={() => toggleChannel(ch)}
                        className={cn(
                          "px-3 py-1.5 rounded text-xs font-medium capitalize transition-colors",
                          form.channels.includes(ch)
                            ? "bg-evo-green/20 text-evo-green border border-evo-green/30"
                            : "bg-background text-muted-foreground border border-evo-border hover:border-evo-green/30"
                        )}
                      >
                        {ch}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Custom Message (optional)</label>
                  <input
                    value={form.message}
                    onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
                    placeholder="Alert fired: AAPL hit $200"
                    className="w-full bg-background border border-evo-border rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-evo-green/50"
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => createAlert()}
                    disabled={creating || form.channels.length === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-evo-green text-black rounded-md text-sm font-semibold hover:bg-evo-green/90 disabled:opacity-50"
                  >
                    <Plus className="w-4 h-4" />
                    {creating ? "Creating..." : "Create Alert"}
                  </button>
                  <button
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-white"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Active alerts */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-evo-green" />
                <div className="text-sm font-semibold text-white">Active ({activeAlerts.length})</div>
              </div>

              {activeAlerts.length === 0 ? (
                <div className="evo-card text-center py-8 text-sm text-muted-foreground">
                  No active alerts. Create one to get started.
                </div>
              ) : (
                <div className="space-y-2">
                  {activeAlerts.map((alert) => (
                    <div key={alert.id} className="evo-card flex items-center gap-4">
                      <div className="w-2 h-2 rounded-full bg-evo-green flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-mono font-medium text-white">{alert.symbol}</span>
                          <span className="text-xs text-muted-foreground">{ALERT_TYPE_LABELS[alert.alert_type]}</span>
                          <span className="text-xs font-mono text-amber-400">{alert.threshold}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {alert.channels.map((ch) => (
                            <span key={ch} className="capitalize">{ch}</span>
                          ))}
                          {alert.message && <span className="text-muted-foreground/60 truncate">· {alert.message}</span>}
                        </div>
                      </div>
                      <button
                        onClick={() => deleteAlert(alert.id)}
                        className="text-muted-foreground hover:text-evo-red transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Triggered alerts */}
            {triggeredAlerts.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-muted-foreground" />
                  <div className="text-sm font-semibold text-muted-foreground">Triggered ({triggeredAlerts.length})</div>
                </div>
                <div className="space-y-2">
                  {triggeredAlerts.slice(0, 10).map((alert) => (
                    <div key={alert.id} className="evo-card flex items-center gap-4 opacity-60">
                      <div className="w-2 h-2 rounded-full bg-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-mono font-medium text-white">{alert.symbol}</span>
                          <span className="text-xs text-muted-foreground">{ALERT_TYPE_LABELS[alert.alert_type]}</span>
                          <span className="text-xs font-mono text-muted-foreground">{alert.threshold}</span>
                        </div>
                        {alert.triggered_at && (
                          <div className="text-xs text-muted-foreground">
                            Triggered {new Date(alert.triggered_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => deleteAlert(alert.id)}
                        className="text-muted-foreground hover:text-evo-red transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
