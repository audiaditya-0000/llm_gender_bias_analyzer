import { useState, useEffect } from "react";
import { Plus, Pencil, Trash2, Search, X, FileText } from "lucide-react";
import { scenariosApi } from "../api/client";
import type { Scenario, ScenarioCreate } from "../types";
import { SCENARIO_CATEGORIES } from "../types";

export default function ScenarioManager() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Scenario | null>(null);
  const [form, setForm] = useState<ScenarioCreate>({
    title: "",
    description: "",
    scenario_text: "",
    category: "General",
    category_other: "",
  });

  useEffect(() => {
    loadScenarios();
  }, []);

  async function loadScenarios() {
    try {
      setLoading(true);
      const data = await scenariosApi.list();
      setScenarios(data);
    } catch (err) {
      console.error("Failed to load scenarios:", err);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({ title: "", description: "", scenario_text: "", category: "General", category_other: "" });
    setShowModal(true);
  }

  function openEdit(scenario: Scenario) {
    setEditing(scenario);
    setForm({
      title: scenario.title,
      description: scenario.description,
      scenario_text: scenario.scenario_text,
      category: scenario.category,
      category_other: scenario.category_other || "",
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editing) {
        await scenariosApi.update(editing.id, form);
      } else {
        await scenariosApi.create(form);
      }
      setShowModal(false);
      loadScenarios();
    } catch (err) {
      console.error("Failed to save scenario:", err);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this scenario?")) return;
    try {
      await scenariosApi.delete(id);
      loadScenarios();
    } catch (err) {
      console.error("Failed to delete scenario:", err);
    }
  }

  const filtered = scenarios.filter(
    (s) =>
      s.title.toLowerCase().includes(search.toLowerCase()) ||
      s.category.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Scenario Manager</h1>
          <p className="text-sm text-surface-400 mt-1">
            Create and manage experimental scenarios for NPC interactions
          </p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          <Plus size={16} />
          New Scenario
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
        <input
          type="text"
          className="input-field pl-9"
          placeholder="Search scenarios by title, category, or description..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-20 text-surface-500">Loading scenarios...</div>
      ) : filtered.length === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <FileText size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No scenarios yet</h3>
          <p className="text-sm text-surface-500 mb-6">
            Create your first scenario to start building experiments.
          </p>
          <button className="btn-primary" onClick={openCreate}>
            <Plus size={16} />
            Create Scenario
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((scenario, idx) => (
            <div
              key={scenario.id}
              className="glass-card p-5 animate-slide-up"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-base font-semibold text-surface-100 truncate">
                      {scenario.title}
                    </h3>
                    <span className="badge badge-info">{scenario.category}</span>
                    {scenario.category === "Other" && scenario.category_other && (
                      <span className="badge badge-neutral">{scenario.category_other}</span>
                    )}
                  </div>
                  <p className="text-sm text-surface-400 mb-3 line-clamp-2">{scenario.description}</p>
                  <div className="text-xs text-surface-600 font-mono bg-surface-800/60 rounded-lg p-3 max-h-24 overflow-hidden">
                    {scenario.scenario_text.substring(0, 200)}
                    {scenario.scenario_text.length > 200 && "..."}
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <button className="btn-icon" onClick={() => openEdit(scenario)} title="Edit">
                    <Pencil size={16} />
                  </button>
                  <button
                    className="btn-icon hover:!text-rose-400"
                    onClick={() => handleDelete(scenario.id)}
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-surface-50">
                {editing ? "Edit Scenario" : "New Scenario"}
              </h2>
              <button className="btn-icon" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="input-label">Title</label>
                <input
                  className="input-field"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Enter scenario title"
                  required
                />
              </div>

              <div>
                <label className="input-label">Category</label>
                <select
                  className="input-field"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                >
                  {SCENARIO_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {form.category === "Other" && (
                <div>
                  <label className="input-label">Custom Category</label>
                  <input
                    className="input-field"
                    value={form.category_other}
                    onChange={(e) => setForm({ ...form, category_other: e.target.value })}
                    placeholder="Enter custom category name"
                  />
                </div>
              )}

              <div>
                <label className="input-label">Description</label>
                <textarea
                  className="input-field"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief description of the scenario"
                  rows={3}
                  required
                />
              </div>

              <div>
                <label className="input-label">Scenario Text</label>
                <textarea
                  className="input-field"
                  value={form.scenario_text}
                  onChange={(e) => setForm({ ...form, scenario_text: e.target.value })}
                  placeholder="The full scenario text that will be used as the user prompt..."
                  rows={6}
                  required
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editing ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
