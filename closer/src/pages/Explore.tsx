import { AudienceFilter } from "../components/AudienceFilter";
import { CategoryGrid } from "../components/CategoryGrid";
import { categories } from "../data/categories";
import { questions } from "../data/questions";
import { numberWord } from "../utils/words";

export function Explore() {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Explore experiences</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        {numberWord(categories.length)} experiences for every kind of moment, {questions.length} questions in all. Choose who's playing and how deep to go, from light to bold, and heart the ones you love.
      </p>

      <AudienceFilter />

      <div className="mt-6">
        <CategoryGrid />
      </div>
    </div>
  );
}
