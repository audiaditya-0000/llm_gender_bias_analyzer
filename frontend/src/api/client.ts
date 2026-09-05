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
  PaginatedPairs,
  ExperimentResponseItem,
  CodingCreate,
  CodingEntry,
  BlindPairsResult,
  AnalysisSummary,
  OllamaModel,
  WordPair,
  RunnerProgress,
  InterRaterReliability,
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

    throw new Error(
      `API Error ${res.status}: ${errorBody}`
    );
  }

  // Handle empty responses
  const text = await res.text();

  if (!text) {
    return {} as T;
  }

  return JSON.parse(text) as T;
}


// ── Scenarios ────────────────────────────────────────────────────────────────

export const scenariosApi = {
  list: () =>
    request<Scenario[]>("/scenarios"),

  get: (id: string) =>
    request<Scenario>(`/scenarios/${id}`),

  create: (data: ScenarioCreate) =>
    request<Scenario>("/scenarios", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    id: string,
    data: ScenarioCreate
  ) =>
    request<Scenario>(`/scenarios/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<{ deleted: boolean }>(
      `/scenarios/${id}`,
      {
        method: "DELETE",
      }
    ),

  categories: () =>
    request<string[]>("/scenarios/categories"),
};


// ── Scaffolds ────────────────────────────────────────────────────────────────

export const scaffoldsApi = {
  list: () =>
    request<Scaffold[]>("/scaffolds"),

  get: (id: string) =>
    request<Scaffold>(`/scaffolds/${id}`),

  create: (data: ScaffoldCreate) =>
    request<Scaffold>("/scaffolds", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    id: string,
    data: ScaffoldCreate
  ) =>
    request<Scaffold>(`/scaffolds/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<{ deleted: boolean }>(
      `/scaffolds/${id}`,
      {
        method: "DELETE",
      }
    ),
};


// ── Counterfactual ───────────────────────────────────────────────────────────

export const counterfactualApi = {
  generate: (
    data: CounterfactualRequest
  ) =>
    request<CounterfactualResponse>(
      "/counterfactual/generate",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  listWordPairs: () =>
    request<WordPair[]>(
      "/counterfactual/word-pairs"
    ),

  addWordPair: (data: {
    male_term: string;
    female_term: string;
  }) =>
    request<WordPair>(
      "/counterfactual/word-pairs",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  deleteWordPair: (id: string) =>
    request<{ deleted: boolean }>(
      `/counterfactual/word-pairs/${id}`,
      {
        method: "DELETE",
      }
    ),
};


// ── Experiments ──────────────────────────────────────────────────────────────

export const experimentsApi = {
  list: () =>
    request<Experiment[]>("/experiments"),

  get: (id: string) =>
    request<Experiment>(
      `/experiments/${id}`
    ),

  create: (data: ExperimentCreate) =>
    request<Experiment>(
      "/experiments",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),

  delete: (id: string) =>
    request<{ deleted: boolean }>(
      `/experiments/${id}`,
      {
        method: "DELETE",
      }
    ),
};


// ── Runner ───────────────────────────────────────────────────────────────────

export const runnerApi = {
  start: (experimentId: string) =>
    request<{
      message: string;
      experiment_id: string;
    }>("/runner/start", {
      method: "POST",
      body: JSON.stringify({
        experiment_id: experimentId,
      }),
    }),

  status: (experimentId: string) =>
    request<RunnerProgress>(
      `/runner/status/${experimentId}`
    ),
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
    const searchParams =
      new URLSearchParams();

    if (params?.experiment_id) {
      searchParams.set(
        "experiment_id",
        params.experiment_id
      );
    }

    if (params?.condition) {
      searchParams.set(
        "condition",
        params.condition
      );
    }

    if (params?.search) {
      searchParams.set(
        "search",
        params.search
      );
    }

    if (params?.limit !== undefined) {
      searchParams.set(
        "limit",
        String(params.limit)
      );
    }

    if (params?.offset !== undefined) {
      searchParams.set(
        "offset",
        String(params.offset)
      );
    }

    const qs = searchParams.toString();

    return request<PaginatedResponses>(
      `/responses${qs ? `?${qs}` : ""}`
    );
  },

  listPairs: (params?: {
    experiment_id?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();

    if (params?.experiment_id) {
      searchParams.set("experiment_id", params.experiment_id);
    }

    if (params?.search) {
      searchParams.set("search", params.search);
    }

    if (params?.limit !== undefined) {
      searchParams.set("limit", String(params.limit));
    }

    if (params?.offset !== undefined) {
      searchParams.set("offset", String(params.offset));
    }

    const qs = searchParams.toString();

    return request<PaginatedPairs>(
      `/responses/pairs${qs ? `?${qs}` : ""}`
    );
  },

  get: (id: string) =>
    request<ExperimentResponseItem>(
      `/responses/${id}`
    ),

  delete: (id: string) =>
    request<{ deleted: boolean }>(
      `/responses/${id}`,
      {
        method: "DELETE",
      }
    ),

  bulkDelete: (experimentId?: string) => {
    const qs = experimentId
      ? `?experiment_id=${experimentId}`
      : "";

    return request<{ deleted: number }>(
      `/responses${qs}`,
      {
        method: "DELETE",
      }
    );
  },
};


// ── Coding ───────────────────────────────────────────────────────────────────

export const codingApi = {
  /**
   * Get all coding records.
   */
  list: (coderId?: string) => {
    const qs = coderId
      ? `?coder_id=${encodeURIComponent(coderId)}`
      : "";

    return request<CodingEntry[]>(
      `/coding${qs}`
    );
  },

  /**
   * Get blinded response pairs.
   *
   * Gender condition labels are hidden by the backend.
   * If coder_id is provided, only that coder's
   * existing coding is attached to each response.
   */
  blind: (params?: {
    experiment_id?: string;
    shuffle_seed?: number;
    coder_id?: string;
  }) => {
    const searchParams =
      new URLSearchParams();

    if (params?.experiment_id) {
      searchParams.set(
        "experiment_id",
        params.experiment_id
      );
    }

    if (
      params?.shuffle_seed !== undefined
    ) {
      searchParams.set(
        "shuffle_seed",
        String(params.shuffle_seed)
      );
    }

    if (params?.coder_id) {
      searchParams.set(
        "coder_id",
        params.coder_id
      );
    }

    const qs = searchParams.toString();

    return request<BlindPairsResult>(
      `/coding/blind${qs ? `?${qs}` : ""}`
    );
  },

  /**
   * Save or update a coding record.
   *
   * The backend identifies a coding uniquely using:
   * response_id + coder_id
   */
  save: (data: CodingCreate) =>
    request<CodingEntry>(
      "/coding",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),
};


// ── Analysis ─────────────────────────────────────────────────────────────────

export const analysisApi = {
  /**
   * Overall analysis summary.
   *
   * If experimentId is omitted, analysis is aggregated
   * across all experiments.
   */
  summary: (experimentId?: string) => {
    const qs = experimentId
      ? `?experiment_id=${experimentId}`
      : "";

    return request<AnalysisSummary>(
      `/analysis/summary${qs}`
    );
  },

  /**
   * Analysis for one experiment.
   */
  byExperiment: (experimentId: string) =>
    request<AnalysisSummary>(
      `/analysis/by-experiment/${experimentId}`
    ),

  /**
   * Analysis for all experiments separately.
   */
  allExperiments: () =>
    request<AnalysisSummary[]>(
      "/analysis/all-experiments"
    ),

  /**
   * Calculate inter-rater agreement between two coders.
   *
   * Only responses coded by BOTH coders are included.
   *
   * The backend calculates:
   * - ICC(2,1) for Truth
   * - ICC(2,1) for Indeterminacy
   * - ICC(2,1) for Falsity
   * - Mean Absolute Difference
   * - Overall ICC
   */
  interRater: (
    experimentId?: string,
    coder1: string = "coder_1",
    coder2: string = "coder_2"
  ) => {
    const searchParams =
      new URLSearchParams();

    if (experimentId) {
      searchParams.set(
        "experiment_id",
        experimentId
      );
    }

    searchParams.set(
      "coder_1",
      coder1
    );

    searchParams.set(
      "coder_2",
      coder2
    );

    const qs = searchParams.toString();

    return request<InterRaterReliability>(
      `/analysis/inter-rater?${qs}`
    );
  },
};


// ── Ollama ───────────────────────────────────────────────────────────────────

export const ollamaApi = {
  models: () =>
    request<OllamaModel[]>(
      "/ollama/models"
    ),

  health: () =>
    request<{ healthy: boolean }>(
      "/ollama/health"
    ),
};


// ── Export ───────────────────────────────────────────────────────────────────

export const exportApi = {
  downloadUrl: () =>
    `${BASE_URL}/export`,
};