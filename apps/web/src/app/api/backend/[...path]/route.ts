// Backend-for-frontend: the browser calls /api/backend/..., this server forwards to the
// workspace API with a short-lived token for the signed-in user. The browser never holds
// an API credential, and the API is never exposed to it directly (decision 029).
import { type NextRequest } from "next/server";
import { SESSION_COOKIE, apiToken, googleConfigured, readSession } from "@/lib/auth";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const FORWARDED_HEADERS = ["content-type", "accept"];

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const headers = new Headers();
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (googleConfigured()) {
    const session = await readSession(request.cookies.get(SESSION_COOKIE)?.value);
    if (!session) return Response.json({ detail: "Sign in to continue." }, { status: 401 });
    headers.set("authorization", `Bearer ${await apiToken(session)}`);
  }
  const target = `${API_URL}/v2/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(request.method);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
    });
  } catch {
    return Response.json({ detail: "Job Copilot's server isn't reachable. Try again in a moment." }, { status: 502 });
  }
  const out = new Headers();
  for (const name of ["content-type", "content-disposition"]) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
