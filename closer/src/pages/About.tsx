import { ArrowRight, HardDrive, Info, Keyboard, PlayCircle, Smartphone } from "lucide-react";
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

const h2 = "flex items-center gap-3 text-3xl font-extrabold tracking-tight sm:text-4xl";
const h2Icon = "size-8 shrink-0 text-plum-600 dark:text-onplum-soft";

/** Help first (shortcuts, how it works, installing, where things are saved), then what Closer is.
 *  Reached as #/help from the top bar and footer, and as #/about. */
export function About() {
  return (
    <div className="mx-auto max-w-4xl space-y-16 px-4 pt-12 sm:px-6">
      <section>
        <h1 tabIndex={-1} className="text-4xl font-extrabold tracking-tight sm:text-5xl">Help</h1>
        <p className="mt-5 text-lg leading-relaxed text-muted">
          Keyboard shortcuts, how a round works, installing Closer as an app, and where your things are saved.
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

      <section aria-labelledby="shortcuts-heading">
        <h2 id="shortcuts-heading" className={h2}>
          <Keyboard aria-hidden className={h2Icon} /> Shortcuts
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">
          On any conversation question, once you've clicked on the card or pressed Tab to reach it. They never fire anywhere else on the page.
        </p>
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

      <section aria-labelledby="install-heading">
        <h2 id="install-heading" className={h2}>
          <Smartphone aria-hidden className={h2Icon} /> Install Closer
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

      <section aria-labelledby="storage-heading">
        <h2 id="storage-heading" className={h2}>
          <HardDrive aria-hidden className={h2Icon} /> Where your things are saved
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">
          There's no account. Your favorites and your own questions are saved only in this browser, on this device.
          Clearing your browsing data, using a private window, or switching to another browser or device starts you
          with none of them. Rounds in progress are kept while you're using the app and start fresh the next time you open it.
        </p>
      </section>

      <section aria-labelledby="about-heading">
        <h2 id="about-heading" className={h2}>
          <Info aria-hidden className={h2Icon} /> About Closer
        </h2>
        <p className="mt-3 text-lg leading-relaxed text-muted">
          Closer is a question-based social experience. It helps couples, friends, families and teams talk about
          things that matter, laugh more, and learn something new about each other and themselves.
        </p>
        <p className="mt-4 text-lg leading-relaxed text-muted">
          This is an early prototype. Online multiplayer and personalized questions are on the way.
        </p>
      </section>
    </div>
  );
}
