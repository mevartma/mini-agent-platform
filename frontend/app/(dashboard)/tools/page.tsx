import { apiFetch } from "@/lib/api";
import type { ToolListResponse } from "@/lib/types";
import Link from "next/link";

export default async function ToolsPage() {
  let data: ToolListResponse = { items: [], total: 0 };
  let fetchError = "";

  try {
    data = await apiFetch<ToolListResponse>("/tools");
  } catch (e) {
    fetchError = e instanceof Error ? e.message : "Failed to load tools.";
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Tools</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data.total} total</p>
        </div>
        <Link
          href="/tools/new"
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
        >
          New tool
        </Link>
      </div>

      {fetchError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          {fetchError}
        </p>
      )}

      {!fetchError && data.items.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-sm">No tools yet.</p>
          <Link href="/tools/new" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
            Create your first tool
          </Link>
        </div>
      )}

      {data.items.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {data.items.map((tool) => (
            <Link
              key={tool.id}
              href={`/tools/${tool.id}/edit`}
              className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{tool.name}</p>
                <p className="text-xs text-gray-500 mt-0.5 truncate">{tool.description}</p>
              </div>
              <span className="text-gray-300 ml-4 shrink-0">›</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
