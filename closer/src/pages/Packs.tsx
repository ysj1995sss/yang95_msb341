import { ArrowRight } from "lucide-react";
import { PackIcon } from "../components/PackIcon";
import { ProgressRing } from "../components/ProgressRing";
import { primary } from "../components/ui";
import { inSeason, orderedPacks, packById, seasonLabel } from "../data/packs";
import { packSet } from "../data/playSets";
import { savedProgress } from "../utils/resume";
import { href } from "../utils/router";
import { SetPlay } from "./SetPlay";

/** Seasonal packs: ten questions for an occasion each. The ones in season come first. */
export function Packs() {
  const today = new Date();
  const list = orderedPacks(today);
  return (
    <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Seasonal packs</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        Ten questions for a holiday, a season or a celebration. The pack that suits this time of year comes first.
      </p>
      <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((pack, i) => {
          const live = inSeason(pack, today);
          const progress = (() => { const set = packSet(pack.id); return set ? savedProgress(set) : null; })();
          return (
            <li key={pack.id}>
              <a href={href.pack(pack.id)} style={{ animationDelay: `${Math.min(i, 9) * 40}ms` }}
                className="group flex h-full animate-fade-up flex-col gap-4 rounded-3xl border border-plum-100 bg-surface/80 p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-plum-200 hover:shadow-lg focus-visible:-translate-y-1">
                <div className="flex items-start justify-between gap-3">
                  <PackIcon pack={pack} />
                  {live ? (
                    <span className="rounded-full bg-coral-100 px-3 py-1 text-xs font-bold text-coral-700">In season</span>
                  ) : (
                    <span className="rounded-full bg-sand px-3 py-1 text-xs font-semibold text-muted">{seasonLabel(pack)}</span>
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-bold leading-snug">{pack.name}</h2>
                  <p className="mt-1 text-[15px] leading-relaxed text-muted">{pack.blurb}</p>
                </div>
                <div className="mt-auto flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-1.5 text-[15px] font-bold text-plum-700 dark:text-onplum-soft">
                    {progress && !progress.finished ? "Continue" : "Start"} <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
                  </span>
                  {progress && (
                    <span className="flex items-center gap-2 text-sm font-semibold text-muted">
                      <ProgressRing done={progress.done} total={progress.total} size={28} /> {progress.done} of {progress.total} seen
                    </span>
                  )}
                </div>
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function PackPlay({ packId }: { packId: string }) {
  const pack = packById(packId);
  const set = packSet(packId);
  if (!pack || !set) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">We couldn't find that pack</h1>
        <p className="mt-3 text-muted">It may have moved. Pick one from the list instead.</p>
        <a href={href.packs} className={`${primary} mt-6`}>See all packs</a>
      </div>
    );
  }
  return <SetPlay set={set} backHref={href.packs} backLabel="Back to packs" icon={<PackIcon pack={pack} size="lg" />} />;
}
