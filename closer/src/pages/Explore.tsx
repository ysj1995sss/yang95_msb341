import { CategoryCard } from "../components/CategoryCard";
import { GuessPromo } from "../components/GuessPromo";
import { categories } from "../data/categories";

export function Explore() {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-12 sm:px-6">
      <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Explore experiences</h1>
      <p className="mt-3 max-w-2xl text-lg text-muted">
        Ten experiences for every kind of moment, with 50 questions each. Choose how deep to go, from light to bold, and heart the ones you love.
      </p>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((category, i) => <CategoryCard key={category.id} category={category} index={i} />)}
      </div>
      <div className="mt-10">
        <GuessPromo />
      </div>
    </div>
  );
}
