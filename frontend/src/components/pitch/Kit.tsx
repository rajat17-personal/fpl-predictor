import type { KitPattern } from "./kitMap";

export interface KitProps {
  primary: string;
  secondary: string;
  pattern: KitPattern;
}

/* One parameterized inline SVG shirt (D-01, D-02). Colours arrive only as
 * props — this component body contains no colour literal of its own. No
 * crest, no sponsor mark, no club-name text, and no external image; every
 * pattern variant is drawn with SVG shapes only. aria-hidden because the
 * shirt carries no information the player card's name text does not.
 * Fixed viewBox so it scales cleanly at every card size, desktop down to
 * the 400px-viewport compact variant. */
export function Kit({ primary, secondary, pattern }: KitProps) {
  const shirtPath =
    "M8 4 L2 8 L4 12 L7 10 L7 26 Q7 28 9 28 L23 28 Q25 28 25 26 L25 10 L28 12 L30 8 L24 4 " +
    "Q22 6 16 6 Q10 6 8 4 Z";

  return (
    <svg viewBox="0 0 32 32" role="img" aria-hidden="true" className="h-8 w-8">
      <path d={shirtPath} fill={primary} stroke={secondary} strokeWidth="0.75" />
      {pattern === "stripes" && (
        <>
          <rect x="11" y="6" width="3" height="22" fill={secondary} />
          <rect x="18" y="6" width="3" height="22" fill={secondary} />
        </>
      )}
      {pattern === "hoops" && (
        <>
          <rect x="7" y="11" width="18" height="3" fill={secondary} />
          <rect x="7" y="18" width="18" height="3" fill={secondary} />
          <rect x="7" y="25" width="18" height="3" fill={secondary} />
        </>
      )}
      {pattern === "sleeves" && (
        <>
          <path d="M8 4 L2 8 L4 12 L7 10 L7 6 Z" fill={secondary} />
          <path d="M24 4 L30 8 L28 12 L25 10 L25 6 Z" fill={secondary} />
        </>
      )}
      <path
        d="M12 6 Q16 9 20 6"
        fill="none"
        stroke={secondary}
        strokeWidth="1.25"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default Kit;
