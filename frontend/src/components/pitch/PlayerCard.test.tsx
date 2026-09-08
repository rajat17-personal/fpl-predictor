import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { PlayerCard } from "./PlayerCard";
import { joinSquad, deriveViceCaptain, type PitchPlayer } from "../../lib/squadJoin";
import squadFixture from "../../test/fixtures/squad.json";
import xpFixture from "../../test/fixtures/xp_table_squad.json";
import type { SquadResponse, XpRow } from "../../lib/api";

const squad = (squadFixture as SquadResponse).squad;
const xp = xpFixture as XpRow[];
const joined = joinSquad(squad, xp);
const captainCode = squad.find((r) => r.captain)!.player_code;
const xpByCode = new Map(xp.map((row) => [row.player_code, row]));
const viceCode = deriveViceCaptain(
  squad.filter((r) => r.starting).map((r) => ({ player_code: r.player_code, captain: r.captain })),
  xpByCode,
);

function basePlayer(overrides: Partial<PitchPlayer> = {}): PitchPlayer {
  return {
    player_code: 1,
    name: "Test Player",
    team: "Test Town",
    position: "MID",
    price_m: 6.5,
    xp: 3.2,
    starting: true,
    captain: false,
    p10: 1.1,
    p90: 8.8,
    xp_capt: 4.5,
    team_short: "ARS",
    status: "a",
    news: "",
    ownership: 12.3,
    ...overrides,
  };
}

function renderSquad() {
  return render(
    <div>
      {joined.map((player) => (
        <PlayerCard
          key={player.player_code}
          player={player}
          captain={player.player_code === captainCode}
          vice={player.player_code === viceCode}
        />
      ))}
    </div>,
  );
}

describe("PlayerCard — C/VC badges (D-08)", () => {
  it("renders exactly one C badge and one different V badge across the fixture squad", () => {
    renderSquad();
    const cBadges = screen.getAllByText("C");
    const vBadges = screen.getAllByText("V");
    expect(cBadges).toHaveLength(1);
    expect(vBadges).toHaveLength(1);
    expect(cBadges[0]).not.toBe(vBadges[0]);
  });

  it("renders no V badge anywhere when every starter's xp_capt is null", () => {
    const players = [
      basePlayer({ player_code: 1, captain: true, xp_capt: 5.0 }),
      basePlayer({ player_code: 2, captain: false, xp_capt: null }),
      basePlayer({ player_code: 3, captain: false, xp_capt: null }),
    ];
    render(
      <div>
        {players.map((p) => (
          <PlayerCard key={p.player_code} player={p} captain={p.captain} vice={false} />
        ))}
      </div>,
    );
    expect(screen.queryAllByText("V")).toHaveLength(0);
  });
});

describe("PlayerCard — range line (D-06, UIX-01)", () => {
  it("renders '2.4–9.1' for p10=2.4/p90=9.1", () => {
    render(
      <PlayerCard
        player={basePlayer({ p10: 2.4, p90: 9.1 })}
        captain={false}
        vice={false}
      />,
    );
    expect(screen.getByText("2.4–9.1")).toBeInTheDocument();
  });

  it("falls back both bounds to xp when p10/p90 are both null, with no NaN", () => {
    render(
      <PlayerCard
        player={basePlayer({ xp: 3.7, p10: null, p90: null })}
        captain={false}
        vice={false}
      />,
    );
    expect(screen.getByText("3.7–3.7")).toBeInTheDocument();
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });

  it("still renders two bounds when p10 equals p90", () => {
    render(
      <PlayerCard player={basePlayer({ p10: 5.0, p90: 5.0 })} captain={false} vice={false} />,
    );
    expect(screen.getByText("5.0–5.0")).toBeInTheDocument();
  });
});

describe("PlayerCard — action popover (D-13)", () => {
  it("renders no popover trigger button and no menu when onMark is undefined", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} />);
    expect(screen.queryAllByRole("menu")).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Test Player actions" })).not.toBeInTheDocument();
  });

  it("opens a role=menu on click, closes on Escape, and closes on an outside click", () => {
    render(
      <div>
        <PlayerCard player={basePlayer()} captain={false} vice={false} onMark={vi.fn()} />
        <button type="button">outside</button>
      </div>,
    );
    const trigger = screen.getByRole("button", { name: "Test Player actions" });
    fireEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    fireEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "outside" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("omits the Clear menu item when mark is null, and shows it when mark is 'locked'", () => {
    const { rerender } = render(
      <PlayerCard player={basePlayer()} captain={false} vice={false} mark={null} onMark={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Test Player actions" }));
    expect(screen.queryByRole("menuitem", { name: "Clear" })).not.toBeInTheDocument();
    // Close the menu before rerendering so the next click reliably re-opens it.
    fireEvent.click(screen.getByRole("button", { name: "Test Player actions" }));

    rerender(
      <PlayerCard
        player={basePlayer()}
        captain={false}
        vice={false}
        mark="locked"
        onMark={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Test Player actions" }));
    expect(screen.getByRole("menuitem", { name: "Clear" })).toBeInTheDocument();
  });

  it("calls onMark with 'excluded' when choosing Exclude on a card whose mark is 'locked'", () => {
    const onMark = vi.fn();
    render(
      <PlayerCard
        player={basePlayer({ player_code: 42 })}
        captain={false}
        vice={false}
        mark="locked"
        onMark={onMark}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Test Player actions" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Exclude from squad" }));
    expect(onMark).toHaveBeenCalledWith(42, "excluded");
  });

  it("shows the full untruncated name in the popover header and falls back to an en dash for null ownership", () => {
    const longName = "A Very Long Player Name That Would Truncate On The Card";
    render(
      <PlayerCard
        player={basePlayer({
          name: longName,
          ownership: null,
        })}
        captain={false}
        vice={false}
        onMark={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: `${longName} actions` }));
    const menu = screen.getByRole("menu");
    expect(
      within(menu).getByText("A Very Long Player Name That Would Truncate On The Card"),
    ).toBeInTheDocument();
    expect(within(menu).getByText(/Ownership –/)).toBeInTheDocument();
  });
});

describe("PlayerCard — mark and diff badges (D-13, D-16, D-18)", () => {
  it("renders an accessible 'Locked — always included in solve' element for mark=locked", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} mark="locked" />);
    expect(screen.getByLabelText("Locked — always included in solve")).toBeInTheDocument();
  });

  it("renders an accessible 'Excluded from solve' element for mark=excluded", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} mark="excluded" />);
    expect(screen.getByLabelText("Excluded from solve")).toBeInTheDocument();
  });

  it("renders an accessible 'New signing this transfer' element for diff=in", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} diff="in" />);
    expect(screen.getByLabelText("New signing this transfer")).toBeInTheDocument();
  });

  it("defaults to no IN badge and no out treatment", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} />);
    expect(screen.queryByLabelText("New signing this transfer")).not.toBeInTheDocument();
    expect(screen.queryByText("Suggested transfer out")).not.toBeInTheDocument();
  });
});

describe("PlayerCard — outgoing red dashed outline (07-03 UAT G-07-2)", () => {
  it("gives diff=out the same dashed-outline idiom as GhostCard, in the bad token", () => {
    const { container } = render(
      <PlayerCard player={basePlayer()} captain={false} vice={false} diff="out" />,
    );
    const outer = container.firstElementChild as HTMLElement;
    expect(outer.className).toContain("border-dashed");
    expect(outer.className).toContain("border-bad");
  });

  it("applies no dashed outline for diff=none or diff=in", () => {
    const { container: noneContainer } = render(
      <PlayerCard player={basePlayer()} captain={false} vice={false} diff="none" />,
    );
    expect((noneContainer.firstElementChild as HTMLElement).className).not.toContain(
      "border-dashed",
    );

    const { container: inContainer } = render(
      <PlayerCard player={basePlayer()} captain={false} vice={false} diff="in" />,
    );
    expect((inContainer.firstElementChild as HTMLElement).className).not.toContain(
      "border-dashed",
    );
  });
});

describe("PlayerCard — pitch stat-line contrast (07-03 UAT G-07-1)", () => {
  it("uses the pitch-stat backdrop tokens for the price/xP line when onPitch is true", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} onPitch />);
    const statLine = screen.getByText("£6.5 · 3.2");
    expect(statLine.className).toContain("bg-pitch-stat-bg");
    expect(statLine.className).toContain("text-pitch-stat-ink");
  });

  it("keeps the plain ink-2 stat colour when onPitch is false (Bench, GhostCard)", () => {
    render(<PlayerCard player={basePlayer()} captain={false} vice={false} />);
    const statLine = screen.getByText("£6.5 · 3.2");
    expect(statLine.className).toContain("text-ink-2");
    expect(statLine.className).not.toContain("bg-pitch-stat-bg");
  });
});
