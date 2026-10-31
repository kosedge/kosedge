export class PaidFetchDenied extends Error {
  readonly code = "PAID_FETCH_DENIED" as const;
  readonly caller: string;
  readonly reason: string;

  constructor(caller: string, reason = "paid_fetch_denied") {
    super(`PAID_FETCH_DENIED caller=${caller}`);
    this.name = "PaidFetchDenied";
    this.caller = caller;
    this.reason = reason;
  }
}

export function isPaidFetchDenied(err: unknown): err is PaidFetchDenied {
  return (
    err instanceof PaidFetchDenied ||
    (Boolean(err) &&
      typeof err === "object" &&
      (err as { code?: string }).code === "PAID_FETCH_DENIED")
  );
}
