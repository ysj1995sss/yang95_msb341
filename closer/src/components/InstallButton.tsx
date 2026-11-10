import { Download, Share, Smartphone } from "lucide-react";
import { useId, useState } from "react";
import { useInstall } from "../hooks";
import { secondary } from "./ui";

/** "Install app" where the browser can do it in one tap, a short "Add to Home Screen" hint on iPhone
 *  and Android, and nothing at all once Closer is installed or where installing isn't possible. */
export function InstallButton({ className = secondary }: { className?: string }) {
  const { mode, install } = useInstall();
  const [open, setOpen] = useState(false);
  const hintId = useId();

  if (mode === "installed" || mode === "none") return null;

  if (mode === "prompt") {
    return (
      <button type="button" onClick={() => void install()} className={className}>
        <Download aria-hidden className="size-5" /> Install app
      </button>
    );
  }

  return (
    <div>
      <button type="button" aria-expanded={open} aria-controls={hintId} onClick={() => setOpen((o) => !o)} className={className}>
        <Smartphone aria-hidden className="size-5" /> Add to Home Screen
      </button>
      {open && (
        <p id={hintId} className="mt-3 max-w-xs rounded-2xl bg-plum-50 p-3 text-sm text-muted">
          {mode === "ios" ? (
            <>
              Tap <Share aria-hidden className="mx-0.5 inline size-4 align-text-bottom text-plum-600 dark:text-onplum-soft" />
              <span className="font-bold text-plum-800"> Share</span> in Safari, then choose <span className="font-bold text-plum-800">Add to Home Screen</span>.
            </>
          ) : (
            <>Open your browser menu, then tap <span className="font-bold text-plum-800">Install app</span> or <span className="font-bold text-plum-800">Add to Home screen</span>.</>
          )}
        </p>
      )}
    </div>
  );
}
