// Browser-side access to the workspace API, always through this app's own server
// (/api/backend), which adds the signed-in user's token.
"use client";

import { useCallback, useEffect, useState } from "react";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function readError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status}).`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") message = body.detail;
    else if (Array.isArray(body?.detail)) message = "Some fields need a look: " + body.detail.map((d: { msg?: string }) => d.msg).join("; ");
  } catch {
    /* keep the generic message */
  }
  if (response.status === 401 && typeof window !== "undefined") {
    window.location.assign(new URL("/signin", window.location.origin).href);
  }
  return new ApiError(message, response.status);
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  const response = await fetch(`/api/backend${path}`, {
    ...rest,
    headers: json === undefined ? rest.headers : { "Content-Type": "application/json", ...rest.headers },
    body: json === undefined ? rest.body : JSON.stringify(json),
    cache: "no-store",
  });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

/** Load a resource; `set` replaces it with a fresher copy (e.g. a save's response). */
export function useResource<T>(path: string | null) {
  const [version, setVersion] = useState(0);
  const key = path ? `${path}#${version}` : null;
  const [state, setState] = useState<{ key: string | null; data: T | null; error: Error | null }>(
    { key: null, data: null, error: null },
  );

  useEffect(() => {
    if (!path || !key) return;
    let cancelled = false;
    api<T>(path).then(
      (data) => { if (!cancelled) setState({ key, data, error: null }); },
      (error: Error) => { if (!cancelled) setState((s) => ({ key, data: s.data, error })); },
    );
    return () => { cancelled = true; };
  }, [path, key]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const set = useCallback((data: T) => setState((s) => ({ ...s, data, error: null })), []);
  return {
    data: state.data,
    error: state.error,
    loading: Boolean(key) && state.key !== key,
    reload,
    set,
  };
}
