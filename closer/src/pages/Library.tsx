import { Calendar, Heart, PenLine } from "lucide-react";
import { HubGrid, type HubEntry } from "../components/HubCard";
import { inSeason, orderedPacks } from "../data/packs";
import { useCustomQuestions, useFavorites } from "../hooks";
import { href } from "../utils/router";

/** "1 question", "3 questions". */
const countOf = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** Everything that is the person's own, on one page: favorites, the questions they wrote, and the
 *  seasonal packs. Each card opens the page that holds it. */
export function Library() {
  const favoriteCount = useFavorites().length;
  const mineCount = useCustomQuestions().length;
  const today = new Date();
  const packs = orderedPacks(today);
  const seasonal = packs.find((p) => inSeason(p, today));
  const entries: HubEntry[] = [
    {
      title: "Favorites", to: href.favorites, cta: "Open", icon: Heart, tint: "rose", gradient: "from-coral-500 to-plum-500",
      text: "The questions you hearted, grouped by experience, ready to play again.",
      detail: favoriteCount ? `${countOf(favoriteCount, "question", "questions")} saved` : "None saved yet",
    },
    {
      title: "My questions", to: href.mine, cta: "Open", icon: PenLine, tint: "sky", gradient: "from-sky-400 to-plum-600",
      text: "Write questions for your own group and play them any time.",
      detail: mineCount ? `${countOf(mineCount, "question", "questions")} written` : "None written yet",
    },
    {
      title: "Seasonal packs", to: href.packs, cta: "Open", icon: Calendar, tint: "yellow", gradient: "from-amber-400 to-coral-500",
      text: "Ten questions for a holiday, a season or a celebration.",
      detail: seasonal ? `In season: ${seasonal.name}` : `${packs.length} packs`,
    },
  ];
  return (
    <div className="mx-auto max-w-5xl px-4 pt-10 sm:px-6 sm:pt-14">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Library</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">Your favorites, your own questions and the seasonal packs. It all stays in this browser on this device, so clearing browser data removes it.</p>
      <HubGrid entries={entries} />
    </div>
  );
}
