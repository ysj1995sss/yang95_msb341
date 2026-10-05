// The privacy policy for the web app and the browser helper (decision 030). Public, so Google's
// OAuth review and the Chrome Web Store listing can link to it. Keep it true to the code.
import type { Metadata } from "next";
import { FileText } from "lucide-react";
import Link from "next/link";

export const metadata: Metadata = { title: "Privacy" };

const UPDATED = "October 5, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-[20px] font-semibold">{title}</h2>
      <div className="mt-2 flex flex-col gap-2 [&_li]:ml-5 [&_li]:list-disc">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  const contact = process.env.PRIVACY_CONTACT;
  return (
    <main id="main" className="mx-auto max-w-2xl px-4 py-10">
      <Link href="/" className="flex items-center gap-2 font-[family-name:var(--font-heading)] text-[18px] font-semibold">
        <FileText aria-hidden className="size-6 text-primary" /> Job Copilot
      </Link>
      <h1 className="mt-6 text-[30px] font-semibold">Privacy</h1>
      <p className="mt-1 text-muted">Last updated {UPDATED}. This covers the Job Copilot website and the Job Copilot form helper for Chrome and Edge.</p>

      <Section title="What Job Copilot keeps">
        <p>Only what you give it or create in it, in a folder that belongs to your account alone:</p>
        <ul>
          <li>Your Career Profile: the facts read from the resume you upload, and the edits and confirmations you make.</li>
          <li>The resume files you upload and the tailored resumes made from them.</li>
          <li>Jobs you searched for, saved or passed on, and your search goals.</li>
          <li>Applications you track, their status history, next steps and notes, and answers you saved for application questions.</li>
          <li>If you sign in with Google: your name, email address and an account number from Google. Your Google password never reaches Job Copilot.</li>
          <li>Counters for daily usage limits, and server logs of each request (the page address, the result and the time, not what you typed).</li>
        </ul>
      </Section>

      <Section title="Who else sees any of it">
        <ul>
          <li><strong>The AI model that tailors your resume.</strong> To tailor a resume, your confirmed facts and the job description are sent to the model provider this site uses, or to your own model if you entered one for a run. Nothing else is sent to it.</li>
          <li><strong>Job boards.</strong> Job Copilot downloads public job listings from Greenhouse, Lever, Ashby and SmartRecruiters. It sends them nothing about you. Applying happens on the employer&apos;s own site, by you.</li>
          <li><strong>Nobody else.</strong> Job Copilot doesn&apos;t sell your data, show ads, or use it to train AI models.</li>
        </ul>
      </Section>

      <Section title="Gmail (only if you connect it)">
        <p>In Tracker you can connect Gmail so Job Copilot can suggest status updates from recruiter emails.</p>
        <ul>
          <li>Google asks for read-only access. Gmail has no narrower permission, so it covers your whole mailbox, but Job Copilot only searches for emails from job-application systems (Greenhouse, Lever, Ashby, Workday, SmartRecruiters) from the last 30 days, and only when you click <strong>Check Gmail now</strong>.</li>
          <li>Those emails are read on the server to suggest a status and then discarded. Job Copilot keeps the ids of emails you confirmed or dismissed, so they aren&apos;t suggested again, and the subject line of an email you confirm, as evidence in that application&apos;s history.</li>
          <li>It never sends, changes or deletes email. Nothing in Tracker changes until you confirm a suggestion.</li>
          <li>The access token is stored encrypted. <strong>Disconnect Gmail</strong> removes it and tells Google to revoke it.</li>
          <li>Job Copilot&apos;s use of information received from Google APIs adheres to the Google API Services User Data Policy, including the Limited Use requirements.</li>
        </ul>
      </Section>

      <Section title="The form helper for Chrome and Edge">
        <ul>
          <li>It runs only when you click <strong>Fill this page</strong>, and only on that tab. It has no access to pages otherwise.</li>
          <li>Your kit (the answers and the tailored resume you copied from Apply) is stored only in your browser. <strong>Forget my kit</strong> removes it.</li>
          <li>It fills fields on the page you&apos;re on and sends nothing anywhere. It never submits a form.</li>
        </ul>
      </Section>

      <Section title="Your choices">
        <ul>
          <li><strong>Download my data</strong> (Career Profile → Your data) gives you everything Job Copilot keeps for you, as a zip file.</li>
          <li><strong>Delete my account and data</strong> removes it all from the server straight away.</li>
          <li><strong>Sign out on every device</strong> ends every session at once.</li>
        </ul>
      </Section>

      <Section title="Questions">
        <p>{contact ? <>Write to <a className="underline" href={`mailto:${contact}`}>{contact}</a>.</> : "Use the contact address on the page where you found Job Copilot."}</p>
      </Section>
    </main>
  );
}
