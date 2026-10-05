// Google returns here. The code is exchanged server-side and the ID token's signature,
// issuer and audience are verified before a session cookie is set.
import { createRemoteJWKSet, jwtVerify } from "jose";
import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, STATE_COOKIE, createSession, currentSessionVersion, googleConfigured, sessionCookieOptions } from "@/lib/auth";

const GOOGLE_KEYS = createRemoteJWKSet(new URL("https://www.googleapis.com/oauth2/v3/certs"));

function fail(request: NextRequest, reason: string) {
  const url = new URL("/signin", request.url);
  url.searchParams.set("error", reason);
  return NextResponse.redirect(url);
}

export async function GET(request: NextRequest) {
  if (!googleConfigured()) return NextResponse.redirect(new URL("/", request.url));
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  if (!code || !state || state !== request.cookies.get(STATE_COOKIE)?.value) return fail(request, "expired");

  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: process.env.AUTH_GOOGLE_ID!,
      client_secret: process.env.AUTH_GOOGLE_SECRET!,
      redirect_uri: new URL("/api/auth/callback/google", request.url).toString(),
      grant_type: "authorization_code",
    }),
  });
  if (!tokenResponse.ok) return fail(request, "google");
  const { id_token: idToken } = (await tokenResponse.json()) as { id_token?: string };
  if (!idToken) return fail(request, "google");

  try {
    const { payload } = await jwtVerify(idToken, GOOGLE_KEYS, {
      issuer: ["https://accounts.google.com", "accounts.google.com"],
      audience: process.env.AUTH_GOOGLE_ID!,
    });
    if (!payload.sub || payload.email_verified === false) return fail(request, "unverified");
    const identity = { sub: payload.sub, name: String(payload.name ?? ""), email: String(payload.email ?? "") };
    const session = await createSession({ ...identity, sv: await currentSessionVersion(identity) });
    const response = NextResponse.redirect(new URL("/", request.url));
    response.cookies.set(SESSION_COOKIE, session, sessionCookieOptions);
    response.cookies.delete(STATE_COOKIE);
    return response;
  } catch {
    return fail(request, "google");
  }
}
