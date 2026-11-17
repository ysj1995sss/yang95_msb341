import { Download, Smartphone, X } from "lucide-react";
import { useId, useState } from "react";
import { useInstall, useInstallCardShown } from "../hooks";
import { installCardDismissed } from "../utils/installCard";
import { InstallHint } from "./InstallButton";
import { primary } from "./ui";

/** "Install Closer", once, on phones: it appears after someone has started a round, on any top-level
 *  page, and goes away when they close it or install. */
export function InstallCard() {
  const { mode, install } = useInstall();
  const [open, setOpen] = useState(false);
  const hintId = useId();
  const shown = useInstallCardShown();
  if (!shown) return null;

  return (
    <section aria-label="Install Closer" className="mx-auto max-w-6xl px-4 pt-4 sm:hidden">
      <div className="relative rounded-3xl border border-plum-200 bg-surface p-4 pr-12 shadow-sm">
        <button type="button" onClick={() => installCardDismissed.set(true)} aria-label="Close install card"
          className="absolute right-1 top-1 inline-flex size-11 cursor-pointer items-center justify-center rounded-full text-muted transition-colors hover:bg-sand hover:text-ink">
          <X aria-hidden className="size-5" />
        </button>
        <div className="flex items-start gap-3">
          <span aria-hidden className="inline-flex size-11 shrink-0 items-center justify-center rounded-2xl bg-plum-600 text-white">
            <Smartphone className="size-5" />
          </span>
          <div>
            <h2 className="font-extrabold leading-snug">Install Closer</h2>
            <p className="mt-0.5 text-sm text-muted">Open it from your home screen like any app. It works without a connection.</p>
          </div>
        </div>
        <div className="mt-3">
          {mode === "prompt" ? (
            <button type="button" onClick={() => void install()} className={primary}>
              <Download aria-hidden className="size-5" /> Install app
            </button>
          ) : (
            <>
              <button type="button" aria-expanded={open} aria-controls={hintId} onClick={() => setOpen((o) => !o)} className={primary}>
                Show me how
              </button>
              {open && <InstallHint id={hintId} mode={mode} />}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
