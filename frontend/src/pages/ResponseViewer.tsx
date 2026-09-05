import React, { useState, useEffect } from "react";
import { Search, ChevronDown, ChevronUp, Bot, ScrollText, Play, Trash2, SplitSquareVertical } from "lucide-react";
import { responsesApi, experimentsApi } from "../api/client";
import type { ResponsePair, Experiment } from "../types";

export default function ResponseViewer() {
  const [pairs, setPairs] = useState<ResponsePair[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Filters
  const [experimentId, setExperimentId] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const limit = 15;

  const [expandedPairId, setExpandedPairId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadExperiments();
  }, []);

  useEffect(() => {
    loadPairs();
  }, [experimentId, search, page]);

  async function loadExperiments() {
    try {
      const data = await experimentsApi.list();
      setExperiments(data);
    } catch (err) {
      console.error("Failed to load experiments:", err);
    }
  }

  async function loadPairs() {
    try {
      setLoading(true);
      const res = await responsesApi.listPairs({
        experiment_id: experimentId || undefined,
        search: search || undefined,
        limit,
        offset: page * limit,
      });
      setPairs(res.data);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load response pairs:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleDeletePair(e: React.MouseEvent, pair: ResponsePair) {
    e.stopPropagation();
    if (!confirm("Delete this response pair?")) return;
    try {
      setDeleting(true);
      if (pair.original?.id) {
        await responsesApi.delete(pair.original.id);
      }
      if (pair.swapped?.id && pair.swapped.id !== pair.original?.id) {
        await responsesApi.delete(pair.swapped.id);
      }
      if (expandedPairId === pair.pair_id) setExpandedPairId(null);
      await loadPairs();
    } catch (err) {
      console.error("Failed to delete pair:", err);
    } finally {
      setDeleting(false);
    }
  }

  async function handleBulkDelete() {
    const label = experimentId ? "all responses for this experiment" : "ALL responses";
    if (!confirm(`Are you sure you want to delete ${label}? This cannot be undone.`)) return;
    try {
      setDeleting(true);
      await responsesApi.bulkDelete(experimentId || undefined);
      setExpandedPairId(null);
      setPage(0);
      await loadPairs();
    } catch (err) {
      console.error("Failed to bulk delete responses:", err);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-3">
            <SplitSquareVertical className="text-primary-400" size={26} />
            Response Viewer
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Review linked original and counterfactual-swapped NPC responses side-by-side
          </p>
        </div>
        {total > 0 && (
          <button
            className="btn-secondary !border-red-500/40 !text-red-400 hover:!bg-red-500/10 flex items-center gap-2 self-start sm:self-auto"
            onClick={handleBulkDelete}
            disabled={deleting}
          >
            <Trash2 size={14} />
            {experimentId ? "Delete Experiment Responses" : "Delete All Responses"}
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="glass-card-static p-4 mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="input-label">Experiment</label>
          <select
            className="input-field py-2"
            value={experimentId}
            onChange={(e) => {
              setExperimentId(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All Experiments</option>
            {experiments.map((e) => (
              <option key={e.id} value={e.id}>
                {e.model} ({new Date(e.created_at).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="input-label">Search</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
            <input
              type="text"
              className="input-field py-2 pl-9"
              placeholder="Search in scenario, scaffold, or responses..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
          </div>
        </div>
      </div>

      {/* Response Pairs List */}
      <div className="space-y-4">
        {loading ? (
          <div className="glass-card p-12 text-center text-surface-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mb-3"></div>
            <p>Loading linked response pairs...</p>
          </div>
        ) : pairs.length === 0 ? (
          <div className="glass-card p-12 text-center text-surface-400">
            No response pairs found matching your criteria.
          </div>
        ) : (
          pairs.map((pair) => {
            const isExpanded = expandedPairId === pair.pair_id;
            const orig = pair.original;
            const swap = pair.swapped;
            const scaffoldText = orig?.scaffold_prompt || orig?.system_prompt || swap?.scaffold_prompt || swap?.system_prompt || "";

            return (
              <div
                key={pair.pair_id}
                className={`glass-card overflow-hidden transition-all duration-200 border ${
                  isExpanded ? "border-primary-500/40 shadow-lg shadow-primary-500/5" : "border-surface-700/40 hover:border-surface-600/60"
                }`}
              >
                {/* Header Summary Row */}
                <div
                  className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer hover:bg-surface-800/30 transition-colors"
                  onClick={() => setExpandedPairId(isExpanded ? null : pair.pair_id)}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-800 text-surface-200 border border-surface-700">
                      Replicate #{pair.replicate_number}
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-md bg-surface-800/80 text-surface-300 font-mono">
                      {pair.model}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                        Original
                      </span>
                      <span className="text-surface-500 text-xs">↔</span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-pink-500/15 text-pink-300 border border-pink-500/30">
                        Swapped
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between md:justify-end gap-3">
                    <span className="text-xs text-surface-400">
                      {pair.timestamp ? new Date(pair.timestamp).toLocaleString() : ""}
                    </span>
                    <button
                      className="p-1.5 rounded-lg text-surface-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      onClick={(e) => handleDeletePair(e, pair)}
                      disabled={deleting}
                      title="Delete pair"
                    >
                      <Trash2 size={15} />
                    </button>
                    <span className="p-1 rounded text-surface-400 bg-surface-800/60">
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </span>
                  </div>
                </div>

                {/* Collapsed Snippet */}
                {!isExpanded && (
                  <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-surface-400 border-t border-surface-800/40 pt-3">
                    <div className="line-clamp-2">
                      <span className="font-semibold text-indigo-300 mr-1.5">Original:</span>
                      {orig?.generated_response || "No response recorded"}
                    </div>
                    <div className="line-clamp-2">
                      <span className="font-semibold text-pink-300 mr-1.5">Swapped:</span>
                      {swap?.generated_response || "No response recorded"}
                    </div>
                  </div>
                )}

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-5 pb-6 pt-2 border-t border-surface-700/40 space-y-6 animate-slide-up">
                    {/* Prompts info: Scaffold and Scenario */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      <div className="glass-card-static p-4 bg-surface-900/60 rounded-xl border border-surface-800">
                        <div className="flex items-center gap-2 text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wider">
                          <Bot size={14} className="text-primary-400" /> NPC Persona (Scaffold)
                        </div>
                        <div className="text-xs font-mono text-surface-300 whitespace-pre-wrap max-h-40 overflow-y-auto pr-2">
                          {scaffoldText || "No scaffold recorded."}
                        </div>
                      </div>

                      <div className="glass-card-static p-4 bg-surface-900/60 rounded-xl border border-surface-800">
                        <div className="flex items-center gap-2 text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wider">
                          <ScrollText size={14} className="text-amber-400" /> Scenario Context
                        </div>
                        <div className="space-y-2 text-xs font-mono max-h-40 overflow-y-auto pr-2">
                          <div className="text-indigo-300">
                            <span className="font-bold text-[10px] uppercase tracking-wide opacity-75">Original:</span>
                            <p className="text-surface-300 whitespace-pre-wrap mt-0.5">
                              {orig?.scenario_prompt || orig?.user_prompt || "None"}
                            </p>
                          </div>
                          {swap?.scenario_prompt && swap.scenario_prompt !== orig?.scenario_prompt && (
                            <div className="text-pink-300 pt-2 border-t border-surface-800/80">
                              <span className="font-bold text-[10px] uppercase tracking-wide opacity-75">Swapped:</span>
                              <p className="text-surface-300 whitespace-pre-wrap mt-0.5">
                                {swap.scenario_prompt || swap.user_prompt}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Side-by-side Responses */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Original condition */}
                      <div className="flex flex-col rounded-xl border border-indigo-500/30 bg-indigo-950/15 overflow-hidden">
                        <div className="px-4 py-3 bg-indigo-900/30 border-b border-indigo-500/20 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Play size={14} className="text-indigo-400" />
                            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                              Original Response
                            </span>
                          </div>
                          <span className="text-[11px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-200">
                            Condition: original
                          </span>
                        </div>
                        <div className="p-4 text-sm text-surface-200 whitespace-pre-wrap font-sans flex-1 leading-relaxed">
                          {orig?.generated_response || (
                            <span className="text-surface-500 italic">No response generated.</span>
                          )}
                        </div>
                      </div>

                      {/* Swapped condition */}
                      <div className="flex flex-col rounded-xl border border-pink-500/30 bg-pink-950/15 overflow-hidden">
                        <div className="px-4 py-3 bg-pink-900/30 border-b border-pink-500/20 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Play size={14} className="text-pink-400" />
                            <span className="text-xs font-bold uppercase tracking-wider text-pink-300">
                              Counterfactual Swapped Response
                            </span>
                          </div>
                          <span className="text-[11px] px-2 py-0.5 rounded bg-pink-500/20 text-pink-200">
                            Condition: swapped
                          </span>
                        </div>
                        <div className="p-4 text-sm text-surface-200 whitespace-pre-wrap font-sans flex-1 leading-relaxed">
                          {swap?.generated_response || (
                            <span className="text-surface-500 italic">No response generated.</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="glass-card-static p-4 mt-6 flex items-center justify-between">
          <span className="text-sm text-surface-400">
            Showing pairs {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              className="btn-secondary !py-1 !px-3"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              className="btn-secondary !py-1 !px-3"
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
