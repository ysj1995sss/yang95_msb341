import { ArrowRight } from "lucide-react";
import { HowItWorks } from "../components/HowItWorks";
import { href } from "../utils/router";

export function About() {
  return (
    <div className="mx-auto max-w-4xl space-y-16 px-4 pt-12 sm:px-6">
      <section>
        <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">About Closer</h1>
        <p className="mt-5 text-lg leading-relaxed text-muted">
          Closer is a question-based social experience. It helps couples, friends, families and teams talk about
          things that matter, laugh more, and learn something new about each other and themselves.
        </p>
        <p className="mt-4 text-lg leading-relaxed text-muted">
          This is an early prototype. There's no account and no sign-up: anything you write is saved only in this
          browser, on this device. Multiplayer rooms, personalized questions and a mobile app are on the way.
        </p>
        <a href={href.explore} className="mt-8 inline-flex min-h-12 items-center gap-2 rounded-full bg-plum-600 px-7 font-bold text-white shadow-lg shadow-plum-600/25 transition hover:bg-plum-700">
          Start Exploring <ArrowRight aria-hidden className="size-5" />
        </a>
      </section>
      <HowItWorks id="about-how" />
    </div>
  );
}
