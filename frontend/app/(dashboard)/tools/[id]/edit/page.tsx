import ToolForm from "@/components/ToolForm";
import { apiFetch, ApiError } from "@/lib/api";
import type { ToolResponse } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EditToolPage({ params }: Props) {
  const { id } = await params;

  let tool: ToolResponse;
  try {
    tool = await apiFetch<ToolResponse>(`/tools/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <Link href="/tools" className="text-sm text-gray-400 hover:text-gray-600">
          ← Tools
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-2">Edit tool</h1>
        <p className="text-sm text-gray-500 mt-0.5 font-mono">{tool.id}</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <ToolForm tool={tool} />
      </div>
    </div>
  );
}
