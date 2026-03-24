"use client";

import { WagmiProvider as WagmiProviderBase, createConfig, http } from "wagmi";
import { mainnet, sepolia, polygon, arbitrum, optimism, base } from "wagmi/chains";
import { RainbowKitProvider, getDefaultConfig, darkTheme } from "@rainbow-me/rainbowkit";
import "@rainbow-me/rainbowkit/styles.css";

const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "demo-project-id";

const config = getDefaultConfig({
  appName: "EvoQuant AI",
  projectId,
  chains: [mainnet, sepolia, polygon, arbitrum, optimism, base],
  transports: {
    [mainnet.id]: http(process.env.NEXT_PUBLIC_ALCHEMY_ETH_MAINNET || "https://eth.llamarpc.com"),
    [sepolia.id]: http(process.env.NEXT_PUBLIC_ALCHEMY_ETH_SEPOLIA),
    [polygon.id]: http(),
    [arbitrum.id]: http(),
    [optimism.id]: http(),
    [base.id]: http(),
  },
  ssr: true,
});

export function WagmiProvider({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProviderBase config={config}>
      <RainbowKitProvider
        theme={darkTheme({
          accentColor: "#00D09C",
          accentColorForeground: "#0D1117",
          borderRadius: "medium",
          fontStack: "system",
        })}
      >
        {children}
      </RainbowKitProvider>
    </WagmiProviderBase>
  );
}

export { config as wagmiConfig };
