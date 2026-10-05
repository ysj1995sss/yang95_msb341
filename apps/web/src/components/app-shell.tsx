"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Briefcase, ClipboardList, FileText, Home, Send, UserRound, Wand2 } from "lucide-react";
import type { ReactNode } from "react";
import { ToastProvider, cx } from "@/components/ui";

const DESTINATIONS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/profile", label: "Career Profile", short: "Profile", icon: UserRound },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/tailor", label: "Tailor", icon: Wand2 },
  { href: "/apply", label: "Apply", icon: Send },
  { href: "/tracker", label: "Tracker", icon: ClipboardList },
];
// Phones: at most five items in the bottom bar; Career Profile stays in the top bar.
const BOTTOM = DESTINATIONS.filter((d) => d.href !== "/profile");

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children, signInEnabled, userName }: {
  children: ReactNode; signInEnabled: boolean; userName: string | null;
}) {
  const pathname = usePathname();
  if (pathname === "/signin") return <ToastProvider>{children}</ToastProvider>;
  const profileActive = isActive(pathname, "/profile");

  return (
    <ToastProvider>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-paper focus:p-3">
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-line bg-paper/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
          <Link href="/" className="flex items-center gap-2 font-[family-name:var(--font-heading)] text-[18px] font-semibold">
            <FileText aria-hidden className="size-6 text-primary" />
            Job Copilot
          </Link>
          <nav aria-label="Main" className="hidden flex-1 md:block">
            <ul className="flex items-center gap-1">
              {DESTINATIONS.map((d) => {
                const active = isActive(pathname, d.href);
                return (
                  <li key={d.href}>
                    <Link href={d.href} aria-current={active ? "page" : undefined}
                      className={cx("flex min-h-11 items-center rounded-[var(--radius-control)] px-3 text-[15px] font-semibold transition-colors duration-150",
                        active ? "bg-primary-soft text-primary" : "text-muted hover:bg-canvas hover:text-ink")}>
                      {d.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/profile" aria-current={profileActive ? "page" : undefined}
              className={cx("flex min-h-11 items-center gap-1.5 rounded-[var(--radius-control)] px-3 text-[15px] font-semibold md:hidden",
                profileActive ? "bg-primary-soft text-primary" : "text-muted")}>
              <UserRound aria-hidden className="size-5" /> Profile
            </Link>
            {signInEnabled ? (
              <form action="/api/auth/signout" method="post" className="flex items-center gap-2">
                {userName && <span className="hidden text-[14px] text-muted lg:inline">{userName}</span>}
                <button className="min-h-11 rounded-[var(--radius-control)] px-3 text-[15px] font-semibold text-muted hover:bg-canvas cursor-pointer">
                  Sign out
                </button>
              </form>
            ) : (
              <details className="relative">
                <summary className="cursor-pointer list-none rounded-full border border-review/30 bg-review-soft px-3 py-1 text-[13px] font-semibold text-review">
                  Local demo
                </summary>
                <p className="absolute right-0 z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-[var(--radius-card)] border border-line bg-paper p-3 text-[14px] text-muted">
                  Sign-in isn&apos;t set up here, so everyone using this address shares one workspace. Don&apos;t share
                  this link. Job Copilot only uses facts you&apos;ve confirmed and never submits for you.
                </p>
              </details>
            )}
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-6xl px-4 pt-6 pb-28 md:pb-12">{children}</main>

      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper md:hidden">
        <ul className="grid grid-cols-5">
          {BOTTOM.map((d) => {
            const active = isActive(pathname, d.href);
            const Icon = d.icon;
            return (
              <li key={d.href}>
                <Link href={d.href} aria-current={active ? "page" : undefined}
                  className={cx("flex min-h-14 flex-col items-center justify-center gap-0.5 text-[12px] font-semibold",
                    active ? "text-primary" : "text-muted")}>
                  <Icon aria-hidden className="size-5" />
                  {d.short ?? d.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </ToastProvider>
  );
}
