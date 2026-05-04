export interface PerModelResult {
  model_label: string;
  mentioned: boolean;
  position: number | null;
  sentiment: string;
  competitors: string[];
  error: string | null;
}

export interface Verification {
  brand: string;
  found: boolean;
  top_hit_url: string | null;
  top_hit_title: string | null;
}

export interface RawResponse {
  model_label: string;
  latency_ms: number;
  text: string;
  error: string | null;
}

export interface DiagnosticResult {
  query: string;
  target: string;
  grade: string;
  overall: number;
  mention_rate: number;
  avg_position: number | null;
  sentiment_score: number;
  citation_score: number;
  per_model: PerModelResult[];
  verifications: Verification[];
  raw_responses: RawResponse[];
  deep_analysis?: string;
}

export type SseEvent =
  | { type: "status"; message: string }
  | { type: "result"; data: DiagnosticResult }
  | { type: "error"; message: string };
