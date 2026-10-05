"use client";

// Any page that throws while rendering lands here instead of a blank screen.
import { Alert, Button } from "@/components/ui";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl py-10">
      <Alert tone="blocked" role="alert" title="This page didn't load">
        <p>Something went wrong showing this page. Your data is safe.</p>
        {error.digest && <p className="mt-1 text-[14px] text-muted">Reference: {error.digest}</p>}
      </Alert>
      <Button variant="primary" className="mt-4" onClick={reset}>Try again</Button>
    </div>
  );
}
