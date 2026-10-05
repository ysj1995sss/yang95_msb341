// Google returns here after the Gmail consent step. The code is exchanged server-side and the
// refresh token goes straight to the API, which stores it encrypted for this user only.
import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, apiToken, googleConfigured, readSession } from "@/lib/auth";
import { GMAIL_SCOPE, GMAIL_STATE_COOKIE } from "@/lib/gmail";

function back(request: NextRequest, result: string) {
  const url = new URL("/tracker", request.url);
  url.searchParams.set("gmail", result);
  const response = NextResponse.redirect(url);
  response.cookies.delete(GMAIL_STATE_COOKIE);
  return response;
}

export async function GET(request: NextRequest) {
  const session = await readSession(request.cookies.get(SESSION_COOKIE)?.value);
  if (!googleConfigured() || !session) return NextResponse.redirect(new URL("/signin", request.url));
  const params = request.nextUrl.searchParams;
  if (params.get("error")) return back(request, "declined");
  const code = params.get("code");
  const state = params.get("state");
  if (!code || !state || state !== request.cookies.get(GMAIL_STATE_COOKIE)?.value) return back(request, "expired");

  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.AUTH_GOOGLE_ID!,
      client_secret: process.env.AUTH_GOOGLE_SECRET!,
      redirect_uri: new URL("/api/gmail/callback", request.url).toString(),
      grant_type: "authorization_code",
    }),
  });
  if (!tokenResponse.ok) return back(request, "failed");
  const granted = (await tokenResponse.json()) as { refresh_token?: string; scope?: string };
  if (!granted.refresh_token || !(granted.scope ?? "").split(" ").includes(GMAIL_SCOPE)) return back(request, "declined");

  const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";
  const saved = await fetch(`${apiUrl}/v2/gmail/connect`, {
    method: "POST",
    headers: { authorization: `Bearer ${await apiToken(session)}`, "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: granted.refresh_token }),
    cache: "no-store",
  });
  return back(request, saved.ok ? "connected" : "failed");
}
