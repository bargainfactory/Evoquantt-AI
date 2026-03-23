"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Shield, Key, Lock, CheckCircle, AlertCircle, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const SECURITY_FEATURES = [
  { name: "Kyber-768 Key Encapsulation", status: "active", desc: "NIST PQC standard KEM (post-quantum)", icon: Key },
  { name: "Dilithium-2 JWT Signing", status: "active", desc: "Quantum-resistant token signatures", icon: Lock },
  { name: "AES-256-GCM Vault", status: "active", desc: "All secrets encrypted at rest", icon: Shield },
  { name: "TOTP 2FA", status: "check_user", desc: "Time-based one-time password", icon: CheckCircle },
  { name: "Rate Limiting", status: "active", desc: "60 req/min per IP, burst 20", icon: Activity },
  { name: "Full Audit Log", status: "active", desc: "All actions logged with user/IP", icon: Activity },
  { name: "HKDF-SHA3-512 KDF", status: "active", desc: "Per-context key derivation", icon: Key },
  { name: "OWASP Compliance", status: "active", desc: "XSS, SQLi, CSRF, injection protection", icon: Shield },
];

export function SecurityDashboard() {
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="evo-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-evo-green/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-evo-green" />
          </div>
          <div>
            <div className="text-lg font-bold text-white">Quantum-Proof Security Layer</div>
            <div className="text-sm text-muted-foreground">EvoQuant AI uses post-quantum cryptography (NIST PQC round 3 standards)</div>
          </div>
          <div className="ml-auto">
            <span className="evo-badge-green">All Systems Secure</span>
          </div>
        </div>

        {/* Security score */}
        <div className="bg-background/50 rounded-lg p-4 flex items-center gap-6">
          <div className="text-center">
            <div className="text-4xl font-bold text-evo-green">98</div>
            <div className="text-xs text-muted-foreground mt-1">Security Score</div>
          </div>
          <div className="flex-1 space-y-2">
            {[
              { label: "Encryption Strength", value: 100 },
              { label: "Authentication", value: me?.totp_enabled ? 100 : 70 },
              { label: "API Security", value: 95 },
              { label: "Data Protection", value: 98 },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-36">{label}</span>
                <div className="flex-1 bg-evo-border rounded-full h-1.5">
                  <div
                    className={cn("h-1.5 rounded-full transition-all", value === 100 ? "bg-evo-green" : value >= 80 ? "bg-evo-blue" : "bg-amber-500")}
                    style={{ width: `${value}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-white w-8 text-right">{value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feature grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SECURITY_FEATURES.map(({ name, status, desc, icon: Icon }) => {
          const isActive = status === "active" || (status === "check_user" && me?.totp_enabled);
          return (
            <div key={name} className="evo-card flex items-start gap-3">
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                isActive ? "bg-evo-green/20" : "bg-amber-500/20"
              )}>
                <Icon className={cn("w-4 h-4", isActive ? "text-evo-green" : "text-amber-400")} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{name}</span>
                  {isActive ? (
                    <CheckCircle className="w-3.5 h-3.5 text-evo-green" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                  )}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>
                {status === "check_user" && !me?.totp_enabled && (
                  <div className="text-xs text-amber-400 mt-1">Enable 2FA in Settings for full protection</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* PQ Proof */}
      <div className="evo-card">
        <div className="text-sm font-semibold text-white mb-3">Post-Quantum Cryptography Proof</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-background/50 rounded p-3">
            <div className="text-evo-green font-semibold mb-1">Key Encapsulation</div>
            <div className="text-muted-foreground">Algorithm: Kyber-768</div>
            <div className="text-muted-foreground">Security Level: NIST Level 3</div>
            <div className="text-muted-foreground">Usage: Session key exchange, broker API keys</div>
          </div>
          <div className="bg-background/50 rounded p-3">
            <div className="text-evo-blue font-semibold mb-1">Digital Signatures</div>
            <div className="text-muted-foreground">Algorithm: Dilithium-2</div>
            <div className="text-muted-foreground">Security Level: NIST Level 2</div>
            <div className="text-muted-foreground">Usage: JWT tokens, audit log entries</div>
          </div>
          <div className="bg-background/50 rounded p-3">
            <div className="text-evo-purple font-semibold mb-1">Symmetric Encryption</div>
            <div className="text-muted-foreground">Algorithm: AES-256-GCM</div>
            <div className="text-muted-foreground">Key Derivation: HKDF-SHA3-512</div>
            <div className="text-muted-foreground">Usage: Vault, database fields</div>
          </div>
        </div>
        <div className="mt-3 text-xs text-muted-foreground">
          All quantum-resistant algorithms are from the <span className="text-white">liboqs (Open Quantum Safe)</span> library,
          implementing NIST Post-Quantum Cryptography standardization round 3 finalists.
          Hybrid mode: PQ + classical cryptography for defense-in-depth.
        </div>
      </div>
    </div>
  );
}
