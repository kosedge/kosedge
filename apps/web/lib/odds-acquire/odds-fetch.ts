/**
 * Server fetch wrappers. Mapping/parsing stays in odds-api.ts;
 * this module is the only caller that may invoke oddsAcquire for those pulls.
 */

export {
  fetchEdgeBoard,
  fetchNcaabEdgeBoard,
  fetchOddsComparison,
} from "@/lib/odds-api";
