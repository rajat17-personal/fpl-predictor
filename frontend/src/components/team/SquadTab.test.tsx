import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent, renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  SquadTab,
  selectLoadedSquad,
  lockedCodes,
  excludedCodes,
  buildSolveRequest,
  useSolveController,
  type MarkRecord,
} from "./SquadTab";
import squadFixture from "../../test/fixtures/squad.json";
import xpFixture from "../../test/fixtures/xp_table_squad.json";
import metaFixture from "../../test/fixtures/meta.json";
import teamResponseFixture from "../../test/fixtures/team_response.json";
import solveFixture from "../../test/fixtures/solve_transfers_response.json";
import type { SolveRequest } from "../../lib/api";

const FIXTURES: Record<string, unknown> = {
  "/data/squad.json": squadFixture,
  "/data/xp_table.json": xpFixture,
  "/data/meta.json": metaFixture,
  "/api/team/6980093": teamResponseFixture,
};

interface FetchResponseLike {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

/** Handles the fixture GETs above plus POST /api/solve, delegated to
 * `solveImpl` so each test controls timing/outcome. Returns the parsed
 * request bodies sent to /api/solve, in call order. */
function mockFetchWithSolve(solveImpl: (body: SolveRequest) => Promise<FetchResponseLike>) {
  const solveCalls: SolveRequest[] = [];
  globalThis.fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.endsWith("/api/solve")) {
      const body = JSON.parse(init?.body as string) as SolveRequest;
      solveCalls.push(body);
      return solveImpl(body);
    }
    const path = Object.keys(FIXTURES).find((key) => url.endsWith(key));
    if (!path) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(FIXTURES[path]) });
  }) as unknown as typeof fetch;
  return solveCalls;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function mockFetchByUrl(overrides: Record<string, unknown> = {}) {
  const body = { ...FIXTURES, ...overrides };
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const path = Object.keys(body).find((key) => url.endsWith(key));
    if (!path) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body[path]) });
  }) as unknown as typeof fetch;
}

function renderSquadTab(props: Partial<Parameters<typeof SquadTab>[0]> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onLoadEntry = vi.fn();
  const onClearEntry = vi.fn();
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <SquadTab entry={null} onLoadEntry={onLoadEntry} onClearEntry={onClearEntry} {...props} />
    </QueryClientProvider>,
  );
  return { ...utils, onLoadEntry, onClearEntry };
}

describe("selectLoadedSquad (03-02 Task 1: starter/captain reconstruction)", () => {
  it("selects exactly 11 starters with exactly 1 GK, and marks the highest-xp_capt starter as captain", () => {
    const rows = selectLoadedSquad(teamResponseFixture.picks, xpFixture);
    const starters = rows.filter((r) => r.starting);
    expect(starters).toHaveLength(11);
    expect(starters.filter((r) => r.position === "GK")).toHaveLength(1);
    expect(rows.filter((r) => r.captain)).toHaveLength(1);
  });

  it("gives a pick missing from the xp table xp: 0 and never selects it as a starter", () => {
    const rows = selectLoadedSquad(teamResponseFixture.picks, xpFixture);
    const unmapped = rows.find((r) => r.player_code === 999001);
    expect(unmapped).toBeDefined();
    expect(unmapped?.xp).toBe(0);
    expect(unmapped?.starting).toBe(false);
  });

  it("returns exactly 15 rows for a 15-pick squad, preserving every player_code", () => {
    const rows = selectLoadedSquad(teamResponseFixture.picks, xpFixture);
    expect(rows).toHaveLength(15);
    expect(new Set(rows.map((r) => r.player_code)).size).toBe(15);
  });
});

describe("lockedCodes / excludedCodes (03-04 Task 1: mark-record derivations)", () => {
  it("returns numeric player_code values for locked players and an empty array when nothing is locked", () => {
    const marks: MarkRecord = { 97032: "locked", 141746: "excluded", 184029: "locked" };
    const locked = lockedCodes(marks);
    expect(locked.sort((a, b) => a - b)).toEqual([97032, 184029]);
    expect(locked.every((c) => typeof c === "number")).toBe(true);
    expect(lockedCodes({})).toEqual([]);
  });

  it("returns numeric player_code values for excluded players and an empty array when nothing is excluded", () => {
    const marks: MarkRecord = { 97032: "locked", 141746: "excluded" };
    expect(excludedCodes(marks)).toEqual([141746]);
    expect(excludedCodes({})).toEqual([]);
  });
});

describe("SquadTab (03-02 Task 1)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the model squad and a Load-your-own-team control when entry is null", async () => {
    mockFetchByUrl();
    renderSquadTab();

    expect(await screen.findByText("Model squad · GW3")).toBeInTheDocument();
    expect(screen.getByLabelText("FPL team ID")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load team" })).toBeInTheDocument();
  });

  it("calls onLoadEntry with the numeric id when Load team is clicked with a valid value", async () => {
    mockFetchByUrl();
    const { onLoadEntry } = renderSquadTab();

    await screen.findByText("Model squad · GW3");
    fireEvent.change(screen.getByLabelText("FPL team ID"), { target: { value: "6980093" } });
    fireEvent.click(screen.getByRole("button", { name: "Load team" }));

    expect(onLoadEntry).toHaveBeenCalledWith(6980093);
  });

  it("does not call onLoadEntry for a non-numeric value", async () => {
    mockFetchByUrl();
    const { onLoadEntry } = renderSquadTab();

    await screen.findByText("Model squad · GW3");
    fireEvent.change(screen.getByLabelText("FPL team ID"), { target: { value: "abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Load team" }));

    expect(onLoadEntry).not.toHaveBeenCalled();
  });

  it("renders the loaded team's banner and a working Change team control", async () => {
    mockFetchByUrl();
    const { onClearEntry } = renderSquadTab({ entry: 6980093 });

    expect(await screen.findByText("The Testers · GW3")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Change team" }));
    expect(onClearEntry).toHaveBeenCalled();
  });

  it("keeps the missing-xp pick on the bench in the rendered loaded squad", async () => {
    mockFetchByUrl();
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    expect(within(screen.getByTestId("bench")).getByText("Unmapped")).toBeInTheDocument();
  });
});

describe("SquadTab lock/exclude marks (03-04 Task 1)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders no popover trigger and no menu in the default model-squad mode", async () => {
    mockFetchByUrl();
    renderSquadTab();

    await screen.findByText("Model squad · GW3");
    fireEvent.click(screen.getByText("Virgil"));
    expect(screen.queryAllByRole("button", { name: /actions$/ })).toHaveLength(0);
    expect(screen.queryAllByRole("menu")).toHaveLength(0);
  });

  it("locks a player through the action menu, rendering the Locked badge on that card and no other", async () => {
    mockFetchByUrl();
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));

    expect(
      screen.getAllByLabelText("Locked — always included in solve"),
    ).toHaveLength(1);
    expect(screen.queryAllByLabelText("Excluded from solve")).toHaveLength(0);
  });

  it("excluding an already-locked player leaves exactly one badge on that card, the excluded one", async () => {
    mockFetchByUrl();
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));
    expect(screen.getAllByLabelText("Locked — always included in solve")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Exclude from squad" }));

    expect(screen.queryAllByLabelText("Locked — always included in solve")).toHaveLength(0);
    expect(screen.getAllByLabelText("Excluded from solve")).toHaveLength(1);
  });

  it("Clear removes the badge and the Clear item is then absent from the reopened menu", async () => {
    mockFetchByUrl();
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));
    expect(screen.getAllByLabelText("Locked — always included in solve")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Clear" }));

    expect(screen.queryAllByLabelText("Locked — always included in solve")).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    expect(screen.queryByRole("menuitem", { name: "Clear" })).not.toBeInTheDocument();
  });

  it("keeps both marks in place after the loaded squad re-renders with a new squad array (e.g. after a solve)", async () => {
    mockFetchByUrl();
    const { rerender } = renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));
    fireEvent.click(screen.getByRole("button", { name: "Egan actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Exclude from squad" }));

    expect(screen.getAllByLabelText("Locked — always included in solve")).toHaveLength(1);
    expect(screen.getAllByLabelText("Excluded from solve")).toHaveLength(1);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    rerender(
      <QueryClientProvider client={queryClient}>
        <SquadTab entry={6980093} onLoadEntry={vi.fn()} onClearEntry={vi.fn()} />
      </QueryClientProvider>,
    );

    await screen.findByText("The Testers · GW3");
    expect(screen.getAllByLabelText("Locked — always included in solve")).toHaveLength(1);
    expect(screen.getAllByLabelText("Excluded from solve")).toHaveLength(1);
  });
});

describe("buildSolveRequest (03-04 Task 2)", () => {
  it("carries numeric locked/excluded player_code arrays and no marked player's display name anywhere in the body", () => {
    const marks: MarkRecord = { 97032: "locked", 108416: "excluded" };
    const body = buildSolveRequest(
      6980093,
      { freeTransfers: 1, maxTransfers: null, horizon: 1 },
      marks,
    );
    expect(body.locks).toEqual([97032]);
    expect(body.excludes).toEqual([108416]);
    expect(body.locks.every((c) => typeof c === "number")).toBe(true);
    expect(body.excludes.every((c) => typeof c === "number")).toBe(true);
    expect(JSON.stringify(body)).not.toContain("Virgil");
    expect(JSON.stringify(body)).not.toContain("Egan");
  });

  it("omits max_transfers entirely when the value is null", () => {
    const body = buildSolveRequest(6980093, { freeTransfers: 1, maxTransfers: null, horizon: 1 }, {});
    expect(body).not.toHaveProperty("max_transfers");
  });

  it("includes max_transfers when a numeric value is supplied", () => {
    const body = buildSolveRequest(6980093, { freeTransfers: 1, maxTransfers: 4, horizon: 2 }, {});
    expect(body.max_transfers).toBe(4);
    expect(body.horizon).toBe(2);
  });
});

describe("SquadTab solve flow (03-04 Task 2)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("sends locks/excludes as numeric player_code arrays, with no marked display name in the request body", async () => {
    const { promise } = deferred<FetchResponseLike>();
    const solveCalls = mockFetchWithSolve(() => promise);
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));
    fireEvent.click(screen.getByRole("button", { name: "Egan actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Exclude from squad" }));

    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    await vi.waitFor(() => expect(solveCalls).toHaveLength(1));
    expect(solveCalls[0].locks).toEqual([97032]);
    expect(solveCalls[0].excludes).toEqual([108416]);
    expect(JSON.stringify(solveCalls[0])).not.toContain("Virgil");
    expect(JSON.stringify(solveCalls[0])).not.toContain("Egan");
  });

  it("omits max_transfers from the request body when the input is left empty", async () => {
    const { promise } = deferred<FetchResponseLike>();
    const solveCalls = mockFetchWithSolve(() => promise);
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    await vi.waitFor(() => expect(solveCalls).toHaveLength(1));
    expect(solveCalls[0]).not.toHaveProperty("max_transfers");
  });

  it("renders exactly 'Solving your transfers…', disables the solve button, and keeps the pitch's cards in the document", async () => {
    const { promise } = deferred<FetchResponseLike>();
    mockFetchWithSolve(() => promise);
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Solving your transfers…");
    expect(screen.getByRole("button", { name: "Solve transfers" })).toBeDisabled();
    expect(screen.getByText("Virgil")).toBeInTheDocument();
  });

  it("renders 'Couldn't solve:' and 'Check your inputs and try again.' on a rejected solve", async () => {
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ detail: "no solution" }) }),
    );
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    expect(await screen.findByText(/Couldn't solve:/)).toBeInTheDocument();
    expect(screen.getByText(/no solution/)).toBeInTheDocument();
    expect(screen.getByText(/Check your inputs and try again\./)).toBeInTheDocument();
  });

  it("renders the solved squad in place after a successful solve", async () => {
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(solveFixture) }),
    );
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    expect(await screen.findByText("Haaland")).toBeInTheDocument();
    expect(screen.getByText("Palmer")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

/* useSolveController's ordering-safety guard (T-03-16), tested directly via
 * renderHook rather than through two real button clicks: SolveControls'
 * `disabled` prop (D-15/T-03-15) is what stops a real user from ever
 * dispatching a second solve through the rendered UI, and browsers (jsdom
 * included) suppress click dispatch to a genuinely disabled form control
 * regardless of how the test tries to force it — so simulating "two
 * overlapping user clicks" through fireEvent cannot reliably exercise this
 * path. Calling solveNow() twice back-to-back exercises the exact same
 * production code the button would call, without fighting that browser
 * behaviour. */
describe("useSolveController ordering safety (03-04 Task 2, T-03-16)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("never lets a superseded solve response overwrite a newer one", async () => {
    const first = deferred<FetchResponseLike>();
    const second = deferred<FetchResponseLike>();
    const responses = [first.promise, second.promise];
    const solveCalls = mockFetchWithSolve(() => responses.shift()!);

    const { result } = renderHook(() => useSolveController(6980093, {}));

    act(() => {
      void result.current.solveNow({ freeTransfers: 1, maxTransfers: null, horizon: 1 });
    });
    expect(result.current.solve.status).toBe("pending");

    act(() => {
      void result.current.solveNow({ freeTransfers: 1, maxTransfers: null, horizon: 1 });
    });
    expect(solveCalls).toHaveLength(2);

    const staleFirstResponse = { ...solveFixture, captain: "StaleCaptain" };

    // The newer (second) solve resolves first.
    second.resolve({ ok: true, status: 200, json: () => Promise.resolve(solveFixture) });
    await vi.waitFor(() => expect(result.current.solve.status).toBe("success"));
    expect(result.current.solve.data?.captain).toBe("Haaland");

    // The first (now-superseded) solve resolves afterward — must not change
    // the applied result at all.
    first.resolve({ ok: true, status: 200, json: () => Promise.resolve(staleFirstResponse) });
    await new Promise((r) => setTimeout(r, 20));
    expect(result.current.solve.status).toBe("success");
    expect(result.current.solve.data?.captain).toBe("Haaland");
  });
});

describe("SquadTab solve results — in-place update, results bar, Reset (03-04 Task 3)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function solveOnce() {
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(solveFixture) }),
    );
    renderSquadTab({ entry: 6980093 });
    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));
    await screen.findByText("Haaland");
  }

  it("renders exactly one pitch with the solve fixture's 15 players after a solve resolves", async () => {
    await solveOnce();
    expect(screen.getAllByTestId("bench")).toHaveLength(1);
    for (const row of solveFixture.squad) {
      expect(screen.getByText(row.name)).toBeInTheDocument();
    }
  });

  it("badges only the two incoming players (absent from the loaded-team fixture) as New signing this transfer", async () => {
    await solveOnce();
    expect(screen.getAllByLabelText("New signing this transfer")).toHaveLength(2);
  });

  it("carries no out treatment on any card after a solve", async () => {
    await solveOnce();
    expect(screen.queryByText("Suggested transfer out")).not.toBeInTheDocument();
  });

  it("renders the results bar with one line per sell-to-buy pair from the fixture", async () => {
    await solveOnce();
    const bar = screen.getByTestId("solve-results-bar");
    expect(bar.textContent).toContain("McBurnie");
    expect(bar.textContent).toContain("Haaland");
    expect(bar.textContent).toContain("Unmapped");
    expect(bar.textContent).toContain("Palmer");
  });

  it("renders Hold in the results bar for a mutated zero-buys solve", async () => {
    const noBuys = { ...solveFixture, buys: [] };
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(noBuys) }),
    );
    renderSquadTab({ entry: 6980093 });
    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    const bar = await screen.findByTestId("solve-results-bar");
    expect(within(bar).getByText("Hold")).toBeInTheDocument();
  });

  it("renders −8 pts in hits for the two-hit fixture", async () => {
    await solveOnce();
    expect(screen.getByText("−8 pts in hits")).toBeInTheDocument();
  });

  it("omits the hit-cost clause for a mutated zero-hit solve", async () => {
    const zeroHits = { ...solveFixture, hits: 0 };
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(zeroHits) }),
    );
    renderSquadTab({ entry: 6980093 });
    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    const bar = await screen.findByTestId("solve-results-bar");
    expect(within(bar).queryByText(/pts in hits/)).not.toBeInTheDocument();
  });

  it("renders the bank, xi_xp and captain in the results bar", async () => {
    await solveOnce();
    const bar = screen.getByTestId("solve-results-bar");
    expect(bar.textContent).toContain(`Bank £${solveFixture.bank_after.toFixed(1)}m`);
    expect(bar.textContent).toContain(`XI xP ${solveFixture.xi_xp}`);
    expect(bar.textContent).toContain(`Captain ${solveFixture.captain}`);
  });

  it("Reset to loaded squad restores the loaded team, clears marks and the results bar, and issues no further fetch", async () => {
    const solveCalls = mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(solveFixture) }),
    );
    renderSquadTab({ entry: 6980093 });

    await screen.findByText("The Testers · GW3");
    fireEvent.click(screen.getByRole("button", { name: "Virgil actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Lock in squad" }));
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));
    await screen.findByText("Haaland");
    expect(solveCalls).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "Reset to loaded squad" }));

    expect(screen.queryByText("Haaland")).not.toBeInTheDocument();
    expect(screen.getByText("McBurnie")).toBeInTheDocument();
    expect(screen.queryAllByLabelText("Locked — always included in solve")).toHaveLength(0);
    expect(screen.queryByTestId("solve-results-bar")).not.toBeInTheDocument();
    expect(solveCalls).toHaveLength(1);
  });

  it("solving twice with identical marks and control values renders an identical squad, results bar, and captain", async () => {
    mockFetchWithSolve(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(solveFixture) }),
    );
    renderSquadTab({ entry: 6980093 });
    await screen.findByText("The Testers · GW3");

    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));
    await screen.findByText("Haaland");
    const firstBarText = screen.getByTestId("solve-results-bar").textContent;

    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));
    await vi.waitFor(() => expect(screen.getByTestId("solve-results-bar")).toBeInTheDocument());

    const secondBarText = screen.getByTestId("solve-results-bar").textContent;
    expect(secondBarText).toBe(firstBarText);
    for (const row of solveFixture.squad) {
      expect(screen.getByText(row.name)).toBeInTheDocument();
    }
    expect(screen.getByText(`Captain ${solveFixture.captain}`)).toBeInTheDocument();
  });
});
