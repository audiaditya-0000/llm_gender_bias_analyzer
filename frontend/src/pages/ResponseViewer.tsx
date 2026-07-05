import React, { useState, useEffect } from "react";
import { Search, ChevronDown, ChevronUp, Bot, User, Play } from "lucide-react";
import { responsesApi, experimentsApi } from "../api/client";
import type { ExperimentResponseItem, Experiment } from "../types";

export default function ResponseViewer() {
  const [responses, setResponses] = useState<ExperimentResponseItem[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Filters
  const [experimentId, setExperimentId] = useState("");
  const [condition, setCondition] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const limit = 20;

  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    loadExperiments();
  }, []);

  useEffect(() => {
    loadResponses();
  }, [experimentId, condition, search, page]);

  async function loadExperiments() {
    try {
      const data = await experimentsApi.list();
      setExperiments(data);
    } catch (err) {
      console.error("Failed to load experiments:", err);
    }
  }

  async function loadResponses() {
    try {
      setLoading(true);
      const res = await responsesApi.list({
        experiment_id: experimentId || undefined,
        condition: condition || undefined,
        search: search || undefined,
        limit,
        offset: page * limit,
      });
      setResponses(res.data);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load responses:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Response Viewer</h1>
          <p className="text-sm text-surface-400 mt-1">
            Review and search through all generated LLM responses
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card-static p-4 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
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
          <label className="input-label">Condition</label>
          <select
            className="input-field py-2"
            value={condition}
            onChange={(e) => {
              setCondition(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All Conditions</option>
            <option value="male_npc">Male NPC</option>
            <option value="female_npc">Female NPC</option>
            <option value="male_player">Male Player</option>
            <option value="female_player">Female Player</option>
            <option value="male_third_person">Male Third Person</option>
            <option value="female_third_person">Female Third Person</option>
          </select>
        </div>
        <div>
          <label className="input-label">Search</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
            <input
              type="text"
              className="input-field py-2 pl-9"
              placeholder="Search in prompts or responses..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-800/80 text-surface-300">
              <tr>
                <th className="px-6 py-3 font-medium border-b border-surface-700/50">Model</th>
                <th className="px-6 py-3 font-medium border-b border-surface-700/50">Condition</th>
                <th className="px-6 py-3 font-medium border-b border-surface-700/50">Rep</th>
                <th className="px-6 py-3 font-medium border-b border-surface-700/50">Preview</th>
                <th className="px-6 py-3 font-medium border-b border-surface-700/50"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700/30">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-surface-500">
                    Loading responses...
                  </td>
                </tr>
              ) : responses.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-surface-500">
                    No responses found matching filters.
                  </td>
                </tr>
              ) : (
                responses.map((res) => {
                  const isExpanded = expandedRow === res.id;
                  return (
                    <React.Fragment key={res.id}>
                      <tr 
                        className={`hover:bg-surface-800/40 transition-colors cursor-pointer ${isExpanded ? 'bg-surface-800/40' : ''}`}
                        onClick={() => setExpandedRow(isExpanded ? null : res.id)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-surface-200">
                          {res.model}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`badge ${res.condition.startsWith('male') ? 'badge-info' : 'badge-error'}`}>
                            {res.condition}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-surface-400">
                          {res.replicate_number}
                        </td>
                        <td className="px-6 py-4 text-surface-400 max-w-xs truncate">
                          {res.generated_response.substring(0, 80)}...
                        </td>
                        <td className="px-6 py-4 text-right text-surface-500">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-surface-800/20">
                          <td colSpan={5} className="px-6 py-6 border-b border-surface-700/50">
                            <div className="grid md:grid-cols-2 gap-6 animate-slide-up">
                              <div className="space-y-4">
                                <div>
                                  <div className="flex items-center gap-2 text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wider">
                                    <Bot size={14} /> System Prompt
                                  </div>
                                  <div className="bg-surface-900/50 p-4 rounded-xl text-sm font-mono text-surface-300 whitespace-pre-wrap">
                                    {res.system_prompt}
                                  </div>
                                </div>
                                <div>
                                  <div className="flex items-center gap-2 text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wider">
                                    <User size={14} /> User Prompt
                                  </div>
                                  <div className="bg-surface-900/50 p-4 rounded-xl text-sm font-mono text-surface-300 whitespace-pre-wrap">
                                    {res.user_prompt}
                                  </div>
                                </div>
                              </div>
                              <div>
                                <div className="flex items-center gap-2 text-xs font-semibold text-accent-400 mb-2 uppercase tracking-wider">
                                  <Play size={14} /> Generated Response
                                </div>
                                <div className="bg-surface-900/50 p-4 rounded-xl text-sm text-surface-200 whitespace-pre-wrap h-full">
                                  {res.generated_response}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {total > limit && (
          <div className="px-6 py-4 border-t border-surface-700/50 flex items-center justify-between">
            <span className="text-sm text-surface-400">
              Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total}
            </span>
            <div className="flex gap-2">
              <button 
                className="btn-secondary !py-1 !px-3"
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </button>
              <button 
                className="btn-secondary !py-1 !px-3"
                disabled={(page + 1) * limit >= total}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
