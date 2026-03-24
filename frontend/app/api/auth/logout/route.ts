import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST() {
  const store = await cookies();
  const token = store.get("token")?.value;

  // Best-effort: blacklist the token on the API side
  if (token) {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {
      // Ignore — cookie will be cleared regardless
    });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set("token", "", { maxAge: 0, path: "/" });
  return response;
}
