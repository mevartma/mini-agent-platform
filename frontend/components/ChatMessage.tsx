"use client";

import type { ChatMessage as ChatMessageType, StreamStepEvent } from "@/lib/types";

interface LiveSteps {
  steps: StreamStepEvent[];
  streaming: boolean;
  finalResponse: string | null;
  error: string | null;
}

interface Props {
  message: ChatMessageType;
  liveSteps?: LiveSteps;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function StepBadge({ step }: { step: StreamStepEvent }) {
  const isTool = step.step_type === "tool_call";
  return (
    <div className={`rounded-lg px-3 py-2 text-xs ${isTool ? "bg-amber-50 border border-amber-200" : "bg-blue-50 border border-blue-200"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`font-semibold ${isTool ? "text-amber-700" : "text-blue-700"}`}>
          {isTool ? `Tool: ${step.tool_name}` : `Step ${step.step_number}: LLM`}
        </span>
        <span className="text-gray-400">#{step.step_number}</span>
      </div>
      {isTool && step.tool_input && (
        <p className="text-gray-600 truncate">Input: {step.tool_input}</p>
      )}
      {isTool && step.tool_output && (
        <p className="text-gray-500 mt-0.5 line-clamp-2">{step.tool_output}</p>
      )}
      {!isTool && step.llm_output && (
        <p className="text-gray-600 line-clamp-3">{step.llm_output}</p>
      )}
    </div>
  );
}

export default function ChatMessageBubble({ message, liveSteps }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg">
          <div className="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
            {message.content}
          </div>
          <p className="text-right text-xs text-gray-400 mt-1">{formatTime(message.created_at)}</p>
        </div>
      </div>
    );
  }

  // Agent message
  const steps = liveSteps?.steps ?? [];
  const streaming = liveSteps?.streaming ?? false;
  const finalResponse = liveSteps?.finalResponse ?? message.content;
  const error = liveSteps?.error ?? null;

  return (
    <div className="flex justify-start">
      <div className="max-w-xl w-full">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-base">🤖</span>
          <span className="text-xs font-semibold text-gray-700">{message.agent_name ?? "Agent"}</span>
          {streaming && (
            <span className="flex gap-0.5 items-center">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:300ms]" />
            </span>
          )}
          <span className="text-xs text-gray-400 ml-auto">{formatTime(message.created_at)}</span>
        </div>

        <div className={`rounded-2xl rounded-tl-sm px-4 py-3 space-y-2 ${error ? "bg-red-50 border border-red-200" : "bg-white border border-gray-200"}`}>
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : (
            <>
              {steps.length > 0 && (
                <div className="space-y-1.5">
                  {steps.map((s) => (
                    <StepBadge key={`${s.step_number}-${s.step_type}`} step={s} />
                  ))}
                </div>
              )}

              {!streaming && finalResponse && (
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{finalResponse}</p>
              )}

              {!streaming && !finalResponse && !error && steps.length === 0 && (
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{message.content}</p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
