export interface RawTurn {
  turn_id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  tool_calls?: any[];
  metadata?: Record<string, any>;
  timestamp: string;
  is_consolidated: boolean;
}

export interface Fact {
  id: string;
  entity: string;
  attribute: string;
  value: any;
  confidence: number;
  timestamp: string;
  source_turn_ids: string[];
  superseded_by?: string | null;
  is_active: boolean;
}

export interface OperationalRule {
  id: string;
  category: "user_preference" | "coding_standard" | "architecture_heuristic" | "operational_directive" | "domain_constraint";
  rule: string;
  rationale: string;
  priority: number;
  is_active: boolean;
  updated_at: string;
}

export interface ContradictionResolution {
  prior_fact_id?: string;
  entity: string;
  attribute: string;
  prior_value: any;
  new_value: any;
  resolution_reasoning: string;
}

export interface DreamResult {
  run_id: string;
  added_facts: Fact[];
  updated_rules: OperationalRule[];
  contradiction_resolutions: ContradictionResolution[];
  pruned_noise_count: number;
  pruned_noise_reasons: string[];
  reasoning_summary: string;
  consolidated_turn_ids: string[];
  timestamp: string;
  estimated_token_savings: number;
}

export interface SystemState {
  turns: RawTurn[];
  unconsolidatedCount: number;
  facts: Fact[];
  rules: OperationalRule[];
  audits: DreamResult[];
  totalPrunedTurns: number;
  lastDreamAt: string | null;
  idleSeconds: number;
  isDreaming: boolean;
  hasApiKey: boolean;
}

export interface SourceFile {
  id: string;
  path: string;
  name: string;
  lang: string;
  content: string;
}
