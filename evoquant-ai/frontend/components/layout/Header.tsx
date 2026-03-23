"use client";

import { useState } from "react";
import { Search, Bell, LogOut, User, ChevronDown } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { useMarketStore } from "@/store/useMarketStore";
import { useSearchSymbols } from "@/hooks/useMarketData";
import { formatPercent } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function Header() {
  const [query, setQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const { user, logout } = useAppStore();
  const { setActiveSymbol } = useMarketStore();
  const { data: searchResults } = useSearchSymbols(query);

  return (
    <header className="h-14 border-b border-evo-border bg-evo-surface flex items-center px-4 gap-4 sticky top-0 z-10">
      {/* Search */}
      <div className="relative flex-1 max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search symbol..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowSearch(true); }}
          onBlur={() => setTimeout(() => setShowSearch(false), 200)}
          className="w-full bg-background border border-evo-border rounded-md pl-8 pr-3 py-1.5 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50"
        />
        {showSearch && query.length > 1 && searchResults?.result && (
          <div className="absolute top-full mt-1 left-0 right-0 bg-evo-surface border border-evo-border rounded-md overflow-hidden z-50 shadow-xl">
            {searchResults.result.slice(0, 8).map((item: { symbol: string; description: string; type: string }) => (
              <button
                key={item.symbol}
                className="w-full text-left px-3 py-2 text-sm hover:bg-white/5 flex items-center justify-between"
                onClick={() => { setActiveSymbol(item.symbol); setQuery(""); setShowSearch(false); }}
              >
                <span className="font-medium text-white">{item.symbol}</span>
                <span className="text-muted-foreground text-xs truncate ml-2">{item.description}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1" />

      {/* Notifications */}
      <button className="relative p-2 rounded-md hover:bg-white/5 text-muted-foreground hover:text-white">
        <Bell className="w-4 h-4" />
        <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-evo-green rounded-full" />
      </button>

      {/* User menu */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-evo-green/20 flex items-center justify-center">
          <User className="w-3.5 h-3.5 text-evo-green" />
        </div>
        <div className="hidden sm:block">
          <div className="text-xs font-medium text-white">{user?.username || "User"}</div>
          <div className="text-xs text-muted-foreground">{user?.email || ""}</div>
        </div>
        <button onClick={logout} className="p-1.5 rounded hover:bg-white/5 text-muted-foreground hover:text-white ml-1">
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
}
