import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type ThemeChoice } from "../lib/theme";

/* Three-state Light / Dark / System segmented control (UIX-02, D-15). Pill
 * styling family shared with the GW banner chip: surface background, line
 * border, rounded-full. Active button reuses the nav's active-link accent
 * token pairing. Token classes only — no hex literal. */
const OPTIONS: { choice: ThemeChoice; label: string; Icon: typeof Sun }[] = [
  { choice: "light", label: "Light theme", Icon: Sun },
  { choice: "dark", label: "Dark theme", Icon: Moon },
  { choice: "system", label: "System theme", Icon: Monitor },
];

export default function ThemeToggle() {
  const { choice, setChoice } = useTheme();

  return (
    <div className="flex items-center gap-0.5 rounded-full border border-line bg-surface p-0.5">
      {OPTIONS.map(({ choice: optionChoice, label, Icon }) => {
        const isActive = choice === optionChoice;
        return (
          <button
            key={optionChoice}
            type="button"
            aria-label={label}
            aria-pressed={isActive}
            onClick={() => setChoice(optionChoice)}
            className={`flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full ${
              isActive
                ? "bg-accent-bg text-accent-ink"
                : "text-ink-2 hover:bg-surface-2"
            }`}
          >
            <Icon size={16} aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
