"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";

export default function RootPage() {
  const router = useRouter();
  const { user } = useAppStore();

  useEffect(() => {
    if (user) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [user, router]);

  return (
    <div className="min-h-screen bg-evo-dark flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-evo-green border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
