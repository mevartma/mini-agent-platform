"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AgentResponse, ToolResponse } from "@/lib/types";

interface Props {
  tools: ToolResponse[];
  agent?: AgentResponse; // present when editing
}

export default function AgentForm({ tools, agent }: Props) {
  const router = useRouter();
  const isEdit = !!agent;

  const [selectedToolIds, setSelectedToolIds] = useState<Set<string>>(
    new Set(agent?.tools.map((t) => t.id) ?? []),
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function toggleTool(id: string) {
    setSelectedToolIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const form = new FormData(e.currentTarget);
    const body = {
      name: form.get("name"),
      role: form.get("role"),
      description: form.get("description"),
      tool_ids: [...selectedToolIds],
    };

    try {
      const url = isEdit ? `/api/agents/${agent.id}` : "/api/agents";
      const method = isEdit ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail ?? "Request failed.");
        return;
      }

      router.push("/agents");
      router.refresh();
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!agent || !confirm(`Delete agent "${agent.name}"?`)) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/agents/${agent.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail ?? "Delete failed.");
        return;
      }
      router.push("/agents");
      router.refresh();
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          name="name"
          required
          defaultValue={agent?.name}
          placeholder="Research Bot"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
        <input
          name="role"
          required
          defaultValue={agent?.role}
          placeholder="Researcher"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          name="description"
          required
          rows={3}
          defaultValue={agent?.description}
          placeholder="Finds and summarises information on any topic."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Tools</label>
        {tools.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No tools yet — create some first.</p>
        ) : (
          <div className="space-y-2">
            {tools.map((tool) => (
              <label key={tool.id} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedToolIds.has(tool.id)}
                  onChange={() => toggleTool(tool.id)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  <span className="font-medium text-gray-800">{tool.name}</span>
                  <span className="text-gray-500 ml-2">{tool.description}</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          {loading ? "Saving…" : isEdit ? "Save changes" : "Create agent"}
        </button>

        <button
          type="button"
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>

        {isEdit && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={loading}
            className="ml-auto text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            Delete agent
          </button>
        )}
      </div>
    </form>
  );
}
