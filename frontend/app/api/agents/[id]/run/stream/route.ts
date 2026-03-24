import { cookies } from "next/headers";
import { NextRequest } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

interface Props {
  params: Promise<{ id: string }>;
}

export async function POST(request: NextRequest, { params }: Props) {
  const { id } = await params;
  const store = await cookies();
  const token = store.get("token")?.value;

  const body = await request.json();

  const upstream = await fetch(`${API_URL}/agents/${id}/run/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  // Pipe the upstream SSE stream directly to the browser without buffering.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
