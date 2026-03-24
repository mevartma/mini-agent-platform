import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const { name, slug, admin_email, admin_password } = await request.json();

  // Step 1: Register tenant
  const registerRes = await fetch(`${API_URL}/tenants/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, slug, admin_email, admin_password }),
  });

  if (!registerRes.ok) {
    const data = await registerRes
      .json()
      .catch(() => ({ detail: "Registration failed." }));
    return NextResponse.json({ detail: data.detail }, { status: registerRes.status });
  }

  // Step 2: Auto-login to get JWT
  const loginRes = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tenant_slug: slug, email: admin_email, password: admin_password }),
  });

  if (!loginRes.ok) {
    // Registration succeeded but login failed — redirect to login page
    return NextResponse.json({ ok: true, redirect: "/login" });
  }

  const { access_token, expires_in } = await loginRes.json();

  const response = NextResponse.json({ ok: true });
  response.cookies.set("token", access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: expires_in,
  });

  return response;
}
