// ── Data Types ────────────────────────────────────────────────────────────────


// ── Scenario ─────────────────────────────────────────────────────────────────

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

export type ScenarioCategory =
  (typeof SCENARIO_CATEGORIES)[number];


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


// ── Scaffold ─────────────────────────────────────────────────────────────────

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


// ── Counterfactual ───────────────────────────────────────────────────────────

export interface CounterfactualRequest {
  prompt: string;
}


export interface CounterfactualResponse {
  male_prompt: string;
  female_prompt: string;

  swaps_made: Array<{
    original: string;
    replaced_with: string;
    count: number;
  }>;
}


// ── Experiment ───────────────────────────────────────────────────────────────

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

  swap_type?: string;

  status:
    | "configured"
    | "running"
    | "completed"
    | "failed";

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

  swap_type?: string;
}


// ── Experiment Response ──────────────────────────────────────────────────────

export interface ExperimentResponseItem {
  id: string;
  pair_id?: string;

  experiment_id: string;

  scenario_id: string;
  scaffold_id: string;

  scaffold_version: string;

  model: string;

  temperature: number;

  seed: number | null;

  timestamp: string;

  /**
   * Internal experimental condition ("original" | "swapped").
   */
  condition: string;

  replicate_number: number;

  scaffold_prompt?: string;
  scenario_prompt?: string;
  system_prompt?: string;
  user_prompt?: string;

  generated_response: string;
}


export interface ResponsePair {
  pair_id: string;
  original: ExperimentResponseItem | null;
  swapped: ExperimentResponseItem | null;
  replicate_number: number;
  scenario_id: string;
  scaffold_id: string;
  model: string;
  timestamp: string;
}


export interface PaginatedResponses {
  total: number;

  limit: number;

  offset: number;

  data: ExperimentResponseItem[];
}


export interface PaginatedPairs {
  total: number;
  limit: number;
  offset: number;
  data: ResponsePair[];
}


// ── Coding ───────────────────────────────────────────────────────────────────

/**
 * A coding entry created by an individual coder.
 *
 * Multiple coders can independently code the
 * same response.
 */
export interface CodingEntry {
  id: string;

  response_id: string;

  coder_id: string;

  /**
   * Truth (T)
   *
   * Degree to which the response expresses
   * stereotype or gender-based disadvantage.
   */
  truth: number;

  /**
   * Indeterminacy (I)
   *
   * Degree of ambiguity, contested interpretation,
   * or context dependence.
   */
  indeterminacy: number;

  /**
   * Falsity (F)
   *
   * Degree to which the response is neutral
   * or counter-stereotypical.
   */
  falsity: number;

  reasoning_notes: string;

  coded_at: string;
}


/**
 * Payload used when saving a coding.
 */
export interface CodingCreate {
  response_id: string;

  coder_id: string;

  truth: number;

  indeterminacy: number;

  falsity: number;

  reasoning_notes?: string;
}


// ── Blind Coding ─────────────────────────────────────────────────────────────

export interface BlindVersion {
  response_id: string;
  generated_response: string;
  coding: CodingEntry | null;
}

export interface BlindPair {
  pair_id: string;
  experiment_id: string;
  scenario_id: string;
  model: string;
  replicate_number: number;
  scenario_prompt: string;
  scaffold_prompt: string;
  version_a: BlindVersion;
  version_b: BlindVersion | null;
  is_coded: boolean;
}

export interface BlindPairsResult {
  total: number;
  coded: number;
  remaining: number;
  coder_id?: string | null;
  data: BlindPair[];
}

/**
 * Response returned to a coder.
 *
 * IMPORTANT:
 * Gender condition labels and system prompts
 * are intentionally excluded.
 */
export interface BlindResponseItem {
  id: string;

  experiment_id: string;

  scenario_id: string;

  model: string;

  replicate_number: number;

  generated_response: string;

  user_prompt: string;

  /**
   * Only the CURRENT coder's coding record
   * is returned.
   *
   * Other coders' ratings remain hidden.
   */
  codings: CodingEntry | null;
}


export interface BlindResponsesResult {
  total: number;

  coded: number;

  remaining: number;

  /**
   * Identifies which coder's progress
   * is represented.
   */
  coder_id?: string | null;

  data: BlindResponseItem[] | BlindPair[];
}


// ── Analysis ─────────────────────────────────────────────────────────────────

export interface ConditionStats {
  avg_T: number;

  avg_I: number;

  avg_F: number;

  count: number;
}


/**
 * Standard SVNS gender-bias analysis result.
 *
 * When multiple coders have coded a response,
 * the backend averages their ratings for that
 * response before calculating condition metrics.
 */
export interface AnalysisSummary {
  experiment_id: string | null;

  total_responses: number;

  /**
   * Number of unique responses with
   * at least one coding.
   */
  total_coded: number;

  /**
   * Total independent coding records.
   *
   * Example:
   *
   * 10 responses
   * × 2 coders
   * = 20 coding records
   */
  total_coding_records: number;

  /**
   * Percentage of unique responses
   * that have at least one coding.
   */
  coding_coverage: number;

  experiment_count: number;

  male: ConditionStats;

  female: ConditionStats;

  /**
   * |Average T (male) - Average T (female)|
   */
  bias_score: number;

  dimensions?: {
    T: string;
    I: string;
    F: string;
  };

  bias_score_definition?: string;
}


// ── Ollama ───────────────────────────────────────────────────────────────────

export interface OllamaModel {
  name: string;

  size: number;

  modified_at: string;

  digest: string;
}


// ── Counterfactual Word Pairs ────────────────────────────────────────────────

export interface WordPair {
  id?: string;

  male_term: string;

  female_term: string;

  builtin: boolean;
}


// ── Runner Progress ──────────────────────────────────────────────────────────

export interface RunnerProgress {
  completed: number;

  total: number;

  status: string;
}


// ── Inter-Rater Agreement ────────────────────────────────────────────────────

/**
 * Agreement statistics for one SVNS dimension.
 *
 * The backend currently calculates:
 *
 * - ICC(2,1)
 * - Interpretation of ICC
 * - Mean Absolute Difference
 * - Number of shared responses
 */
export interface ReliabilityDimension {
  icc: number | null;

  interpretation: string;

  mean_absolute_difference: number | null;

  /**
   * Number of responses coded by BOTH coders.
   */
  n: number;

  label: string;
}


/**
 * Complete inter-rater reliability result.
 *
 * Returned from:
 *
 * GET /api/analysis/inter-rater
 */
export interface InterRaterReliability {
  experiment_id: string | null;

  coder_1: string;

  coder_2: string;

  /**
   * Number of responses independently coded
   * by both selected coders.
   */
  total_shared_responses: number;

  dimensions: {
    /**
     * Truth:
     * Stereotype / Gender-based Disadvantage
     */
    T: ReliabilityDimension;

    /**
     * Indeterminacy:
     * Ambiguity / Context-dependent Interpretation
     */
    I: ReliabilityDimension;

    /**
     * Falsity:
     * Neutral / Counter-stereotypical Content
     */
    F: ReliabilityDimension;
  };

  overall: {
    icc: number | null;

    interpretation: string;
  };
}


// ── Backwards-Compatible Type Aliases ────────────────────────────────────────

/**
 * Alias retained so existing components using
 * InterRaterAgreement do not break.
 */
export type InterRaterAgreement =
  InterRaterReliability;


/**
 * Alias retained for compatibility with
 * any existing analysis components.
 */
export type InterRaterResult =
  InterRaterReliability;