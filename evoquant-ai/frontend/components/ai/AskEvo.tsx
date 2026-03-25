"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { useMarketStore } from "@/store/useMarketStore";
import { Bot, Send, User, Sparkles, X, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  suggestions?: string[];
}

const QUICK_PROMPTS = [
  "What does the ensemble signal show?",
  "Explain Kelly criterion sizing",
  "How does recursive sell optimization work?",
  "What's the current regime?",
  "Best option strategy for this market?",
];

function MarkdownText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />;
        // Bold **text**
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        const rendered = parts.map((p, j) =>
          p.startsWith("**") && p.endsWith("**")
            ? <strong key={j} className="text-white font-semibold">{p.slice(2, -2)}</strong>
            : p
        );
        // Bullet points
        if (line.trimStart().startsWith("- ") || line.trimStart().startsWith("• ")) {
          return <p key={i} className={cn("flex gap-1.5", i > 0 && "mt-0.5")}><span className="text-evo-green mt-0.5">•</span><span>{rendered}</span></p>;
        }
        return <p key={i} className={i > 0 ? "mt-1" : ""}>{rendered}</p>;
      })}
    </>
  );
}

export function AskEvo({ onClose, triggerPrompt }: { onClose?: () => void; triggerPrompt?: string }) {
  const { activeSymbol } = useMarketStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hi! I'm Evo, your AI trading co-pilot. I can help you with technical analysis, options strategies, recursive sell optimization, DEX routing, and more.\n\nCurrently analyzing: **${activeSymbol}**`,
      suggestions: QUICK_PROMPTS.slice(0, 3),
    },
  ]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const prevTrigger = useRef<string | undefined>(undefined);

  // Wire up external quick prompt triggers from parent (format: "prompt__timestamp")
  useEffect(() => {
    if (triggerPrompt && triggerPrompt !== prevTrigger.current) {
      prevTrigger.current = triggerPrompt;
      const text = triggerPrompt.replace(/__\d+$/, "");
      handleSend(text);
    }
  }, [triggerPrompt]);

  const { mutate: sendMessage, isPending } = useMutation({
    mutationFn: (message: string) => {
      const history = messages
        .filter((m) => !m.suggestions || m.role === "user")
        .map((m) => ({ role: m.role, content: m.content }));
      return api.askEvo(message, { symbol: activeSymbol }, activeSymbol, history).then((r) => r.data);
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response, suggestions: data.suggestions },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that. Please try again." },
      ]);
    },
  });

  const handleSend = (msg?: string) => {
    const text = (msg || input).trim();
    if (!text || isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    sendMessage(text);
    inputRef.current?.focus();
  };

  const handleClear = () => {
    setMessages([{
      role: "assistant",
      content: `Conversation cleared. I'm ready to help with **${activeSymbol}** analysis or any trading questions!`,
      suggestions: QUICK_PROMPTS.slice(0, 3),
    }]);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  return (
    <div className="flex flex-col h-full min-h-[500px] bg-evo-surface border border-evo-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-evo-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-evo-green/20 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-evo-green" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Ask Evo</div>
            <div className="text-xs text-evo-green">AI Trading Co-Pilot · {activeSymbol}</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleClear}
            title="Clear conversation"
            className="p-1.5 text-muted-foreground hover:text-white rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          {onClose && (
            <button onClick={onClose} className="p-1.5 text-muted-foreground hover:text-white rounded transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-3", msg.role === "user" && "flex-row-reverse")}>
            <div className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
              msg.role === "assistant" ? "bg-evo-green/20" : "bg-white/10"
            )}>
              {msg.role === "assistant" ? (
                <Bot className="w-3.5 h-3.5 text-evo-green" />
              ) : (
                <User className="w-3.5 h-3.5 text-white" />
              )}
            </div>
            <div className={cn("flex-1 max-w-[85%]", msg.role === "user" && "items-end flex flex-col")}>
              <div className={cn(
                "rounded-lg px-3 py-2 text-sm leading-relaxed",
                msg.role === "assistant"
                  ? "bg-background/50 text-white/90"
                  : "bg-evo-green/10 border border-evo-green/20 text-white"
              )}>
                <MarkdownText text={msg.content} />
              </div>
              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {msg.suggestions.map((s, j) => (
                    <button
                      key={j}
                      onClick={() => handleSend(s)}
                      disabled={isPending}
                      className="text-xs px-2 py-1 rounded-full bg-white/5 border border-evo-border text-muted-foreground hover:text-white hover:border-evo-green/30 transition-colors disabled:opacity-40"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isPending && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-evo-green/20 flex items-center justify-center mt-0.5">
              <Bot className="w-3.5 h-3.5 text-evo-green" />
            </div>
            <div className="bg-background/50 rounded-lg px-3 py-2.5 flex items-center gap-1">
              {[0, 1, 2].map((i) => (
                <div key={i} className="w-1.5 h-1.5 bg-evo-green rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div className="px-4 py-2 border-t border-evo-border/50 flex gap-1.5 overflow-x-auto">
        {QUICK_PROMPTS.map((p, i) => (
          <button
            key={i}
            onClick={() => handleSend(p)}
            disabled={isPending}
            className="whitespace-nowrap text-xs px-2.5 py-1 rounded-full bg-white/5 text-muted-foreground hover:text-white hover:bg-white/10 transition-colors flex-shrink-0 disabled:opacity-40"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-evo-border">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={`Ask about ${activeSymbol} or any trading topic...`}
            disabled={isPending}
            className="flex-1 bg-background border border-evo-border rounded-md px-3 py-2 text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-evo-green/50 disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={isPending || !input.trim()}
            className="p-2 bg-evo-green/10 border border-evo-green/30 text-evo-green rounded-md hover:bg-evo-green/20 transition-colors disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
