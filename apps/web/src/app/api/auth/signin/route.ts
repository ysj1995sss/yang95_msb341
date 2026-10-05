// Starts Google sign-in (OpenID Connect, authorization-code flow).
import { randomBytes } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { STATE_COOKIE, googleConfigured } from "@/lib/auth";

export async function GET(request: NextRequest) {
  if (!googleConfigured()) return NextResponse.redirect(new URL("/", request.url));
  const state = randomBytes(24).toString("base64url");
  const params = new URLSearchParams({
    client_id: process.env.AUTH_GOOGLE_ID!,
    redirect_uri: new URL("/api/auth/callback/google", request.url).toString(),
    response_type: "code",
    scope: "openid email profile",
    state,
    prompt: "select_account",
  });
  const response = NextResponse.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params}`);
  response.cookies.set(STATE_COOKIE, state, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 600,
  });
  return response;
}
