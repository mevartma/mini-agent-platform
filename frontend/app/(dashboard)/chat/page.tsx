"use client";

import ChatInput from "@/components/ChatInput";
import ChatMessageBubble from "@/components/ChatMessage";
import type {
  AgentResponse,
  ChatMessage,
  ChatSession,
  StreamFinalEvent,
  StreamStepEvent,
} from "@/lib/types";
import { useEffect, useRef, useState } from "react";

interface LiveState {
  [tempId: string]: {
    steps: StreamStepEvent[];
    streaming: boolean;
    finalResponse: string | null;
    error: string | null;
  };
}

export default function ChatPage() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [liveState, setLiveState] = useState<LiveState>({});
  const [agents, setAgents] = useState<AgentResponse[]>([]);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load agents + default session on mount
  useEffect(() => {
    loadAgents();
    loadOrCreateSession();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveState]);

  async function loadAgents() {
    try {
      const res = await fetch("/api/agents");
      if (res.ok) {
        const data = await res.json();
        setAgents(data.items ?? []);
      }
    } catch {
      // agents list is best-effort
    }
  }

  async function loadOrCreateSession() {
    try {
      const listRes = await fetch("/api/chat");
      if (!listRes.ok) return;
      const sessions: ChatSession[] = await listRes.json();

      let active: ChatSession;
      if (sessions.length > 0) {
        active = sessions[0];
      } else {
        const createRes = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "Default Chat" }),
        });
        if (!createRes.ok) return;
        active = await createRes.json();
      }

      setSession(active);
      loadMessages(active.id);
    } catch {
      setError("Failed to load chat session.");
    }
  }

  async function loadMessages(sessionId: string) {
    try {
      const res = await fetch(`/api/chat/${sessionId}/messages?limit=100`);
      if (!res.ok) return;
      const data: ChatMessage[] = await res.json();
      // API returns newest-first; reverse for display
      setMessages(data.reverse());
    } catch {
      // ignore
    }
  }

  async function handleSubmit(text: string) {
    if (!session) return;
    setError("");

    // 1. Save and display user message
    const userMsg = await postMessage(session.id, {
      role: "user",
      content: text,
    });
    if (!userMsg) return;
    setMessages((prev) => [...prev, userMsg]);

    // 2. Parse @AgentName mentions
    const mentionMatches = [...text.matchAll(/@(\S+)/g)];
    const mentionedNames = [...new Set(mentionMatches.map((m) => m[1].toLowerCase()))];
    const invokedAgents = agents.filter((a) =>
      mentionedNames.includes(a.name.toLowerCase())
    );

    if (invokedAgents.length === 0) return;

    // 3. Open parallel SSE streams for each mentioned agent
    await Promise.all(
      invokedAgents.map((agent) => streamAgent(session.id, agent, text))
    );
  }

  async function streamAgent(
    sessionId: string,
    agent: AgentResponse,
    task: string
  ) {
    const tempId = `${agent.id}-${Date.now()}`;
    const now = new Date().toISOString();

    // Create a placeholder agent message immediately
    const placeholder: ChatMessage = {
      id: tempId,
      session_id: sessionId,
      tenant_id: "",
      role: "agent",
      content: "",
      agent_name: agent.name,
      execution_id: null,
      created_at: now,
    };
    setMessages((prev) => [...prev, placeholder]);
    setLiveState((prev) => ({
      ...prev,
      [tempId]: { steps: [], streaming: true, finalResponse: null, error: null },
    }));

    try {
      const res = await fetch(`/api/agents/${agent.id}/run/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, model: "gpt-4o" }),
      });

      if (!res.ok || !res.body) {
        let detail = "Request failed.";
        try {
          const errData = await res.json();
          detail = errData.detail ?? detail;
        } catch { /* ignore */ }
        setLiveState((prev) => ({
          ...prev,
          [tempId]: { ...prev[tempId], streaming: false, error: detail },
        }));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let executionId: string | null = null;
      let finalText: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          let eventType = "";
          let dataLine = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) eventType = line.slice(7);
            if (line.startsWith("data: ")) dataLine = line.slice(6);
          }
          if (!dataLine) continue;

          try {
            const payload = JSON.parse(dataLine);
            if (eventType === "step") {
              const step = payload as StreamStepEvent;
              setLiveState((prev) => ({
                ...prev,
                [tempId]: {
                  ...prev[tempId],
                  steps: [...prev[tempId].steps, step],
                },
              }));
            } else if (eventType === "final") {
              const final = payload as StreamFinalEvent;
              executionId = final.execution_id;
              finalText = final.final_response;
              setLiveState((prev) => ({
                ...prev,
                [tempId]: {
                  ...prev[tempId],
                  streaming: false,
                  finalResponse: finalText,
                },
              }));
            } else if (eventType === "error") {
              setLiveState((prev) => ({
                ...prev,
                [tempId]: {
                  ...prev[tempId],
                  streaming: false,
                  error: payload.detail ?? "An error occurred.",
                },
              }));
              return;
            }
          } catch {
            // malformed SSE frame — skip
          }
        }
      }

      // 4. Persist agent message to DB (skip if no response was produced)
      if (!finalText) return;
      const saved = await postMessage(sessionId, {
        role: "agent",
        content: finalText ?? "(no response)",
        agent_name: agent.name,
        execution_id: executionId ?? undefined,
      });

      if (saved) {
        // Replace placeholder with real DB record (keeps live steps in place)
        setMessages((prev) =>
          prev.map((m) => (m.id === tempId ? { ...saved } : m))
        );
        // Move live state to real ID
        setLiveState((prev) => {
          const { [tempId]: live, ...rest } = prev;
          return { ...rest, [saved.id]: { ...live, streaming: false } };
        });
      }
    } catch {
      setLiveState((prev) => ({
        ...prev,
        [tempId]: { ...prev[tempId], streaming: false },
      }));
    }
  }

  async function postMessage(
    sessionId: string,
    data: {
      role: string;
      content: string;
      agent_name?: string;
      execution_id?: string | null;
    }
  ): Promise<ChatMessage | null> {
    try {
      const res = await fetch(`/api/chat/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  const anyStreaming = Object.values(liveState).some((s) => s.streaming);

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] max-w-3xl mx-auto">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Chat</h1>
        {session && (
          <span className="text-xs text-gray-400">Session: {session.name}</span>
        )}
      </div>

      {error && (
        <p className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && !anyStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <p className="text-4xl mb-3">💬</p>
            <p className="text-sm font-medium">Start a conversation</p>
            <p className="text-xs mt-1">Use @AgentName to invoke an agent</p>
          </div>
        )}

        {messages.map((msg) => {
          const live = liveState[msg.id];
          return (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              liveSteps={live}
            />
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="pt-3 border-t border-gray-200">
        <ChatInput
          agents={agents}
          onSubmit={handleSubmit}
          disabled={!session || anyStreaming}
        />
      </div>
    </div>
  );
}
