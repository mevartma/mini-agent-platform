import AgentForm from "@/components/AgentForm";
import { apiFetch, ApiError } from "@/lib/api";
import type { AgentResponse, ToolListResponse } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EditAgentPage({ params }: Props) {
  const { id } = await params;

  let agent: AgentResponse;
  let tools: ToolListResponse = { items: [], total: 0 };

  try {
    [agent, tools] = await Promise.all([
      apiFetch<AgentResponse>(`/agents/${id}`),
      apiFetch<ToolListResponse>("/tools"),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <Link href="/agents" className="text-sm text-gray-400 hover:text-gray-600">
          ← Agents
        </Link>
        <div className="flex items-center justify-between mt-2">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Edit agent</h1>
            <p className="text-sm text-gray-500 mt-0.5 font-mono">{agent.id}</p>
          </div>
          <div className="flex gap-3">
            <Link href={`/agents/${id}/run`} className="text-sm text-blue-600 hover:underline">
              Run
            </Link>
            <Link href={`/agents/${id}/history`} className="text-sm text-gray-500 hover:underline">
              History
            </Link>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <AgentForm tools={tools.items} agent={agent} />
      </div>
    </div>
  );
}
