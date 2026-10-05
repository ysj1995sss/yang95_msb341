// Server-only: sign-in session and the token the API trusts (spec 009, decision 029).
//
// With AUTH_GOOGLE_ID unset, the app runs in local single-user mode (like the Streamlit
// app without [auth]): no sign-in, and the API treats every request as the local owner.
import { SignJWT, jwtVerify } from "jose";

export const SESSION_COOKIE = "jc_session";
export const STATE_COOKIE = "jc_oauth_state";
const SESSION_DAYS = 7;

export type Session = { sub: string; name: string; email: string };

export function googleConfigured(): boolean {
  return Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET);
}

function key(name: "AUTH_SECRET" | "WORKSPACE_TOKEN_SECRET"): Uint8Array {
  const value = process.env[name];
  if (!value || value.length < 32) {
    throw new Error(`${name} must be set to a random value of at least 32 characters`);
  }
  return new TextEncoder().encode(value);
}

export async function createSession(session: Session): Promise<string> {
  return new SignJWT({ name: session.name, email: session.email })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(session.sub)
    .setIssuedAt()
    .setExpirationTime(`${SESSION_DAYS}d`)
    .sign(key("AUTH_SECRET"));
}

export async function readSession(cookie: string | undefined): Promise<Session | null> {
  if (!cookie) return null;
  try {
    const { payload } = await jwtVerify(cookie, key("AUTH_SECRET"), { algorithms: ["HS256"] });
    if (!payload.sub) return null;
    return { sub: payload.sub, name: String(payload.name ?? ""), email: String(payload.email ?? "") };
  } catch {
    return null;
  }
}

/** A five-minute token for one API request, for the signed-in user only. */
export async function apiToken(session: Session): Promise<string> {
  return new SignJWT({ name: session.name, email: session.email })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(session.sub)
    .setAudience("job-copilot-workspace")
    .setIssuedAt()
    .setExpirationTime("5m")
    .sign(key("WORKSPACE_TOKEN_SECRET"));
}

export const sessionCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: SESSION_DAYS * 24 * 60 * 60,
};
