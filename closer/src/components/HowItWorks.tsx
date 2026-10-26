import { Compass, MessageCircleHeart, SkipForward } from "lucide-react";

const steps = [
  { icon: Compass, title: "Choose your experience", text: "Ten ways in: date night, a party, a family dinner, a new team, or just you." },
  { icon: MessageCircleHeart, title: "Discover interesting questions", text: "One question at a time, picked fresh each round so it never feels repetitive." },
  { icon: SkipForward, title: "Answer, skip, keep going", text: "Talk it out, jot down an answer, or skip. No sign-up, no pressure." },
];

export function HowItWorks({ id }: { id?: string }) {
  return (
    <section id={id} aria-labelledby={`${id ?? "how"}-heading`} className="scroll-mt-24">
      <h2 id={`${id ?? "how"}-heading`} className="text-3xl font-extrabold tracking-tight sm:text-4xl">How it works</h2>
      <ol className="mt-8 grid gap-4 sm:grid-cols-3">
        {steps.map((step, i) => (
          <li key={step.title} className="rounded-3xl bg-white/80 p-6 shadow-sm ring-1 ring-plum-100">
            <div className="flex items-center gap-3">
              <span className="inline-flex size-10 items-center justify-center rounded-full bg-coral-100 font-extrabold text-coral-700">{i + 1}</span>
              <step.icon aria-hidden className="size-6 text-plum-600" />
            </div>
            <h3 className="mt-4 text-lg font-bold">{step.title}</h3>
            <p className="mt-1 text-[15px] leading-relaxed text-muted">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
