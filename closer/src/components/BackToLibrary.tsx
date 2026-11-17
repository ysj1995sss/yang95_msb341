import { ArrowLeft } from "lucide-react";
import { href } from "../utils/router";

/** "Back to library", at the top of the pages the Library page leads to. */
export function BackToLibrary() {
  return (
    <a href={href.library} className="-ml-3 mb-4 inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-[15px] font-bold text-plum-700 transition-colors hover:bg-plum-50 dark:text-onplum-soft">
      <ArrowLeft aria-hidden className="size-4" /> Back to library
    </a>
  );
}
