import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { resolveTheme, THEME_STORAGE_KEY, useTheme } from "./theme";

/* Installs a window.matchMedia stub that records its `change` listeners so a
 * test can dispatch a synthetic media-query change event, mirroring how the
 * real browser fires it when the OS theme flips. */
function installMatchMediaStub(initialMatches: boolean) {
  let matches = initialMatches;
  const listeners = new Set<(ev: { matches: boolean }) => void>();

  const mql = {
    get matches() {
      return matches;
    },
    media: "(prefers-color-scheme: dark)",
    addEventListener: (event: string, cb: (ev: { matches: boolean }) => void) => {
      if (event === "change") listeners.add(cb);
    },
    removeEventListener: (event: string, cb: (ev: { matches: boolean }) => void) => {
      if (event === "change") listeners.delete(cb);
    },
  };

  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => mql),
  );

  return {
    listenerCount: () => listeners.size,
    fireChange: (nextMatches: boolean) => {
      matches = nextMatches;
      for (const cb of listeners) cb({ matches: nextMatches });
    },
  };
}

/* Installs a localStorage stub whose setItem can be made to throw, for the
 * storage-write-failure degradation case (UI-SPEC E9). */
function installThrowingStorage() {
  const store = new Map<string, string>();
  const stub: Storage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: () => {
      throw new Error("storage disabled");
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => store.clear(),
    key: () => null,
    get length() {
      return store.size;
    },
  };
  vi.stubGlobal("localStorage", stub);
}

describe("resolveTheme", () => {
  it("resolves system to dark when the media query matches", () => {
    expect(resolveTheme("system", true)).toBe("dark");
  });

  it("resolves system to light when the media query does not match", () => {
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("resolves dark regardless of the media query", () => {
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("resolves light regardless of the media query", () => {
    expect(resolveTheme("light", true)).toBe("light");
  });
});

describe("useTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.classList.remove("dark");
  });

  it("falls through to the operating-system result for a corrupt or unrecognised stored value", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "not-a-real-choice");
    installMatchMediaStub(true);

    const { result } = renderHook(() => useTheme());

    expect(result.current.choice).toBe("system");
    expect(result.current.resolved).toBe("dark");
  });

  it("adds the dark class to document.documentElement when dark is chosen", () => {
    installMatchMediaStub(false);
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("dark");
    });

    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes the dark class from document.documentElement when light is chosen", () => {
    installMatchMediaStub(true);
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("light");
    });

    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("writes the chosen theme to localStorage", () => {
    installMatchMediaStub(false);
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("dark");
    });

    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("still applies the theme and updates state when the storage write throws", () => {
    installThrowingStorage();
    installMatchMediaStub(false);
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("dark");
    });

    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(result.current.choice).toBe("dark");
  });

  it("flips the class on a media-query change while the choice is system, without a reload", () => {
    const media = installMatchMediaStub(false);
    const { result } = renderHook(() => useTheme());

    expect(result.current.choice).toBe("system");
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    act(() => {
      media.fireChange(true);
    });

    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("does not move the class on a media-query change once the choice is dark or light", () => {
    const media = installMatchMediaStub(false);
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("light");
    });
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    act(() => {
      media.fireChange(true);
    });

    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("removes the media-query listener on unmount", () => {
    const media = installMatchMediaStub(false);
    const { unmount } = renderHook(() => useTheme());

    expect(media.listenerCount()).toBeGreaterThan(0);

    unmount();

    expect(media.listenerCount()).toBe(0);
  });

  it("leaves the class list unchanged when the same resolved theme is applied twice", () => {
    installMatchMediaStub(false);
    const { result, rerender } = renderHook(() => useTheme());

    act(() => {
      result.current.setChoice("light");
    });
    const before = document.documentElement.className;

    rerender();

    expect(document.documentElement.className).toBe(before);
  });
});
