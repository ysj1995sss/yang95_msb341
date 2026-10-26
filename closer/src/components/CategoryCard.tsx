import { ArrowRight } from "lucide-react";
import { questionsFor } from "../data/questions";
import type { Category } from "../types";
import { href } from "../utils/router";
import { CategoryIcon } from "./CategoryIcon";

/** The whole card is one link into the category's questions. */
export function CategoryCard({ category, index = 0 }: { category: Category; index?: number }) {
  const count = questionsFor(category.id).length;
  return (
    <a
      href={href.play(category.id)}
      style={{ animationDelay: `${Math.min(index, 9) * 40}ms` }}
      className="group flex animate-fade-up flex-col gap-4 rounded-3xl border border-plum-100 bg-white/80 p-5 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-plum-200 hover:shadow-lg focus-visible:-translate-y-1"
    >
      <div className="flex items-start justify-between gap-3">
        <CategoryIcon category={category} />
        <span className="rounded-full bg-sand px-3 py-1 text-xs font-semibold text-muted">
          {category.id === "trivia" ? "Quiz" : `${count} questions`}
        </span>
      </div>
      <div>
        <h3 className="text-lg font-bold leading-snug">{category.name}</h3>
        <p className="mt-1 text-[15px] leading-relaxed text-muted">{category.description}</p>
      </div>
      <span className="mt-auto inline-flex items-center gap-1.5 text-[15px] font-bold text-plum-700">
        Start <ArrowRight aria-hidden className="size-4 transition-transform group-hover:translate-x-1" />
      </span>
    </a>
  );
}
