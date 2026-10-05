// Asks Google for read-only Gmail access, separately from sign-in (spec 005, decision 030).
// Only a signed-in person can start it; the refresh token never reaches the browser.
import { randomBytes } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, googleConfigured, readSession } from "@/lib/auth";
import { GMAIL_SCOPE, GMAIL_STATE_COOKIE } from "@/lib/gmail";

export async function GET(request: NextRequest) {
  const session = await readSession(request.cookies.get(SESSION_COOKIE)?.value);
  if (!googleConfigured() || !session) return NextResponse.redirect(new URL("/tracker", request.url));
  const state = randomBytes(24).toString("base64url");
  const params = new URLSearchParams({
    client_id: process.env.AUTH_GOOGLE_ID!,
    redirect_uri: new URL("/api/gmail/callback", request.url).toString(),
    response_type: "code",
    scope: GMAIL_SCOPE,
    access_type: "offline",
    prompt: "consent",
    login_hint: session.email,
    state,
  });
  const response = NextResponse.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params}`);
  response.cookies.set(GMAIL_STATE_COOKIE, state, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 600,
  });
  return response;
}
