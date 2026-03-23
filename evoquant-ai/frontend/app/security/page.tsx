"use client";

import { AppLayout } from "@/components/layout/AppLayout";
import { WagmiProvider } from "@/providers/WagmiProvider";
import { SolanaProvider } from "@/providers/SolanaProvider";
import { SecurityDashboard } from "@/components/security/SecurityDashboard";

export default function SecurityPage() {
  return (
    <WagmiProvider>
      <SolanaProvider>
        <AppLayout>
          <SecurityDashboard />
        </AppLayout>
      </SolanaProvider>
    </WagmiProvider>
  );
}
