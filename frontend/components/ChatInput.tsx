"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentResponse } from "@/lib/types";

interface Props {
  agents: AgentResponse[];
  onSubmit: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ agents, onSubmit, disabled }: Props) {
  const [text, setText] = useState("");
  const [mention, setMention] = useState<{ query: string; start: number } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (mention) {
      if (e.key === "Escape") {
        setMention(null);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const value = e.target.value;
    setText(value);

    // Detect @mention at cursor
    const cursor = e.target.selectionStart ?? value.length;
    const before = value.slice(0, cursor);
    const match = before.match(/@(\w*)$/);
    if (match) {
      setMention({ query: match[1].toLowerCase(), start: cursor - match[0].length });
    } else {
      setMention(null);
    }
  }

  function insertMention(agentName: string) {
    if (!mention) return;
    const before = text.slice(0, mention.start);
    const after = text.slice(mention.start + 1 + mention.query.length);
    const newText = `${before}@${agentName} ${after}`;
    setText(newText);
    setMention(null);
    textareaRef.current?.focus();
  }

  function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText("");
    setMention(null);
  }

  const filteredAgents = mention
    ? agents.filter((a) => a.name.toLowerCase().includes(mention.query))
    : [];

  return (
    <div className="relative">
      {mention && filteredAgents.length > 0 && (
        <div className="absolute bottom-full mb-2 left-0 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-10 min-w-48">
          {filteredAgents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                insertMention(agent.name);
              }}
              className="w-full text-left px-4 py-2 text-sm text-gray-800 hover:bg-blue-50 hover:text-blue-700"
            >
              <span className="font-medium">@{agent.name}</span>
              <span className="text-gray-400 ml-2">{agent.role}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end border border-gray-300 rounded-xl px-3 py-2 bg-white focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Type a message… use @AgentName to invoke an agent"
          className="flex-1 resize-none text-sm text-gray-900 placeholder:text-gray-400 outline-none bg-transparent max-h-40 overflow-y-auto"
          style={{ minHeight: "24px" }}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || !text.trim()}
          className="shrink-0 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-sm font-medium rounded-lg px-3 py-1.5 transition-colors"
        >
          Send
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-400">Enter to send · Shift+Enter for newline · @Name to invoke agent</p>
    </div>
  );
}
