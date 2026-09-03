import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SquadTab, selectLoadedSquad, lockedCodes, excludedCodes, type MarkRecord } from "./SquadTab";
import squadFixture from "../../test/fixtures/squad.json";
import xpFixture from "../../test/fixtures/xp_table_squad.json";
import metaFixture from "../../test/fixtures/meta.json";
import teamResponseFixture from "../../test/fixtures/team_response.json";

const FIXTURES: Record<string, unknown> = {
  "/data/squad.json": squadFixture,
  "/data/xp_table.json": xpFixture,
  "/data/meta.json": metaFixture,
  "/api/team/6980093": teamResponseFixture,
};

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
