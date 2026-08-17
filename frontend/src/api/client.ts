/**
 * Centralized API client for the backend.
 * All fetch calls go through this module.
 */

import type {
  Scenario,
  ScenarioCreate,
  Scaffold,
  ScaffoldCreate,
  CounterfactualRequest,
  CounterfactualResponse,
  Experiment,
  ExperimentCreate,
  PaginatedResponses,
  ExperimentResponseItem,
  CodingCreate,
  CodingEntry,
  BlindResponsesResult,
  AnalysisSummary,
  OllamaModel,
  WordPair,
  RunnerProgress,
} from "../types";

const BASE_URL = "http://localhost:8000/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API Error ${res.status}: ${errorBody}`);
  }

  // Handle empty responses (204, etc.)
  const text = await res.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

// ── Scenarios ────────────────────────────────────────────────────────────────

export const scenariosApi = {
  list: () => request<Scenario[]>("/scenarios"),
  get: (id: string) => request<Scenario>(`/scenarios/${id}`),
  create: (data: ScenarioCreate) =>
    request<Scenario>("/scenarios", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: ScenarioCreate) =>
    request<Scenario>(`/scenarios/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<{ deleted: boolean }>(`/scenarios/${id}`, { method: "DELETE" }),
  categories: () => request<string[]>("/scenarios/categories"),
};

// ── Scaffolds ────────────────────────────────────────────────────────────────

export const scaffoldsApi = {
  list: () => request<Scaffold[]>("/scaffolds"),
  get: (id: string) => request<Scaffold>(`/scaffolds/${id}`),
  create: (data: ScaffoldCreate) =>
    request<Scaffold>("/scaffolds", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: ScaffoldCreate) =>
    request<Scaffold>(`/scaffolds/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<{ deleted: boolean }>(`/scaffolds/${id}`, { method: "DELETE" }),
};

// ── Counterfactual ───────────────────────────────────────────────────────────

export const counterfactualApi = {
  generate: (data: CounterfactualRequest) =>
    request<CounterfactualResponse>("/counterfactual/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listWordPairs: () => request<WordPair[]>("/counterfactual/word-pairs"),
  addWordPair: (data: { male_term: string; female_term: string }) =>
    request<WordPair>("/counterfactual/word-pairs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteWordPair: (id: string) =>
    request<{ deleted: boolean }>(`/counterfactual/word-pairs/${id}`, {
      method: "DELETE",
    }),
};

// ── Experiments ──────────────────────────────────────────────────────────────

export const experimentsApi = {
  list: () => request<Experiment[]>("/experiments"),
  get: (id: string) => request<Experiment>(`/experiments/${id}`),
  create: (data: ExperimentCreate) =>
    request<Experiment>("/experiments", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<{ deleted: boolean }>(`/experiments/${id}`, { method: "DELETE" }),
};

// ── Runner ───────────────────────────────────────────────────────────────────

export const runnerApi = {
  start: (experimentId: string) =>
    request<{ message: string; experiment_id: string }>("/runner/start", {
      method: "POST",
      body: JSON.stringify({ experiment_id: experimentId }),
    }),
  status: (experimentId: string) =>
    request<RunnerProgress>(`/runner/status/${experimentId}`),
};

// ── Responses ────────────────────────────────────────────────────────────────

export const responsesApi = {
  list: (params?: {
    experiment_id?: string;
    condition?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.experiment_id) searchParams.set("experiment_id", params.experiment_id);
    if (params?.condition) searchParams.set("condition", params.condition);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return request<PaginatedResponses>(`/responses${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => request<ExperimentResponseItem>(`/responses/${id}`),
  delete: (id: string) =>
    request<{ deleted: boolean }>(`/responses/${id}`, { method: "DELETE" }),
  bulkDelete: (experimentId?: string) => {
    const qs = experimentId ? `?experiment_id=${experimentId}` : "";
    return request<{ deleted: number }>(`/responses${qs}`, { method: "DELETE" });
  },
};

// ── Coding ───────────────────────────────────────────────────────────────────

export const codingApi = {
  list: () => request<CodingEntry[]>("/coding"),
  blind: (params?: { experiment_id?: string; shuffle_seed?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.experiment_id) searchParams.set("experiment_id", params.experiment_id);
    if (params?.shuffle_seed !== undefined)
      searchParams.set("shuffle_seed", String(params.shuffle_seed));
    const qs = searchParams.toString();
    return request<BlindResponsesResult>(`/coding/blind${qs ? `?${qs}` : ""}`);
  },
  save: (data: CodingCreate) =>
    request<CodingEntry>("/coding", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ── Analysis ─────────────────────────────────────────────────────────────────

export const analysisApi = {
  summary: (experimentId?: string) => {
    const qs = experimentId ? `?experiment_id=${experimentId}` : "";
    return request<AnalysisSummary>(`/analysis/summary${qs}`);
  },
  byExperiment: (experimentId: string) =>
    request<AnalysisSummary>(`/analysis/by-experiment/${experimentId}`),
  allExperiments: () =>
    request<AnalysisSummary[]>("/analysis/all-experiments"),
};

// ── Ollama ───────────────────────────────────────────────────────────────────

export const ollamaApi = {
  models: () => request<OllamaModel[]>("/ollama/models"),
  health: () => request<{ healthy: boolean }>("/ollama/health"),
};

// ── Export ────────────────────────────────────────────────────────────────────

export const exportApi = {
  downloadUrl: () => `${BASE_URL}/export`,
};
