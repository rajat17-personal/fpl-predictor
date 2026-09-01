import { useCallback, useEffect, useState } from "react";

/* Theme resolution (UIX-02, D-14..D-17). Mirrors frontend/index.html's inline
 * pre-mount head script exactly — same storage key, same coercion of
 * anything other than "light"/"dark" to "system" — so the two can never
 * disagree about which class belongs on <html>. */

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "fpl-theme";

/** Pure resolver: an explicit choice wins; "system" defers to the media query. */
export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme {
  if (choice === "dark") return "dark";
  if (choice === "light") return "light";
  return prefersDark ? "dark" : "light";
}

function readStoredChoice(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* storage access can throw (private browsing, storage disabled) — a
     * corrupt or inaccessible value falls through to the operating-system
     * result rather than throwing. */
  }
  return "system";
}

function getMediaQueryList(): MediaQueryList | null {
  try {
    if (typeof window === "undefined" || !window.matchMedia) return null;
    return window.matchMedia("(prefers-color-scheme: dark)");
  } catch {
    return null;
  }
}

/** Idempotent by construction — classList.toggle with the same boolean is a no-op. */
function applyResolvedTheme(resolved: ResolvedTheme) {
  document.documentElement.classList.toggle("dark", resolved === "dark");
}

export function useTheme(): {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setChoice: (next: ThemeChoice) => void;
} {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => readStoredChoice());
  const [resolved, setResolved] = useState<ResolvedTheme>(() => {
    const mql = getMediaQueryList();
    return resolveTheme(readStoredChoice(), mql?.matches ?? false);
  });

  // Apply the resolved theme to the document whenever it changes.
  useEffect(() => {
    applyResolvedTheme(resolved);
  }, [resolved]);

  // Recompute the resolved theme whenever the choice changes.
  useEffect(() => {
    const mql = getMediaQueryList();
    setResolved(resolveTheme(choice, mql?.matches ?? false));
  }, [choice]);

  // While choice === "system", track OS-level changes live; remove the
  // listener on unmount or as soon as the choice stops being "system".
  useEffect(() => {
    if (choice !== "system") return;
    const mql = getMediaQueryList();
    if (!mql) return;

    const handleChange = (event: MediaQueryListEvent | { matches: boolean }) => {
      setResolved(resolveTheme("system", event.matches));
    };

    mql.addEventListener("change", handleChange as EventListener);
    return () => mql.removeEventListener("change", handleChange as EventListener);
  }, [choice]);

  const setChoice = useCallback((next: ThemeChoice) => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* storage write failure degrades to session-only in-memory state — the
       * choice below is still applied and remains active for the session
       * (UI-SPEC E9); no user-facing error surface. */
    }
    setChoiceState(next);
  }, []);

  return { choice, resolved, setChoice };
}
