"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { Zap, Eye, EyeOff } from "lucide-react";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const { setUser, setTokens } = useAppStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [needTotp, setNeedTotp] = useState(false);

  const { mutate: login, isPending } = useMutation({
    mutationFn: () => api.login(email, password, needTotp ? totpCode : undefined),
    onSuccess: (r) => {
      setTokens(r.data.access_token, r.data.refresh_token);
      setUser(r.data.user);
      toast.success("Welcome back!");
      router.push("/dashboard");
    },
    onError: (e: unknown) => {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      if (err?.response?.status === 428) {
        setNeedTotp(true);
        toast("Please enter your 2FA code");
      } else {
        toast.error(err?.response?.data?.detail || "Login failed");
      }
    },
  });

  return (
    <div className="min-h-screen bg-evo-dark flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-evo-green/20 mb-4">
            <Zap className="w-7 h-7 text-evo-green" />
          </div>
          <h1 className="text-2xl font-bold text-white">EvoQuant AI</h1>
          <p className="text-sm text-muted-foreground mt-1">Quantum-proof trading platform</p>
        </div>

        {/* Form */}
        <div className="evo-card space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="trader@example.com"
              className="w-full bg-background border border-evo-border rounded-md px-3 py-2.5 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !needTotp && login()}
                placeholder="••••••••"
                className="w-full bg-background border border-evo-border rounded-md px-3 py-2.5 pr-10 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {needTotp && (
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">2FA Code</label>
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && login()}
                placeholder="000000"
                maxLength={6}
                className="w-full bg-background border border-evo-green/30 rounded-md px-3 py-2.5 text-sm font-mono text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50 tracking-widest text-center"
              />
            </div>
          )}

          <button
            onClick={() => login()}
            disabled={isPending || !email || !password}
            className="w-full py-2.5 bg-evo-green text-black font-semibold rounded-md hover:bg-evo-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? "Signing in..." : "Sign In"}
          </button>
        </div>

        <div className="text-center mt-4 text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-evo-green hover:underline">Create one</Link>
        </div>

        {/* Demo hint */}
        <div className="mt-4 p-3 bg-white/3 border border-evo-border/50 rounded-md text-xs text-muted-foreground text-center">
          Demo: register any email/password to get started
        </div>
      </div>
    </div>
  );
}
