import { apiFetch } from "@/lib/api";
import type { AgentListResponse } from "@/lib/types";
import Link from "next/link";

export default async function AgentsPage() {
  let data: AgentListResponse = { items: [], total: 0 };
  let fetchError = "";

  try {
    data = await apiFetch<AgentListResponse>("/agents");
  } catch (e) {
    fetchError = e instanceof Error ? e.message : "Failed to load agents.";
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Agents</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data.total} total</p>
        </div>
        <Link
          href="/agents/new"
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          New agent
        </Link>
      </div>

      {fetchError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          {fetchError}
        </p>
      )}

      {!fetchError && data.items.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-sm">No agents yet.</p>
          <Link href="/agents/new" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
            Create your first agent
          </Link>
        </div>
      )}

      {data.items.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {data.items.map((agent) => (
            <Link
              key={agent.id}
              href={`/agents/${agent.id}/edit`}
              className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{agent.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">{agent.role}</p>
              </div>
              <div className="flex items-center gap-4 ml-4 shrink-0">
                <span className="text-xs text-gray-400">
                  {agent.tools.length} {agent.tools.length === 1 ? "tool" : "tools"}
                </span>
                <span className="text-gray-300">›</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
