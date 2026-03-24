"use client";

import { useState } from "react";
import type { ExecutionStepResponse } from "@/lib/types";

interface Props {
  steps: ExecutionStepResponse[];
}

export default function ExecutionSteps({ steps }: Props) {
  const [open, setOpen] = useState(false);

  if (steps.length === 0) return null;

  return (
    <div className="mt-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className={`transition-transform ${open ? "rotate-90" : ""}`}>›</span>
        {open ? "Hide" : "Show"} {steps.length} execution {steps.length === 1 ? "step" : "steps"}
      </button>

      {open && (
        <ol className="mt-3 space-y-3">
          {steps.map((step) => (
            <li key={step.id} className="flex gap-3">
              <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-500">
                {step.step_number}
              </div>
              <div className="flex-1 min-w-0">
                {step.step_type === "tool_call" ? (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
                    <p className="font-medium text-amber-800">Tool call: {step.tool_name}</p>
                    {step.tool_input && (
                      <p className="mt-1 text-amber-700 truncate">Input: {step.tool_input}</p>
                    )}
                    {step.tool_output && (
                      <p className="mt-1 text-amber-600 text-xs whitespace-pre-wrap break-words">
                        {step.tool_output}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm">
                    <p className="font-medium text-blue-800">LLM response</p>
                    {step.llm_output && (
                      <p className="mt-1 text-blue-700 text-xs whitespace-pre-wrap break-words">
                        {step.llm_output}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
