"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import api from "@/lib/api";
import { useAppStore } from "@/store/useAppStore";
import { Zap } from "lucide-react";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const { setUser, setTokens } = useAppStore();
  const [form, setForm] = useState({ email: "", username: "", password: "", full_name: "" });

  const { mutate: register, isPending } = useMutation({
    mutationFn: () => api.register(form),
    onSuccess: async () => {
      toast.success("Account created! Logging in...");
      try {
        const loginRes = await api.login(form.email, form.password);
        setTokens(loginRes.data.access_token, loginRes.data.refresh_token);
        setUser(loginRes.data.user);
        router.push("/dashboard");
      } catch {
        router.push("/login");
      }
    },
    onError: (e: unknown) => {
      const err = e as { response?: { data?: { detail?: string } } };
      toast.error(err?.response?.data?.detail || "Registration failed");
    },
  });

  return (
    <div className="min-h-screen bg-evo-dark flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-evo-green/20 mb-4">
            <Zap className="w-7 h-7 text-evo-green" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create Account</h1>
          <p className="text-sm text-muted-foreground mt-1">Start trading with EvoQuant AI</p>
        </div>

        <div className="evo-card space-y-4">
          {[
            { key: "full_name", label: "Full Name", type: "text", placeholder: "John Trader" },
            { key: "username", label: "Username", type: "text", placeholder: "jtrader" },
            { key: "email", label: "Email", type: "email", placeholder: "john@example.com" },
            { key: "password", label: "Password", type: "password", placeholder: "••••••••" },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="text-xs text-muted-foreground mb-1.5 block">{label}</label>
              <input
                type={type}
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full bg-background border border-evo-border rounded-md px-3 py-2.5 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
              />
            </div>
          ))}

          <button
            onClick={() => register()}
            disabled={isPending || !form.email || !form.username || !form.password}
            className="w-full py-2.5 bg-evo-green text-black font-semibold rounded-md hover:bg-evo-green/90 transition-colors disabled:opacity-50"
          >
            {isPending ? "Creating..." : "Create Account"}
          </button>
        </div>

        <div className="text-center mt-4 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-evo-green hover:underline">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
