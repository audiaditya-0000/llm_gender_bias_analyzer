import { useState, useEffect } from "react";
import { FlaskConical, Save, Trash2, RefreshCw } from "lucide-react";
import { experimentsApi, scenariosApi, scaffoldsApi, ollamaApi } from "../api/client";
import type { Experiment, Scenario, Scaffold, OllamaModel, ExperimentCreate } from "../types";

export default function ExperimentConfig() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scaffolds, setScaffolds] = useState<Scaffold[]>([]);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [ollamaHealthy, setOllamaHealthy] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState<ExperimentCreate>({
    scenario_id: "",
    scaffold_id: "",
    model: "",
    temperature: 0.7,
    top_p: 0.9,
    max_tokens: 512,
    seed: 42,
    num_replicates: 20,
  });

  const [seedEnabled, setSeedEnabled] = useState(true);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    try {
      const [expData, scenData, scaffData] = await Promise.all([
        experimentsApi.list(),
        scenariosApi.list(),
        scaffoldsApi.list(),
      ]);
      setExperiments(expData);
      setScenarios(scenData);
      setScaffolds(scaffData);

      // Try to load models
      try {
        const health = await ollamaApi.health();
        setOllamaHealthy(health.healthy);
        if (health.healthy) {
          const modelData = await ollamaApi.models();
          setModels(modelData);
          if (modelData.length > 0 && !form.model) {
            setForm((f) => ({ ...f, model: modelData[0].name }));
          }
        }
      } catch {
        setOllamaHealthy(false);
      }
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }

  async function refreshModels() {
    try {
      const health = await ollamaApi.health();
      setOllamaHealthy(health.healthy);
      if (health.healthy) {
        const modelData = await ollamaApi.models();
        setModels(modelData);
      }
    } catch {
      setOllamaHealthy(false);
    }
  }

  async function handleSave() {
    if (!form.scenario_id || !form.scaffold_id || !form.model) {
      alert("Please select a scenario, scaffold, and model.");
      return;
    }
    try {
      const payload = {
        ...form,
        seed: seedEnabled ? form.seed : null,
      };
      const created = await experimentsApi.create(payload);
      if (created && created.id) {
        setExperiments((prev) => [created, ...prev]);
      }
      loadAll();
    } catch (err) {
      console.error("Failed to save experiment:", err);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this experiment configuration?")) return;
    try {
      setExperiments((prev) => prev.filter((e) => e.id !== id));
      await experimentsApi.delete(id);
      loadAll();
    } catch (err) {
      console.error("Failed to delete:", err);
      loadAll();
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  if (loading && experiments.length === 0) {
    return <div className="text-center py-20 text-surface-500">Loading...</div>;
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Experiment Configuration</h1>
          <p className="text-sm text-surface-400 mt-1">
            Configure model parameters and experiment settings
          </p>
        </div>
        <div className="flex items-center gap-2">
          {ollamaHealthy !== null && (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium ${
              ollamaHealthy
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
            }`}>
              <div className={`glow-dot ${ollamaHealthy ? "bg-emerald-400" : "bg-rose-400"}`} />
              Ollama {ollamaHealthy ? "Connected" : "Offline"}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Form */}
        <div className="lg:col-span-2">
          <div className="glass-card-static p-6">
            <h2 className="text-base font-semibold text-surface-100 mb-5">New Experiment</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {/* Scenario */}
              <div>
                <label className="input-label">Scenario</label>
                <select
                  className="input-field"
                  value={form.scenario_id}
                  onChange={(e) => setForm({ ...form, scenario_id: e.target.value })}
                >
                  <option value="">Select a scenario...</option>
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title} ({s.category})
                    </option>
                  ))}
                </select>
              </div>

              {/* Scaffold */}
              <div>
                <label className="input-label">Scaffold</label>
                <select
                  className="input-field"
                  value={form.scaffold_id}
                  onChange={(e) => setForm({ ...form, scaffold_id: e.target.value })}
                >
                  <option value="">Select a scaffold...</option>
                  {scaffolds.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} (v{s.version})
                    </option>
                  ))}
                </select>
              </div>

              {/* Model */}
              <div>
                <label className="input-label flex items-center gap-2">
                  Ollama Model
                  <button className="btn-icon !p-0" onClick={refreshModels} title="Refresh models">
                    <RefreshCw size={12} />
                  </button>
                </label>
                {models.length > 0 ? (
                  <select
                    className="input-field"
                    value={form.model}
                    onChange={(e) => setForm({ ...form, model: e.target.value })}
                  >
                    {models.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name} ({formatBytes(m.size)})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="input-field"
                    value={form.model}
                    onChange={(e) => setForm({ ...form, model: e.target.value })}
                    placeholder="e.g., llama3.2, mistral"
                  />
                )}
              </div>


              {/* Replicates */}
              <div>
                <label className="input-label">Number of Replicates</label>
                <input
                  type="number"
                  className="input-field"
                  value={form.num_replicates}
                  onChange={(e) =>
                    setForm({ ...form, num_replicates: parseInt(e.target.value) || 1 })
                  }
                  min={1}
                  max={100}
                />
              </div>
            </div>

            {/* Sliders */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="input-label">
                  Temperature: <span className="text-accent-400">{form.temperature.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.01}
                  value={form.temperature}
                  onChange={(e) =>
                    setForm({ ...form, temperature: parseFloat(e.target.value) })
                  }
                />
                <div className="flex justify-between text-[0.625rem] text-surface-600 mt-1">
                  <span>Deterministic</span>
                  <span>Creative</span>
                </div>
              </div>

              <div>
                <label className="input-label">
                  Top P: <span className="text-accent-400">{form.top_p.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={form.top_p}
                  onChange={(e) => setForm({ ...form, top_p: parseFloat(e.target.value) })}
                />
                <div className="flex justify-between text-[0.625rem] text-surface-600 mt-1">
                  <span>Focused</span>
                  <span>Diverse</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div>
                <label className="input-label">Max Tokens</label>
                <input
                  type="number"
                  className="input-field"
                  value={form.max_tokens}
                  onChange={(e) =>
                    setForm({ ...form, max_tokens: parseInt(e.target.value) || 128 })
                  }
                  min={64}
                  max={4096}
                />
              </div>

              <div>
                <label className="input-label flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={seedEnabled}
                    onChange={(e) => {
                      setSeedEnabled(e.target.checked);
                      if (!e.target.checked) setForm({ ...form, seed: null });
                    }}
                    className="rounded"
                  />
                  Seed (for reproducibility)
                </label>
                <input
                  type="number"
                  className="input-field"
                  value={form.seed ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, seed: e.target.value ? parseInt(e.target.value) : null })
                  }
                  placeholder="Random"
                  disabled={!seedEnabled}
                />
              </div>
            </div>

            <button className="btn-primary" onClick={handleSave}>
              <Save size={16} />
              Save Experiment Configuration
            </button>
          </div>
        </div>

        {/* Saved Experiments */}
        <div>
          <div className="glass-card-static p-5">
            <h2 className="text-base font-semibold text-surface-100 mb-4">
              Saved Experiments ({experiments.length})
            </h2>
            {experiments.length === 0 ? (
              <p className="text-sm text-surface-500 text-center py-8">
                No experiments configured yet
              </p>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {experiments.map((exp) => {
                  const scenario = scenarios.find((s) => s.id === exp.scenario_id);
                  const scaffold = scaffolds.find((s) => s.id === exp.scaffold_id);
                  return (
                    <div key={exp.id} className="bg-surface-800/60 rounded-xl p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FlaskConical size={14} className="text-accent-400" />
                          <span className="text-xs font-semibold text-surface-200">
                            {exp.model}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span
                            className={`badge ${
                              exp.status === "completed"
                                ? "badge-success"
                                : exp.status === "running"
                                ? "badge-warning"
                                : exp.status === "failed"
                                ? "badge-error"
                                : "badge-neutral"
                            }`}
                          >
                            {exp.status}
                          </span>
                          <button
                            className="btn-icon hover:!text-rose-400"
                            onClick={() => handleDelete(exp.id)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="text-xs text-surface-400 space-y-1">
                        <div>Scenario: {scenario?.title || "—"}</div>
                        <div>Scaffold: {scaffold?.name || "—"}</div>
                        <div>
                          T={exp.temperature} | P={exp.top_p} | Reps={exp.num_replicates}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
