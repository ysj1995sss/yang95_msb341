import { ArrowRight, Smartphone } from "lucide-react";
import { HowItWorks } from "../components/HowItWorks";
import { href } from "../utils/router";

const installSteps = [
  { device: "iPhone or iPad (Safari)", how: "Tap the Share button, then Add to Home Screen." },
  { device: "Android (Chrome)", how: "Open the menu, then tap Install app or Add to Home screen." },
  { device: "Computer (Chrome or Edge)", how: "Click the install icon at the right of the address bar." },
];

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
          This is an early prototype. There's no account and no sign-up: your favorites are saved only in this
          browser, on this device. Online multiplayer and personalized questions are on the way.
        </p>
        <a href={href.explore} className="mt-8 inline-flex min-h-12 items-center gap-2 rounded-full bg-plum-600 px-7 font-bold text-white shadow-lg shadow-plum-600/25 transition hover:bg-plum-700">
          Start Exploring <ArrowRight aria-hidden className="size-5" />
        </a>
      </section>
      <section aria-labelledby="install-heading">
        <h2 id="install-heading" className="flex items-center gap-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
          <Smartphone aria-hidden className="size-8 text-plum-600" /> Install Closer
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">
          Closer works like an app. Add it to your home screen and it opens full screen, with no app store, and keeps
          working without a connection once it has loaded.
        </p>
        <ul className="mt-6 grid gap-4 sm:grid-cols-3">
          {installSteps.map((step) => (
            <li key={step.device} className="rounded-3xl bg-white/80 p-6 shadow-sm ring-1 ring-plum-100">
              <h3 className="text-lg font-bold">{step.device}</h3>
              <p className="mt-1 text-[15px] leading-relaxed text-muted">{step.how}</p>
            </li>
          ))}
        </ul>
      </section>
      <HowItWorks id="about-how" />
    </div>
  );
}
