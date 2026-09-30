/**
 * MLB/NHL market contract — research-only schema (v1 draft).
 *
 * Not wired into production UI. Does not unlock PLAY/LEAN thresholds.
 * Locked settlement semantics are documented; calculations here are
 * fail-closed helpers for contract tests and future migration.
 */

export const MARKET_CONTRACT_SCHEMA_VERSION = "mlb-nhl-market-contract-v1" as const;

/** Versioned contract id pattern: `{sport}.{family}.{period}.{settlement}.v{n}` */
export type MarketContractId =
  | "mlb.ml.fg.incl_extra_innings.v1"
  | "mlb.ml.f5.regulation_only.v1"
  | "mlb.run_line.fg.incl_extra_innings.v1"
  | "mlb.total.fg.incl_extra_innings.v1"
  | "mlb.total.f5.regulation_only.v1"
  | "nhl.ml.fg.incl_ot_so.v1"
  | "nhl.ml.regulation.three_way.v1"
  | "nhl.puck_line.fg.incl_ot_so.v1"
  | "nhl.total.fg.incl_ot_so.v1";

export type SportCode = "mlb" | "nhl";

export type MarketFamily =
  | "moneyline"
  | "run_line"
  | "puck_line"
  | "total";

export type PeriodScope = "full_game" | "first_five" | "regulation";

export type SettlementScope =
  | "includes_extra_innings"
  | "first_five_innings_only"
  | "includes_overtime_shootout"
  | "regulation_only_three_way";

export type SelectedSide =
  | "home"
  | "away"
  | "over"
  | "under"
  | "draw"; // regulation three-way only

/** Orientation of line numbers relative to home team. */
export type HomeAwayOrientation =
  | "home_signed"
  | "away_signed"
  | "side_explicit"
  | "not_applicable";

export type PriceFormat = "american" | "decimal" | "implied_prob" | "fair_line_points";

export type PushVoidBehavior =
  | "push_stake_returned"
  | "void_cancelled"
  | "three_way_no_push_on_draw" // regulation ML: draw is a priced outcome
  | "run_line_no_push_at_1_5"
  | "puck_line_no_push_at_1_5"
  | "total_push_on_exact";

export type MarketContractDefinition = {
  market_contract_id: MarketContractId;
  sport: SportCode;
  family: MarketFamily;
  period_scope: PeriodScope;
  settlement_scope: SettlementScope;
  customer_label: string;
  internal_legacy_keys: readonly string[];
  orientation: HomeAwayOrientation;
  price_format_primary: PriceFormat;
  push_void: PushVoidBehavior;
  board_initial: boolean;
  desk_research_only: boolean;
  notes: string;
};

export const MARKET_CONTRACT_CATALOG: readonly MarketContractDefinition[] = [
  {
    market_contract_id: "mlb.ml.fg.incl_extra_innings.v1",
    sport: "mlb",
    family: "moneyline",
    period_scope: "full_game",
    settlement_scope: "includes_extra_innings",
    customer_label: "Game Moneyline (includes extras)",
    internal_legacy_keys: ["ml", "h2h", "fair_fg_home_ml", "Moneyline"],
    orientation: "side_explicit",
    price_format_primary: "american",
    push_void: "void_cancelled",
    board_initial: true,
    desk_research_only: false,
    notes: "Book settlement includes extra innings. Not First Five.",
  },
  {
    market_contract_id: "mlb.ml.f5.regulation_only.v1",
    sport: "mlb",
    family: "moneyline",
    period_scope: "first_five",
    settlement_scope: "first_five_innings_only",
    customer_label: "First Five Moneyline",
    internal_legacy_keys: ["f5_ml", "fair_f5_home_ml"],
    orientation: "side_explicit",
    price_format_primary: "american",
    push_void: "push_stake_returned",
    board_initial: false,
    desk_research_only: true,
    notes: "Separate market contract from full-game ML.",
  },
  {
    market_contract_id: "mlb.run_line.fg.incl_extra_innings.v1",
    sport: "mlb",
    family: "run_line",
    period_scope: "full_game",
    settlement_scope: "includes_extra_innings",
    customer_label: "Run Line",
    internal_legacy_keys: ["run_line", "fg_home_cover_prob_run_line", "Spread"],
    orientation: "home_signed",
    price_format_primary: "fair_line_points",
    push_void: "run_line_no_push_at_1_5",
    board_initial: false,
    desk_research_only: true,
    notes: "Desk/research-only until product board contract exists.",
  },
  {
    market_contract_id: "mlb.total.fg.incl_extra_innings.v1",
    sport: "mlb",
    family: "total",
    period_scope: "full_game",
    settlement_scope: "includes_extra_innings",
    customer_label: "Game Total",
    internal_legacy_keys: ["total", "fair_fg_total", "totals"],
    orientation: "not_applicable",
    price_format_primary: "fair_line_points",
    push_void: "total_push_on_exact",
    board_initial: true,
    desk_research_only: false,
    notes: "MLB initial board = Moneyline + Total.",
  },
  {
    market_contract_id: "mlb.total.f5.regulation_only.v1",
    sport: "mlb",
    family: "total",
    period_scope: "first_five",
    settlement_scope: "first_five_innings_only",
    customer_label: "First Five Total",
    internal_legacy_keys: ["f5_total", "fair_f5_total"],
    orientation: "not_applicable",
    price_format_primary: "fair_line_points",
    push_void: "total_push_on_exact",
    board_initial: false,
    desk_research_only: true,
    notes: "Separate from full-game total.",
  },
  {
    market_contract_id: "nhl.ml.fg.incl_ot_so.v1",
    sport: "nhl",
    family: "moneyline",
    period_scope: "full_game",
    settlement_scope: "includes_overtime_shootout",
    customer_label: "Game Moneyline — Includes OT/Shootout",
    internal_legacy_keys: ["Moneyline", "h2h", "fair_home_ml"],
    orientation: "side_explicit",
    price_format_primary: "american",
    push_void: "void_cancelled",
    board_initial: false,
    desk_research_only: true,
    notes: "Must never silently equal Regulation Moneyline.",
  },
  {
    market_contract_id: "nhl.ml.regulation.three_way.v1",
    sport: "nhl",
    family: "moneyline",
    period_scope: "regulation",
    settlement_scope: "regulation_only_three_way",
    customer_label: "Regulation Moneyline (3-way)",
    internal_legacy_keys: ["regulation_ml", "h2h_3_way"],
    orientation: "side_explicit",
    price_format_primary: "american",
    push_void: "three_way_no_push_on_draw",
    board_initial: false,
    desk_research_only: true,
    notes: "Separate three-way market; draw is a priced outcome.",
  },
  {
    market_contract_id: "nhl.puck_line.fg.incl_ot_so.v1",
    sport: "nhl",
    family: "puck_line",
    period_scope: "full_game",
    settlement_scope: "includes_overtime_shootout",
    customer_label: "Puck Line",
    internal_legacy_keys: ["Spread", "spread", "fair_spread_home", "kei_puck_home"],
    orientation: "home_signed",
    price_format_primary: "fair_line_points",
    push_void: "puck_line_no_push_at_1_5",
    board_initial: true,
    desk_research_only: false,
    notes: "Customer label is Puck Line; internal key often still Spread.",
  },
  {
    market_contract_id: "nhl.total.fg.incl_ot_so.v1",
    sport: "nhl",
    family: "total",
    period_scope: "full_game",
    settlement_scope: "includes_overtime_shootout",
    customer_label: "Game Total",
    internal_legacy_keys: ["Total", "totals", "fair_total"],
    orientation: "not_applicable",
    price_format_primary: "fair_line_points",
    push_void: "total_push_on_exact",
    board_initial: true,
    desk_research_only: false,
    notes: "Full-game total follows governed book settlement (OT goals count).",
  },
] as const;

export function getMarketContract(
  id: MarketContractId,
): MarketContractDefinition | undefined {
  return MARKET_CONTRACT_CATALOG.find((c) => c.market_contract_id === id);
}

export function isMarketContractId(value: string): value is MarketContractId {
  return MARKET_CONTRACT_CATALOG.some((c) => c.market_contract_id === value);
}
