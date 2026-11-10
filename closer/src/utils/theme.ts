import { createSetting } from "./settings";

export type Theme = "light" | "dark";
/** What the person chose: a theme, or "system" to follow the device. */
export type ThemeChoice = Theme | "system";

export const isThemeChoice = (value: unknown): value is ThemeChoice => value === "light" || value === "dark" || value === "system";

export const resolveTheme = (choice: ThemeChoice, systemDark: boolean): Theme =>
  choice === "system" ? (systemDark ? "dark" : "light") : choice;

/** The browser toolbar color on phones, to match the page. */
export const THEME_COLOR: Record<Theme, string> = { light: "#5b3fd1", dark: "#14102a" };

export const themeSetting = createSetting<ThemeChoice>("closer.theme", "system", isThemeChoice);

/** Puts the theme on the page: a data attribute the styles read, and the phone toolbar color. */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.dataset.theme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", THEME_COLOR[theme]);
}
