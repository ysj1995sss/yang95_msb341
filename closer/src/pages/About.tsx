import { ArrowRight, Keyboard, PlayCircle, Smartphone } from "lucide-react";
import { HowItWorks } from "../components/HowItWorks";
import { InstallButton } from "../components/InstallButton";
import { primary, secondary } from "../components/ui";
import { href } from "../utils/router";
import { replayTour } from "../utils/tour";

const installSteps = [
  { device: "iPhone or iPad (Safari)", how: "Tap the Share button, then Add to Home Screen." },
  { device: "Android (Chrome)", how: "Open the menu, then tap Install app or Add to Home screen." },
  { device: "Computer (Chrome or Edge)", how: "Click the install icon at the right of the address bar." },
];

const shortcuts = [
  { keys: "→ or swipe left", does: "Next question" },
  { keys: "← or swipe right", does: "Skip this question" },
  { keys: "F", does: "Heart the question" },
  { keys: "T", does: "Table mode: one big card for reading aloud" },
  { keys: "R", does: "Read the question aloud" },
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
          This is an early prototype. There's no account and no sign-up: your favorites, your own questions and your
          progress are saved only in this browser, on this device. Online multiplayer and personalized questions are on the way.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href={href.explore} className={primary}>
            Start Exploring <ArrowRight aria-hidden className="size-5" />
          </a>
          <button type="button" onClick={replayTour} className={secondary}>
            <PlayCircle aria-hidden className="size-5" /> Replay the tour
          </button>
        </div>
      </section>

      <section aria-labelledby="install-heading">
        <h2 id="install-heading" className="flex items-center gap-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
          <Smartphone aria-hidden className="size-8 text-plum-600 dark:text-onplum-soft" /> Install Closer
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">
          Closer works like an app. Add it to your home screen and it opens full screen, with no app store, and keeps
          working without a connection once it has loaded.
        </p>
        <div className="mt-5"><InstallButton className={primary} /></div>
        <ul className="mt-6 grid gap-4 sm:grid-cols-3">
          {installSteps.map((step) => (
            <li key={step.device} className="rounded-3xl bg-surface/80 p-6 shadow-sm ring-1 ring-plum-100">
              <h3 className="text-lg font-bold">{step.device}</h3>
              <p className="mt-1 text-[15px] leading-relaxed text-muted">{step.how}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="shortcuts-heading">
        <h2 id="shortcuts-heading" className="flex items-center gap-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
          <Keyboard aria-hidden className="size-8 text-plum-600 dark:text-onplum-soft" /> Shortcuts
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">On any conversation question:</p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          {shortcuts.map((s) => (
            <div key={s.keys} className="flex items-center gap-4 rounded-2xl bg-surface/80 p-4 ring-1 ring-plum-100">
              <dt className="min-w-36 rounded-lg border border-plum-200 bg-surface px-3 py-1.5 text-center text-sm font-bold text-plum-800">{s.keys}</dt>
              <dd className="text-[15px] text-muted">{s.does}</dd>
            </div>
          ))}
        </dl>
      </section>

      <HowItWorks id="about-how" />
    </div>
  );
}
