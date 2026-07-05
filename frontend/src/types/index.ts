// ── Data Types ────────────────────────────────────────────────────────────────

export const SCENARIO_CATEGORIES = [
  "Combat",
  "Dialogue",
  "Quest",
  "Exploration",
  "Trading",
  "Social Interaction",
  "Puzzle",
  "Tutorial",
  "General",
  "Other",
] as const;

export type ScenarioCategory = (typeof SCENARIO_CATEGORIES)[number];

export interface Scenario {
  id: string;
  title: string;
  description: string;
  scenario_text: string;
  category: ScenarioCategory;
  category_other?: string;
  created_at: string;
}

export interface ScenarioCreate {
  title: string;
  description: string;
  scenario_text: string;
  category: string;
  category_other?: string;
}

export interface Scaffold {
  id: string;
  name: string;
  prompt: string;
  version: string;
  notes: string;
  created_at: string;
}

export interface ScaffoldCreate {
  name: string;
  prompt: string;
  version: string;
  notes?: string;
}

export interface CounterfactualRequest {
  prompt: string;
  swap_type: "npc" | "player" | "third_person";
}

export interface CounterfactualResponse {
  male_prompt: string;
  female_prompt: string;
  swap_type: string;
  swaps_made: Array<{
    original: string;
    replaced_with: string;
    count: number;
  }>;
}

export interface Experiment {
  id: string;
  scenario_id: string;
  scaffold_id: string;
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  seed: number | null;
  num_replicates: number;
  swap_type: string;
  status: "configured" | "running" | "completed" | "failed";
  created_at: string;
}

export interface ExperimentCreate {
  scenario_id: string;
  scaffold_id: string;
  model: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  seed: number | null;
  num_replicates: number;
  swap_type: string;
}

export interface ExperimentResponseItem {
  id: string;
  experiment_id: string;
  scenario_id: string;
  scaffold_id: string;
  scaffold_version: string;
  model: string;
  temperature: number;
  seed: number | null;
  timestamp: string;
  condition: string;
  replicate_number: number;
  system_prompt: string;
  user_prompt: string;
  generated_response: string;
}

export interface PaginatedResponses {
  total: number;
  limit: number;
  offset: number;
  data: ExperimentResponseItem[];
}

export interface CodingEntry {
  id: string;
  response_id: string;
  truth: number;
  indeterminacy: number;
  falsity: number;
  reasoning_notes: string;
  coded_at: string;
}

export interface CodingCreate {
  response_id: string;
  truth: number;
  indeterminacy: number;
  falsity: number;
  reasoning_notes?: string;
}

export interface BlindResponseItem {
  id: string;
  experiment_id: string;
  scenario_id: string;
  model: string;
  replicate_number: number;
  generated_response: string;
  user_prompt: string;
  coding: CodingEntry | null;
}

export interface BlindResponsesResult {
  total: number;
  coded: number;
  remaining: number;
  data: BlindResponseItem[];
}

export interface ConditionStats {
  avg_truth: number;
  avg_indeterminacy: number;
  avg_falsity: number;
  count: number;
}

export interface AnalysisSummary {
  experiment_id: string | null;
  total_responses: number;
  total_coded: number;
  male: ConditionStats;
  female: ConditionStats;
  bias_score: number;
}

export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
  digest: string;
}

export interface WordPair {
  id?: string;
  male_term: string;
  female_term: string;
  builtin: boolean;
}

export interface RunnerProgress {
  completed: number;
  total: number;
  status: string;
}
