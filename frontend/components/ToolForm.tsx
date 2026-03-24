"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ToolResponse } from "@/lib/types";

interface Props {
  tool?: ToolResponse;
}

export default function ToolForm({ tool }: Props) {
  const router = useRouter();
  const isEdit = !!tool;
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const form = new FormData(e.currentTarget);
    const body = {
      name: form.get("name"),
      description: form.get("description"),
    };

    try {
      const url = isEdit ? `/api/tools/${tool.id}` : "/api/tools";
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

      router.push("/tools");
      router.refresh();
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!tool || !confirm(`Delete tool "${tool.name}"?`)) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/tools/${tool.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail ?? "Delete failed.");
        return;
      }
      router.push("/tools");
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
          defaultValue={tool?.name}
          placeholder="web-search"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          name="description"
          required
          rows={3}
          defaultValue={tool?.description}
          placeholder="Searches the web for information."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 resize-none"
        />
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
          {loading ? "Saving…" : isEdit ? "Save changes" : "Create tool"}
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
            Delete tool
          </button>
        )}
      </div>
    </form>
  );
}
