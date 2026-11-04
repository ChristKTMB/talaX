// The JSON answer of POST /api/analyze (schema 2), with the API's own field
// names, so that docs/api-examples/ can be used as they are. See docs/api.md.

export type State = 'consistent' | 'to_check' | 'suspicious' | 'unverifiable';
export const STATES: readonly State[] = ['consistent', 'to_check', 'suspicious', 'unverifiable'];

export type Verdict = 'original' | 'reprocessed' | 'undetermined';
export type Sky = 'day' | 'twilight' | 'night';

export type Evidence = Readonly<Record<string, unknown>>;

export interface Integrity {
  readonly verdict: Verdict;
  readonly label: string;
  readonly pipeline: string | null;
  readonly message: string;
  readonly explanation: string;
  readonly evidence: Evidence;
}

export interface CheckResult {
  readonly signal: string;
  readonly name: string;
  readonly state: State;
  readonly label: string;
  readonly message: string;
  readonly explanation: string;
  readonly evidence: Evidence;
  readonly confidence: number | null;
}

export interface FileSummary {
  readonly name: null;
  readonly sha256: string;
  readonly size: number;
  readonly declared_format: string | null;
  readonly real_format: string | null;
}

export interface AnalysisResult {
  readonly schema: 2;
  readonly lang: string;
  readonly tools: Readonly<Record<string, string>>;
  readonly created_at: string;
  readonly file: FileSummary;
  readonly integrity: Integrity;
  readonly results: readonly CheckResult[];
  readonly disclaimer: string;
  /** The preview embedded in the file, as a data: URI, or null. */
  readonly thumbnail: string | null;
}

/** Codes of the API and of nginx, plus `network` when no answer came back. */
export type ErrorCode =
  | 'file_too_large'
  | 'busy'
  | 'rate_limited'
  | 'analysis_failed'
  | 'invalid_request'
  | 'internal'
  | 'not_found'
  | 'network';

export interface ApiError {
  readonly code: ErrorCode | string;
  /** Text to show; null when the server gave none (network failure, odd answer). */
  readonly message: string | null;
}
