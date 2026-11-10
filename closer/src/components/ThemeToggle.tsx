import { Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks";

/** Light or dark. Starts with the device's setting; a tap makes it the person's own choice. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button type="button" onClick={toggle} aria-pressed={dark} aria-label="Dark mode"
      className="inline-flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted transition-colors hover:bg-sand hover:text-ink">
      {dark ? <Sun aria-hidden className="size-5" /> : <Moon aria-hidden className="size-5" />}
    </button>
  );
}
