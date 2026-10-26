import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="mt-20 bg-plum-900 text-plum-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <Logo light />
          <p className="mt-2 text-sm text-plum-200">Every connection starts with a question.</p>
        </div>
        <p className="text-sm text-plum-200">
          Prototype v0.1 · Your answers stay on this device.
        </p>
      </div>
    </footer>
  );
}
