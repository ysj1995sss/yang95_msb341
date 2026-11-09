import { useMemo } from "react";
import { SessionView } from "../components/SessionView";
import { primary } from "../components/ui";
import { categoryById } from "../data/categories";
import { questionsFor } from "../data/questions";
import { href } from "../utils/router";

export function QuestionExperience({ categoryId }: { categoryId: string }) {
  const category = categoryById(categoryId);
  const pool = useMemo(() => (category ? questionsFor(category.id) : []), [category]);
  if (!category) {
    return (
      <div className="mx-auto max-w-3xl px-4 pt-16 sm:px-6">
        <h1 tabIndex={-1} className="text-3xl font-extrabold">We couldn't find that experience</h1>
        <p className="mt-3 text-muted">It may have moved. Pick one of the ten experiences instead.</p>
        <a href={href.explore} className={`${primary} mt-6`}>See all experiences</a>
      </div>
    );
  }
  return (
    <SessionView
      category={category}
      heading={category.name}
      description={category.description}
      pool={pool}
      persistKey={`play:${category.id}`}
      backHref={href.explore}
      backLabel="Back to categories"
    />
  );
}
