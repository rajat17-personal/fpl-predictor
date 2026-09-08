"""One shared player-identity crosswalk keyed on `player_code` (D-03).

Problem: this phase introduces three foreign identity namespaces at once
(Understat, FotMob, FBref) on top of the existing FPL-internal identity in
`data/id_map.py`. Without a shared crosswalk, each enrichment source would
grow its own divergent name matcher -- exactly the kind of many-to-many join
that once silently corrupted a whole backtest in `data/fbref.py` (see
IMPROVEMENTS.md Phase E).

`data/id_map.py` stays the sole authority for FPL identity; `player_code`
remains the canonical join key everywhere. This module is an *alias table*
keyed by `player_code`, built from theFPLkiwi's committed `ID_Dictionary.csv`
(`data/external/kiwi/ID_Dictionary.csv`, see `data/external/README.md`) --
not a competing identity model.

IMPORTANT: the committed `ID_Dictionary.csv` carries NO Understat identifier
column (verified 2026-09-08 against the live upstream repository; this
settles 09-RESEARCH.md's Open Question 3 and assumption A5 in the negative --
no Understat IDs exist upstream). `resolve_by_name()` -- normalised-name
matching, with a manual `_NAME_FIXUPS` override for misses -- is therefore
the REQUIRED fallback path for resolving Understat player names to
`player_code`, and for any other source without a direct id column.

Run:
  python -m data.id_crosswalk        # (re)build data/processed/id_crosswalk.parquet
"""
from __future__ import annotations

import functools
import sys

import pandas as pd

import config

_SRC = config.ROOT / "data" / "external" / "kiwi" / "ID_Dictionary.csv"
_OUT = config.PROCESSED_DIR / "id_crosswalk.parquet"

# Source name -> a name that resolves via one of resolve_by_name()'s tiers
# (extend as later plans discover more -- same manual-override convention as
# data/fbref.py's _NAME_FIXUPS).
#
# Entries below were added by plan 09-08's first real Understat join. Understat
# displays many Portuguese/Brazilian/Spanish players by their popular nickname
# or a shortened name, while `data/id_map.py` (the historical registry
# `_fpl_name_index()` matches against) stores each player's full legal name.
# Every entry here was verified by requiring BOTH of the Understat display
# name's tokens (never a single mononym -- see rationale below) to appear as
# WHOLE tokens (never a coincidental substring) within exactly one candidate's
# full name in `data/id_map.py` -- e.g. "Ricardo Pereira" only maps here
# because both "ricardo" and "pereira" are whole tokens inside exactly one
# id_map full name, "Ricardo Domingos Barbosa Pereira", and no other. This
# mechanically rules out the coincidental-substring false positives a naive
# substring search finds (e.g. "Palacios" matching an unrelated different
# player also surnamed Palacios) -- verified during this plan's execution
# by re-running the same search with a plain substring match first and
# discovering several such false positives before tightening to this rule.
#
# Single-token Understat mononyms (e.g. "Fred", "Jonny", "Jota", "Bojan") were
# deliberately EXCLUDED even where the same whole-token search found exactly
# one id_map candidate: a short, common first name being literally recorded
# as its own player's `first_name` field in id_map (e.g. a lesser-known player
# whose actual first name IS "Fred") does not make that player the SAME
# real person as a globally-famous player commonly known by that mononym
# (e.g. Manchester United's "Fred" -- Frederico Rodrigues de Paula Santos).
# `data/id_crosswalk.py::resolve_by_name` has no season/team context to
# disambiguate a bare mononym safely, so those names are left unresolved
# (T-09-08-05's spoofing risk) rather than guessed -- see 09-08-SUMMARY.md.
_NAME_FIXUPS: dict[str, str] = {
    # Single-mononym entries -- ONLY added where independently verified (not
    # just "unique in id_map") to have no competing same-era EPL player known
    # by the identical mononym. "Fred" and "Jonny" were BOTH found "unique" by
    # the same whole-token search that produced the multi-token entries below,
    # yet BOTH are wrong/ambiguous on inspection: id_map records Man Utd's
    # real "Fred" under first_name="Frederico" (so the search's one "Fred"
    # hit is a different, obscure player whose literal first_name happens to
    # be "Fred"), and Wolves' "Jonny" (Jonathan Castro Otto) is a second real
    # person also known by the exact mononym "Jonny" that Jonny Evans is.
    # Left unresolved rather than guessed -- see the module docstring above.
    "Jota": "Diogo Jota",
    "Bojan": "Bojan Krkic",
    "Kepa": "Kepa Arrizabalaga",
    "Sokratis": "Sokratis Papastathopoulos",
    "Diego Costa": "Diego Da Silva Costa",
    "Yaya Touré": "Gnegneri Yaya Touré",
    "Oriol Romeu": "Oriol Romeu Vidal",
    "David Luiz": "David Luiz Moreira Marinho",
    "Lucas Leiva": "Leiva Lucas",
    "Lee Chung-yong": "Chung-yong Lee",
    "Ki Sung-yueng": "Sung-yueng Ki",
    "Aleix García": "Aleix García Serrano",
    "Joel Pereira": "Joel Dinis Castro Pereira",
    "João Mário": "João Mário Naval Costa Eduardo",
    "Ahmed Hegazy": "Ahmed El-Sayed Hegazy",
    "Jesús Gámez": "Jesús Gámez Duarte",
    "Lucas Moura": "Lucas Rodrigues Moura da Silva",
    "Felipe Anderson": "Felipe Anderson Pereira Gomes",
    "Rúben Neves": "Rúben Diogo da Silva Neves",
    "Junior Hoilett": "David Junior Hoilett",
    "Ricardo Pereira": "Ricardo Domingos Barbosa Pereira",
    "André Gomes": "André Filipe Tavares Gomes",
    "João Moutinho": "João Filipe Iria Santos Moutinho",
    "Jazz Richards": "Ashley Darel Jazz Richards",
    "Rui Patrício": "Rui Pedro dos Santos Patrício",
    "Rúben Vinagre": "Rúben Gonçalo Silva Nascimento Vinagre",
    "Xande Silva": "Xande Nascimento da Costa Silva",
    "Gabriel Martinelli": "Gabriel Teodoro Martinelli Silva",
    "Roberto Jiménez": "Roberto Jimenez Gago",
    "Jesús Vallejo": "Jesús Vallejo Lázaro",
    "Bruno Jordao": "Bruno André Cavaco Jordao",
    "Gedson Fernandes": "Gedson Carvalho Fernandes",
    "Willian José": "Willian José Da Silva",
    "Pablo Hernández": "Pablo Hernández Domínguez",
    "Cristiano Ronaldo": "Cristiano Ronaldo dos Santos Aveiro",
    "Juan Camilo Hernández": "Juan Camilo Hernández Suárez",
    "Júnior Firpo": "Héctor Junior Firpo Adames",
    "Oghenekaro Etebo": "Oghenekaro Peter Etebo",
    "João Félix": "João Félix Sequeira",
    "Marc Roca": "Marc Roca Junqué",
    "Gonçalo Guedes": "Gonçalo Manuel Ganchinho Guedes",
    "Renan Lodi": "Renan Augusto Lodi dos Santos",
    "Pape Sarr": "Pape Matar Sarr",
    "Juan Larios": "Juan Larios López",
    "Mateo Joseph": "Mateo Joseph Fernández",
    "Gustavo Scarpa": "Gustavo Henrique Furtado Scarpa",
    "Rodrigo Muniz": "Rodrigo Muniz Carvalho",
    "Anssumane Fati": "Anssumane Fati Vieira",
    "Mads Andersen": "Mads Juel Andersen",
    "Igor Julio": "Igor Julio dos Santos de Paulo",
    "Andrey Santos": "Andrey Nascimento dos Santos",
    "Deivid Washington": "Deivid Washington de Souza Eugênio",
    "Brandon Aguilera": "Brandon Aguilera Zamora",
    "Matheus França": "Matheus França de Oliveira",
    "Rodrigo Ribeiro": "Rodrigo Duarte Ribeiro",
    "Rodrigo Gomes": "Rodrigo Martins Gomes",
    "Yukinari Sugawara": "Sugawara Yukinari",
    "Jorge Cuenca": "Jorge Cuenca Barreno",
    "Chadi Riad": "Chadi Riad Dnanou",
    "Renato Veiga": "Renato Palma Veiga",
    "Marc Guiu": "Marc Guiu Paz",
    "Julián Araujo": "Julián Araujo Zúñiga",
    "Luis Guilherme": "Luis Guilherme Lira dos Santos",
    "Carlos Forbs": "Carlos Roberto Forbs Borges",
    "Pedro Lima": "Pedro Cardoso de Lima",
    "Vitor Reis": "Vitor de Oliveira Nunes dos Reis",
    "Gustavo Nunes": "Gustavo Nunes Fernandes Gomes",
    "Igor Jesus": "Igor Jesus Maciel da Cruz",
    "Martín Zubimendi": "Martín Zubimendi Ibáñez",
    "Eliezer Mayenda": "Eliezer Mayenda Dossou",
    "Ao Tanaka": "Tanaka Ao",
    "Florentino Luís": "Florentino Ibrain Morris Luís",
    "Lucas Pires": "Lucas Pires Silva",
    "Dário Essugo": "Dário Luís Essugo",
    "John Victor": "John Victor Maciel Furtado",
    "Alysson Edward": "Alysson Edward Franco da Rocha dos Santos",
    "Sindre Egeli": "Sindre Walle Egeli",
    "António Silva": "António João Pereira de Albuquerque Tavares da Silva",
}

_RENAME = {
    "FPL code": "player_code",
    "FPL ID": "kiwi_fpl_id",
    "FPL name": "fpl_name",
    "fbref": "fbref_name",
    "fbref ID": "fbref_id",
    "Name": "kiwi_name",
    "FPL pos": "position",
    "Team": "team",
    "DOB": "dob",
}
_COLS = ["player_code", "kiwi_fpl_id", "fpl_name", "fbref_name", "fbref_id",
         "kiwi_name", "position", "team", "dob", "name_key", "fbref_key"]


def _norm(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.normalize("NFKD").str.encode("ascii", "ignore")
            .str.decode("ascii").str.lower().str.strip())


def build() -> pd.DataFrame:
    """Build the player_code-keyed alias table from the committed ID dictionary.

    `drop_duplicates(subset="player_code")` plus the trailing uniqueness
    assertion make a many-to-many join structurally impossible downstream --
    the same discipline that stopped a repeat of the fbref join corruption
    (IMPROVEMENTS.md Phase E).
    """
    raw = pd.read_csv(_SRC, encoding="latin-1")
    df = raw.rename(columns=_RENAME)
    df["player_code"] = pd.to_numeric(df["player_code"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["player_code"])
    df["name_key"] = _norm(df["fpl_name"])
    df["fbref_key"] = _norm(df["fbref_name"])
    df = df.drop_duplicates(subset="player_code", keep="first").reset_index(drop=True)
    if not df["player_code"].is_unique:
        raise AssertionError(
            "id_crosswalk.build(): duplicate player_code would multiply rows "
            "in every downstream merge")
    return df[_COLS]


def load_crosswalk() -> pd.DataFrame | None:
    """Return the cached crosswalk, or None when absent -- matching
    `data/fbref.py::load_fbref`'s no-op-if-absent contract so downstream
    joins can stay inside a guarded try/except."""
    return pd.read_parquet(_OUT) if _OUT.exists() else None


@functools.lru_cache(maxsize=1)
def _fpl_name_index() -> pd.Series:
    """Normalised "first second" full name -> player_code, over EVERY
    historical player `data/id_map.py` has ever seen (2,737+ distinct codes),
    not just theFPLkiwi's ~454-row CURRENT-squad snapshot `build()` is keyed
    on. This is the tier that makes `resolve_by_name` usable for a source
    whose player universe spans many seasons (e.g. Understat, back to
    2016-17) rather than only this week's 20 squads -- discovered necessary
    when plan 09-08's first real Understat join measured only ~20% coverage
    through the theFPLkiwi-only tiers alone (most historically-departed
    players, e.g. Harry Kane, Sergio Agüero, simply never appear in
    theFPLkiwi's current-squad CSV at all -- no fixup spelling can invent a
    row that source never had). A given full name maps to exactly one
    player_code (first write wins on a duplicate key, which is rare and
    inherent to any name-only join, not something this cache can resolve
    better than that).
    """
    from data import id_map

    idm = id_map.load_id_map().dropna(subset=["first_name", "second_name", "player_code"])
    full = idm["first_name"].fillna("") + " " + idm["second_name"].fillna("")
    key = _norm(full)
    return (pd.Series(idm["player_code"].to_numpy(), index=key)
            .groupby(level=0).first())


def resolve_by_name(names: pd.Series) -> pd.Series:
    """Map arbitrary source names to `player_code`.

    Tries, in order: `_norm` against `name_key` (theFPLkiwi's own FPL name),
    then `_norm` against `fbref_key`, then `_norm` against the full
    first+second name of EVERY player `data/id_map.py` has ever recorded
    (the tier that gives historical coverage theFPLkiwi's current-squad-only
    snapshot cannot), then `_NAME_FIXUPS` (applied to the raw name before
    normalising, for a source's persistent misses across ALL three tiers).
    Returns `pd.NA` for names that resolve nowhere.
    """
    fixed = names.replace(_NAME_FIXUPS)
    keys = _norm(fixed)
    out = pd.Series(pd.NA, index=names.index, dtype="Int64")

    cw = load_crosswalk()
    if cw is not None:
        by_name = (cw.dropna(subset=["name_key"]).drop_duplicates("name_key")
                   .set_index("name_key")["player_code"])
        by_fbref = (cw.dropna(subset=["fbref_key"]).drop_duplicates("fbref_key")
                    .set_index("fbref_key")["player_code"])
        out = keys.map(by_name)
        missing = out.isna()
        if missing.any():
            out.loc[missing] = keys[missing].map(by_fbref)

    missing = out.isna()
    if missing.any():
        out.loc[missing] = keys[missing].map(_fpl_name_index())
    return out.astype("Int64")


def main() -> int:
    from data.id_map import load_id_map

    cw = build()
    cw.to_parquet(_OUT, index=False)

    idm_codes = set(load_id_map()["player_code"].dropna().unique())
    cw_codes = set(cw["player_code"].dropna().unique())
    covered = len(idm_codes & cw_codes)
    pct = covered / len(idm_codes) if idm_codes else 0.0
    print(f"[crosswalk] {len(cw):,} rows; covers {pct:.1%} of id_map.parquet's "
          f"{len(idm_codes):,} distinct player_code values")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
