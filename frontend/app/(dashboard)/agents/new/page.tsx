import AgentForm from "@/components/AgentForm";
import { apiFetch } from "@/lib/api";
import type { ToolListResponse } from "@/lib/types";
import Link from "next/link";

export default async function NewAgentPage() {
  let tools: ToolListResponse = { items: [], total: 0 };
  try {
    tools = await apiFetch<ToolListResponse>("/tools");
  } catch {
    // Non-fatal — form still works with no tools
  }

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <Link href="/agents" className="text-sm text-gray-400 hover:text-gray-600">
          ← Agents
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-2">New agent</h1>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <AgentForm tools={tools.items} />
      </div>
    </div>
  );
}
