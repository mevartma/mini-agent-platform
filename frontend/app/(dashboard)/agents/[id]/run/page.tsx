"use client";

import ExecutionSteps from "@/components/ExecutionSteps";
import type { RunResponse } from "@/lib/types";
import Link from "next/link";
import { use, useState } from "react";

const MODELS = ["gpt-4o", "claude-3-5-sonnet"];

interface Props {
  params: Promise<{ id: string }>;
}

export default function RunAgentPage({ params }: Props) {
  const { id } = use(params);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    const form = new FormData(e.currentTarget);

    try {
      const res = await fetch(`/api/agents/${id}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: form.get("task"),
          model: form.get("model"),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Run failed.");
        return;
      }
      setResult(data as RunResponse);
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <Link href="/agents" className="text-sm text-gray-400 hover:text-gray-600">
          ← Agents
        </Link>
        <div className="flex items-center justify-between mt-2">
          <h1 className="text-xl font-semibold text-gray-900">Run agent</h1>
          <Link
            href={`/agents/${id}/history`}
            className="text-sm text-blue-600 hover:underline"
          >
            View history
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Task</label>
            <textarea
              name="task"
              required
              rows={4}
              placeholder="Search for the latest developments in quantum computing."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <select
              name="model"
              defaultValue="gpt-4o"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 bg-white"
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            {loading ? "Running…" : "Run agent"}
          </button>
        </form>
      </div>

      {result && (
        <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Result</h2>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                result.status === "completed"
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {result.status}
            </span>
          </div>

          {result.final_response ? (
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{result.final_response}</p>
          ) : (
            <p className="text-sm text-gray-400 italic">No final response.</p>
          )}

          <ExecutionSteps steps={result.steps} />
        </div>
      )}
    </div>
  );
}
