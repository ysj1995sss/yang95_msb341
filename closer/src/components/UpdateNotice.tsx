import { RefreshCw } from "lucide-react";
import { useSyncExternalStore } from "react";
import { updateWatch } from "../utils/update";

/** "New version available": shown when a newer Closer has been installed behind the page. One tap
 *  reloads into it. `aboveTabBar` lifts it clear of the phone's tab bar. */
export function UpdateNotice({ aboveTabBar }: { aboveTabBar: boolean }) {
  const watch = updateWatch();
  const available = useSyncExternalStore(watch.subscribe, watch.get, () => false);
  if (!available) return null;
  return (
    <div role="status" className={`fixed inset-x-3 z-30 mx-auto flex max-w-md items-center gap-3 rounded-2xl bg-plum-800 p-3 pl-4 text-onplum shadow-lg sm:inset-x-auto sm:right-6 sm:mx-0 ${aboveTabBar ? "bottom-[calc(var(--tab-bar-height)+1rem+env(safe-area-inset-bottom))] sm:bottom-6" : "bottom-[calc(1rem+env(safe-area-inset-bottom))]"}`}>
      <p className="flex-1 text-sm font-semibold">New version available</p>
      <button type="button" onClick={() => window.location.reload()}
        className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full bg-onplum px-4 text-sm font-bold text-plum-900">
        <RefreshCw aria-hidden className="size-4" /> Tap to refresh
      </button>
    </div>
  );
}
