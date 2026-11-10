import { AudienceFilter } from "../components/AudienceFilter";
import { CategoryCard } from "../components/CategoryCard";
import { ModeCards } from "../components/ModeCards";
import { audienceSetting } from "../data/audience";
import { categories } from "../data/categories";
import { questions } from "../data/questions";
import { useSetting } from "../hooks";

export function Explore() {
  const audience = useSetting(audienceSetting);
  return (
    <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Explore experiences</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        Ten experiences for every kind of moment, {questions.length} questions in all. Choose who's playing and how deep to go, from light to bold, and heart the ones you love.
      </p>

      <AudienceFilter />

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-live="polite" data-audience={audience}>
        {categories.map((category, i) => <CategoryCard key={category.id} category={category} index={i} />)}
      </div>

      <h2 className="mt-14 text-2xl font-extrabold tracking-tight sm:text-3xl">More ways to play</h2>
      <div className="mt-6">
        <ModeCards />
      </div>
    </div>
  );
}
