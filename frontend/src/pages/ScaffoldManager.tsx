import { useState, useEffect } from "react";
import { Plus, Pencil, Trash2, X, Wrench } from "lucide-react";
import { scaffoldsApi } from "../api/client";
import type { Scaffold, ScaffoldCreate } from "../types";

export default function ScaffoldManager() {
  const [scaffolds, setScaffolds] = useState<Scaffold[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Scaffold | null>(null);
  const [form, setForm] = useState<ScaffoldCreate>({
    name: "",
    prompt: "",
    version: "1.0",
    notes: "",
  });

  useEffect(() => {
    loadScaffolds();
  }, []);

  async function loadScaffolds() {
    try {
      setLoading(true);
      const data = await scaffoldsApi.list();
      setScaffolds(data);
    } catch (err) {
      console.error("Failed to load scaffolds:", err);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({ name: "", prompt: "", version: "1.0", notes: "" });
    setShowModal(true);
  }

  function openEdit(scaffold: Scaffold) {
    setEditing(scaffold);
    setForm({
      name: scaffold.name,
      prompt: scaffold.prompt,
      version: scaffold.version,
      notes: scaffold.notes || "",
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editing) {
        await scaffoldsApi.update(editing.id, form);
      } else {
        await scaffoldsApi.create(form);
      }
      setShowModal(false);
      loadScaffolds();
    } catch (err) {
      console.error("Failed to save scaffold:", err);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this scaffold?")) return;
    try {
      await scaffoldsApi.delete(id);
      loadScaffolds();
    } catch (err) {
      console.error("Failed to delete scaffold:", err);
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Prompt Scaffold Manager</h1>
          <p className="text-sm text-surface-400 mt-1">
            Define NPC system prompts that shape model behavior
          </p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          <Plus size={16} />
          New Scaffold
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-20 text-surface-500">Loading scaffolds...</div>
      ) : scaffolds.length === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <Wrench size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No scaffolds yet</h3>
          <p className="text-sm text-surface-500 mb-6">
            Create your first NPC system prompt scaffold.
          </p>
          <button className="btn-primary" onClick={openCreate}>
            <Plus size={16} />
            Create Scaffold
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {scaffolds.map((scaffold, idx) => (
            <div
              key={scaffold.id}
              className="glass-card p-5 animate-slide-up"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-base font-semibold text-surface-100">{scaffold.name}</h3>
                    <span className="badge badge-info">v{scaffold.version}</span>
                  </div>
                  <div className="text-xs text-surface-500 font-mono bg-surface-800/60 rounded-lg p-3 max-h-32 overflow-hidden whitespace-pre-wrap mb-2">
                    {scaffold.prompt.substring(0, 400)}
                    {scaffold.prompt.length > 400 && "..."}
                  </div>
                  {scaffold.notes && (
                    <p className="text-xs text-surface-500 italic">{scaffold.notes}</p>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <button className="btn-icon" onClick={() => openEdit(scaffold)} title="Edit">
                    <Pencil size={16} />
                  </button>
                  <button
                    className="btn-icon hover:!text-rose-400"
                    onClick={() => handleDelete(scaffold.id)}
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
                {editing ? "Edit Scaffold" : "New Scaffold"}
              </h2>
              <button className="btn-icon" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="input-label">Name</label>
                <input
                  className="input-field"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g., Friendly NPC, Aggressive Guard"
                  required
                />
              </div>

              <div>
                <label className="input-label">Version</label>
                <input
                  className="input-field"
                  value={form.version}
                  onChange={(e) => setForm({ ...form, version: e.target.value })}
                  placeholder="1.0"
                  required
                />
              </div>

              <div>
                <label className="input-label">System Prompt</label>
                <textarea
                  className="input-field"
                  value={form.prompt}
                  onChange={(e) => setForm({ ...form, prompt: e.target.value })}
                  placeholder="You are a [male/female] NPC in a fantasy RPG. You are a shopkeeper in a medieval town..."
                  rows={8}
                  required
                />
              </div>

              <div>
                <label className="input-label">Notes (optional)</label>
                <textarea
                  className="input-field"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Research notes about this scaffold..."
                  rows={3}
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
