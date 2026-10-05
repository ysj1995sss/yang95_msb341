// Optimistic route guard: with Google sign-in configured, pages need a session cookie.
// The real check happens on every API call (api/backend) and in the API itself.
import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, googleConfigured, readSession } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  if (!googleConfigured()) return NextResponse.next();
  const session = await readSession(request.cookies.get(SESSION_COOKIE)?.value);
  if (session) return NextResponse.next();
  return NextResponse.redirect(new URL("/signin", request.url));
}

export const config = {
  // Everything except sign-in, auth callbacks, the API proxy (it answers 401 itself) and static files.
  matcher: ["/((?!signin|api/|_next/|favicon.ico|.*\\.(?:svg|png|ico|webp|woff2?)$).*)"],
};
