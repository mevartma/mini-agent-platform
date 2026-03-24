import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const store = await cookies();
  const token = store.get("token")?.value;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

interface Props {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: Props) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") ?? "50";
  const offset = searchParams.get("offset") ?? "0";
  const res = await fetch(
    `${API_URL}/chat/${id}/messages?limit=${limit}&offset=${offset}`,
    { headers: await authHeaders(), cache: "no-store" }
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(request: NextRequest, { params }: Props) {
  const { id } = await params;
  const body = await request.json();
  const res = await fetch(`${API_URL}/chat/${id}/messages`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
