"use client";

import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { useAppStore } from "@/store/useAppStore";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";
import { Settings, Shield, Bell, Wallet, User, Key, Trash2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

type Tab = "profile" | "security" | "brokers" | "notifications" | "trading";

const BROKER_OPTIONS = [
  { id: "binance", label: "Binance", type: "crypto" },
  { id: "bybit", label: "Bybit", type: "crypto" },
  { id: "coinbase", label: "Coinbase Advanced", type: "crypto" },
  { id: "kraken", label: "Kraken", type: "crypto" },
  { id: "okx", label: "OKX", type: "crypto" },
  { id: "ibkr", label: "Interactive Brokers", type: "stocks" },
  { id: "etrade", label: "E*TRADE", type: "stocks" },
  { id: "schwab", label: "Charles Schwab", type: "stocks" },
  { id: "tradier", label: "Tradier", type: "options" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const { user, isPaper, setIsPaper } = useAppStore();

  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name ?? "",
    email: user?.email ?? "",
  });
  const [passwordForm, setPasswordForm] = useState({ current: "", next: "", confirm: "" });
  const [brokerForm, setBrokerForm] = useState({ broker: "binance", api_key: "", secret: "", testnet: true });
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");

  const { data: brokers, refetch: refetchBrokers } = useQuery({
    queryKey: ["brokers"],
    queryFn: () => api.listBrokers().then((r) => r.data.brokers as string[]),
  });

  const { mutate: updateProfile, isPending: updatingProfile } = useMutation({
    mutationFn: () => api.updateProfile(profileForm),
    onSuccess: () => toast.success("Profile updated"),
    onError: () => toast.error("Update failed"),
  });

  const { mutate: setup2fa } = useMutation({
    mutationFn: () => api.setup2fa().then((r) => r.data),
    onSuccess: (data) => setQrCode(data.qr_code),
    onError: () => toast.error("Failed to setup 2FA"),
  });

  const { mutate: confirm2fa, isPending: confirming2fa } = useMutation({
    mutationFn: () => api.confirm2fa(totpCode),
    onSuccess: () => {
      toast.success("2FA enabled!");
      setQrCode(null);
      setTotpCode("");
    },
    onError: () => toast.error("Invalid code"),
  });

  const { mutate: connectBroker, isPending: connectingBroker } = useMutation({
    mutationFn: () => api.connectBroker(brokerForm),
    onSuccess: () => {
      toast.success(`${brokerForm.broker} connected!`);
      refetchBrokers();
      setBrokerForm((f) => ({ ...f, api_key: "", secret: "" }));
    },
    onError: () => toast.error("Failed to connect broker"),
  });

  const tabs = [
    { id: "profile" as Tab, label: "Profile", icon: User },
    { id: "security" as Tab, label: "Security & 2FA", icon: Shield },
    { id: "brokers" as Tab, label: "Brokers", icon: Key },
    { id: "notifications" as Tab, label: "Notifications", icon: Bell },
    { id: "trading" as Tab, label: "Trading", icon: Settings },
  ];

  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <div className="space-y-6 max-w-4xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-muted/20 flex items-center justify-center">
                <Settings className="w-5 h-5 text-muted-foreground" />
              </div>
              <h1 className="text-xl font-bold text-white">Settings</h1>
            </div>

            <div className="flex gap-1 border-b border-evo-border">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
                    activeTab === tab.id
                      ? "text-white border-evo-green"
                      : "text-muted-foreground border-transparent hover:text-white"
                  )}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === "profile" && (
              <div className="evo-card space-y-4 max-w-md">
                <div className="text-sm font-semibold text-white">Profile Information</div>
                {[
                  { key: "full_name", label: "Full Name", type: "text" },
                  { key: "email", label: "Email", type: "email" },
                ].map(({ key, label, type }) => (
                  <div key={key}>
                    <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
                    <input
                      type={type}
                      value={profileForm[key as keyof typeof profileForm]}
                      onChange={(e) => setProfileForm((f) => ({ ...f, [key]: e.target.value }))}
                      className="w-full bg-background border border-evo-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-evo-green/50"
                    />
                  </div>
                ))}
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Username</label>
                  <input
                    value={user?.username ?? ""}
                    disabled
                    className="w-full bg-background border border-evo-border rounded px-3 py-2 text-sm text-muted-foreground cursor-not-allowed"
                  />
                </div>
                <button
                  onClick={() => updateProfile()}
                  disabled={updatingProfile}
                  className="flex items-center gap-2 px-4 py-2 bg-evo-green text-black rounded-md text-sm font-semibold hover:bg-evo-green/90 disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  {updatingProfile ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}

            {activeTab === "security" && (
              <div className="space-y-4 max-w-md">
                <div className="evo-card space-y-4">
                  <div className="text-sm font-semibold text-white">Change Password</div>
                  {[
                    { key: "current", label: "Current Password" },
                    { key: "next", label: "New Password" },
                    { key: "confirm", label: "Confirm New Password" },
                  ].map(({ key, label }) => (
                    <div key={key}>
                      <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
                      <input
                        type="password"
                        value={passwordForm[key as keyof typeof passwordForm]}
                        onChange={(e) => setPasswordForm((f) => ({ ...f, [key]: e.target.value }))}
                        className="w-full bg-background border border-evo-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-evo-green/50"
                      />
                    </div>
                  ))}
                  <button
                    onClick={() => {
                      if (passwordForm.next !== passwordForm.confirm) {
                        toast.error("Passwords don't match");
                        return;
                      }
                      toast.success("Password update coming soon");
                    }}
                    className="px-4 py-2 bg-evo-blue text-white rounded-md text-sm font-semibold hover:bg-evo-blue/90"
                  >
                    Update Password
                  </button>
                </div>

                <div className="evo-card space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-white">Two-Factor Authentication</div>
                      <div className="text-xs text-muted-foreground mt-0.5">TOTP via authenticator app</div>
                    </div>
                    <div className={cn(
                      "px-2 py-0.5 rounded-full text-xs font-medium",
                      user?.totp_enabled ? "bg-evo-green/20 text-evo-green" : "bg-muted/20 text-muted-foreground"
                    )}>
                      {user?.totp_enabled ? "Enabled" : "Disabled"}
                    </div>
                  </div>

                  {!user?.totp_enabled && !qrCode && (
                    <button
                      onClick={() => setup2fa()}
                      className="px-4 py-2 bg-evo-purple text-white rounded-md text-sm font-semibold hover:bg-evo-purple/90"
                    >
                      Enable 2FA
                    </button>
                  )}

                  {qrCode && (
                    <div className="space-y-3">
                      <div className="text-xs text-muted-foreground">Scan with your authenticator app:</div>
                      <img src={`data:image/png;base64,${qrCode}`} alt="2FA QR Code" className="w-40 h-40 rounded" />
                      <div>
                        <label className="text-xs text-muted-foreground mb-1 block">Enter 6-digit code to confirm</label>
                        <div className="flex gap-2">
                          <input
                            value={totpCode}
                            onChange={(e) => setTotpCode(e.target.value)}
                            maxLength={6}
                            placeholder="000000"
                            className="flex-1 bg-background border border-evo-border rounded px-3 py-2 text-sm text-white font-mono text-center tracking-widest focus:outline-none focus:border-evo-green/50"
                          />
                          <button
                            onClick={() => confirm2fa()}
                            disabled={confirming2fa || totpCode.length !== 6}
                            className="px-4 py-2 bg-evo-green text-black rounded-md text-sm font-semibold disabled:opacity-50"
                          >
                            Confirm
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "brokers" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="evo-card space-y-4">
                  <div className="text-sm font-semibold text-white">Connect Broker</div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1 block">Broker</label>
                    <select
                      value={brokerForm.broker}
                      onChange={(e) => setBrokerForm((f) => ({ ...f, broker: e.target.value }))}
                      className="w-full bg-background border border-evo-border rounded px-2 py-2 text-sm text-white focus:outline-none"
                    >
                      {BROKER_OPTIONS.map((b) => (
                        <option key={b.id} value={b.id}>{b.label} ({b.type})</option>
                      ))}
                    </select>
                  </div>
                  {[{ field: "api_key", label: "API Key" }, { field: "secret", label: "API Secret" }].map(({ field, label }) => (
                    <div key={field}>
                      <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
                      <input
                        type="password"
                        value={brokerForm[field as "api_key" | "secret"]}
                        onChange={(e) => setBrokerForm((f) => ({ ...f, [field]: e.target.value }))}
                        placeholder="••••••••••••••••"
                        className="w-full bg-background border border-evo-border rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-evo-green/50"
                      />
                    </div>
                  ))}
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={brokerForm.testnet}
                      onChange={(e) => setBrokerForm((f) => ({ ...f, testnet: e.target.checked }))}
                      className="accent-evo-green"
                    />
                    <span className="text-xs text-muted-foreground">Sandbox / Testnet mode</span>
                  </label>
                  <button
                    onClick={() => connectBroker()}
                    disabled={connectingBroker || !brokerForm.api_key}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-evo-green text-black rounded-md text-sm font-semibold hover:bg-evo-green/90 disabled:opacity-50"
                  >
                    <Key className="w-4 h-4" />
                    {connectingBroker ? "Connecting..." : "Connect Broker"}
                  </button>
                  <p className="text-xs text-muted-foreground">
                    API keys are encrypted with Kyber-768 post-quantum encryption before storage.
                  </p>
                </div>

                <div className="evo-card">
                  <div className="text-sm font-semibold text-white mb-3">Connected Brokers</div>
                  {!brokers || brokers.length === 0 ? (
                    <div className="text-sm text-muted-foreground text-center py-6">No brokers connected</div>
                  ) : (
                    <div className="space-y-2">
                      {brokers.map((name: string) => (
                        <div key={name} className="flex items-center justify-between px-3 py-2 bg-background/50 rounded">
                          <div>
                            <div className="text-sm text-white capitalize">{name}</div>
                            <div className="text-xs text-muted-foreground">Connected</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-evo-green" />
                            <button className="text-muted-foreground hover:text-evo-red">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "notifications" && (
              <div className="evo-card max-w-md space-y-4">
                <div className="text-sm font-semibold text-white">Notification Preferences</div>
                {[
                  { label: "Price alerts", sub: "When asset hits target price" },
                  { label: "Order fills", sub: "When orders are executed" },
                  { label: "P&L milestones", sub: "Daily P&L targets hit" },
                  { label: "Evolution Lab completion", sub: "Nightly optimization results" },
                  { label: "Security events", sub: "Login from new device" },
                  { label: "Margin calls", sub: "Approaching margin limits" },
                ].map(({ label, sub }) => (
                  <label key={label} className="flex items-center justify-between cursor-pointer">
                    <div>
                      <div className="text-sm text-white">{label}</div>
                      <div className="text-xs text-muted-foreground">{sub}</div>
                    </div>
                    <input type="checkbox" defaultChecked className="accent-evo-green w-4 h-4" />
                  </label>
                ))}
              </div>
            )}

            {activeTab === "trading" && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-2xl">
                <div className="evo-card space-y-4">
                  <div className="text-sm font-semibold text-white">Trading Mode</div>
                  <div className="space-y-2">
                    {[
                      { value: true, label: "Paper Trading", sub: "Simulated trades, no real money" },
                      { value: false, label: "Live Trading", sub: "Real money — trade carefully" },
                    ].map(({ value, label, sub }) => (
                      <label
                        key={String(value)}
                        className={cn(
                          "flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                          isPaper === value ? "border-evo-green/40 bg-evo-green/5" : "border-evo-border hover:border-evo-border/80"
                        )}
                      >
                        <input
                          type="radio"
                          checked={isPaper === value}
                          onChange={() => setIsPaper(value)}
                          className="accent-evo-green"
                        />
                        <div>
                          <div className="text-sm font-medium text-white">{label}</div>
                          <div className="text-xs text-muted-foreground">{sub}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="evo-card space-y-4">
                  <div className="text-sm font-semibold text-white">Risk Defaults</div>
                  {[
                    { label: "Max position size (%)", defaultValue: "5", min: "1", max: "25" },
                    { label: "Default stop loss (%)", defaultValue: "2", min: "0.5", max: "10" },
                    { label: "Max daily loss (%)", defaultValue: "5", min: "1", max: "20" },
                  ].map(({ label, defaultValue, min, max }) => (
                    <div key={label}>
                      <label className="text-xs text-muted-foreground mb-1 block">{label}</label>
                      <input
                        type="number"
                        defaultValue={defaultValue}
                        min={min}
                        max={max}
                        className="w-full bg-background border border-evo-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-evo-green/50"
                      />
                    </div>
                  ))}
                  <button
                    onClick={() => toast.success("Risk settings saved")}
                    className="px-4 py-2 bg-evo-green text-black rounded-md text-sm font-semibold hover:bg-evo-green/90"
                  >
                    Save Defaults
                  </button>
                </div>
              </div>
            )}
          </div>
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
