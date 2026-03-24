import ExecutionSteps from "@/components/ExecutionSteps";
import { apiFetch, ApiError } from "@/lib/api";
import type { ExecutionListResponse } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ page?: string; limit?: string }>;
}

function statusBadge(status: string) {
  return status === "completed"
    ? "bg-green-100 text-green-700"
    : "bg-red-100 text-red-700";
}

export default async function HistoryPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { page = "1", limit = "10" } = await searchParams;

  let data: ExecutionListResponse;
  try {
    data = await apiFetch<ExecutionListResponse>(
      `/agents/${id}/executions?page=${page}&limit=${limit}`,
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  const currentPage = Number(page);

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <Link href="/agents" className="text-sm text-gray-400 hover:text-gray-600">
          ← Agents
        </Link>
        <div className="flex items-center justify-between mt-2">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Execution history</h1>
            <p className="text-sm text-gray-500 mt-0.5">{data.total} total</p>
          </div>
          <Link
            href={`/agents/${id}/run`}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            Run agent
          </Link>
        </div>
      </div>

      {data.items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-sm">No executions yet.</p>
          <Link href={`/agents/${id}/run`} className="mt-2 inline-block text-sm text-blue-600 hover:underline">
            Run this agent
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {data.items.map((execution) => (
            <div
              key={execution.id}
              className="bg-white rounded-xl border border-gray-200 px-5 py-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-800 line-clamp-2">{execution.task}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-xs text-gray-400">{execution.model}</span>
                    <span className="text-xs text-gray-300">·</span>
                    <span className="text-xs text-gray-400">
                      {new Date(execution.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge(execution.status)}`}>
                  {execution.status}
                </span>
              </div>

              {execution.final_response && (
                <p className="mt-3 text-sm text-gray-600 border-t border-gray-100 pt-3 line-clamp-3">
                  {execution.final_response}
                </p>
              )}

              <ExecutionSteps steps={execution.steps} />
            </div>
          ))}
        </div>
      )}

      {data.pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          {currentPage > 1 && (
            <Link
              href={`/agents/${id}/history?page=${currentPage - 1}&limit=${limit}`}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              ← Previous
            </Link>
          )}
          <span className="text-sm text-gray-400">
            Page {currentPage} of {data.pages}
          </span>
          {currentPage < data.pages && (
            <Link
              href={`/agents/${id}/history?page=${currentPage + 1}&limit=${limit}`}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Next →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
