import { useState, useEffect } from "react";
import { EyeOff, CheckCircle2, Save, ChevronRight, SkipForward } from "lucide-react";
import { codingApi, experimentsApi } from "../api/client";
import type { BlindResponseItem, Experiment } from "../types";

export default function BlindCoding() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [responses, setResponses] = useState<BlindResponseItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [experimentId, setExperimentId] = useState("");
  const [shuffleSeed, setShuffleSeed] = useState<number>(42);

  // Coding form state
  const [truth, setTruth] = useState(0.5);
  const [indeterminacy, setIndeterminacy] = useState(0.5);
  const [falsity, setFalsity] = useState(0.5);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    loadExperiments();
  }, []);

  useEffect(() => {
    loadBlindData();
  }, [experimentId, shuffleSeed]);

  // When current response changes, populate form if already coded
  useEffect(() => {
    if (responses.length > 0 && currentIndex < responses.length) {
      const current = responses[currentIndex];
      if (current.coding) {
        setTruth(current.coding.truth);
        setIndeterminacy(current.coding.indeterminacy);
        setFalsity(current.coding.falsity);
        setNotes(current.coding.reasoning_notes);
      } else {
        // Reset to defaults
        setTruth(0.5);
        setIndeterminacy(0.5);
        setFalsity(0.5);
        setNotes("");
      }
    }
  }, [currentIndex, responses]);

  async function loadExperiments() {
    try {
      const data = await experimentsApi.list();
      setExperiments(data);
    } catch (err) {
      console.error("Failed to load experiments:", err);
    }
  }

  async function loadBlindData() {
    try {
      setLoading(true);
      const res = await codingApi.blind({
        experiment_id: experimentId || undefined,
        shuffle_seed: shuffleSeed,
      });
      setResponses(res.data);
      // Auto-advance to first uncoded response
      const firstUncoded = res.data.findIndex((r) => r.coding === null);
      if (firstUncoded !== -1) {
        setCurrentIndex(firstUncoded);
      } else {
        setCurrentIndex(0);
      }
    } catch (err) {
      console.error("Failed to load blind data:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveAndNext() {
    if (responses.length === 0) return;
    const current = responses[currentIndex];
    
    try {
      setSaving(true);
      const newCoding = await codingApi.save({
        response_id: current.id,
        truth,
        indeterminacy,
        falsity,
        reasoning_notes: notes,
      });

      // Update local state
      const updatedResponses = [...responses];
      updatedResponses[currentIndex].coding = newCoding;
      setResponses(updatedResponses);

      // Advance
      if (currentIndex < responses.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err) {
      console.error("Failed to save coding:", err);
      alert("Failed to save coding. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const current = responses[currentIndex];
  const codedCount = responses.filter(r => r.coding !== null).length;
  const total = responses.length;

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-2">
            <EyeOff className="text-accent-400" />
            Blind Coding Interface
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Assign neutrosophic truth values to outputs (gender labels hidden)
          </p>
        </div>
      </div>

      {/* Config Bar */}
      <div className="glass-card-static p-4 mb-6 flex flex-wrap gap-4 items-center justify-between">
        <div className="flex gap-4">
          <div>
            <label className="input-label !mb-1">Filter by Experiment</label>
            <select
              className="input-field py-1.5 text-sm"
              value={experimentId}
              onChange={(e) => setExperimentId(e.target.value)}
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
             <label className="input-label !mb-1">Shuffle Seed</label>
             <input
               type="number"
               className="input-field py-1.5 text-sm w-24"
               value={shuffleSeed}
               onChange={(e) => setShuffleSeed(parseInt(e.target.value) || 0)}
             />
          </div>
        </div>
        
        {total > 0 && (
          <div className="text-right">
            <div className="text-sm font-semibold text-surface-200">
              {codedCount} / {total} Coded
            </div>
            <div className="w-48 h-2 bg-surface-700 rounded-full mt-1.5 overflow-hidden">
              <div 
                className="h-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${(codedCount / total) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="text-center py-20 text-surface-500">Loading blind data...</div>
      ) : total === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <CheckCircle2 size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No responses to code</h3>
          <p className="text-sm text-surface-500">
            Run an experiment first to generate responses.
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Response Viewer Area */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between text-sm text-surface-400 bg-surface-800/50 px-4 py-2 rounded-xl">
              <span>Response {currentIndex + 1} of {total}</span>
              <span>Model: <span className="text-surface-200">{current?.model}</span></span>
            </div>

            <div className="glass-card p-6 h-[500px] overflow-y-auto">
              <h3 className="text-xs font-semibold text-surface-400 mb-3 uppercase tracking-wider">
                User Prompt
              </h3>
              <div className="bg-surface-900/50 p-4 rounded-xl text-sm font-mono text-surface-300 whitespace-pre-wrap mb-6 border border-surface-700/50">
                {current?.user_prompt}
              </div>

              <h3 className="text-xs font-semibold text-accent-400 mb-3 uppercase tracking-wider">
                Generated Response
              </h3>
              <div className="text-base text-surface-100 whitespace-pre-wrap leading-relaxed">
                {current?.generated_response}
              </div>
            </div>
          </div>

          {/* Coding Panel */}
          <div className="lg:col-span-2">
            <div className="glass-card-static p-6 h-full flex flex-col">
              <h2 className="text-lg font-bold text-surface-50 mb-6 flex items-center justify-between">
                Coding Values
                {current?.coding && <span className="badge badge-success">Saved</span>}
              </h2>

              <div className="space-y-6 flex-1">
                {/* Truth Slider */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-semibold text-emerald-400">Truth (T)</label>
                    <span className="text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded">
                      {truth.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={truth}
                    onChange={(e) => setTruth(parseFloat(e.target.value))}
                    className="accent-emerald-500"
                    style={{ background: "linear-gradient(90deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.8))" }}
                  />
                  <div className="flex justify-between text-[10px] text-surface-500 mt-1 uppercase tracking-wider">
                    <span>Completely False</span>
                    <span>Completely True</span>
                  </div>
                </div>

                {/* Indeterminacy Slider */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-semibold text-amber-400">Indeterminacy (I)</label>
                    <span className="text-amber-300 font-mono bg-amber-500/10 px-2 py-0.5 rounded">
                      {indeterminacy.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={indeterminacy}
                    onChange={(e) => setIndeterminacy(parseFloat(e.target.value))}
                    style={{ background: "linear-gradient(90deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.8))" }}
                  />
                  <div className="flex justify-between text-[10px] text-surface-500 mt-1 uppercase tracking-wider">
                    <span>Certain</span>
                    <span>Ambiguous/Uncertain</span>
                  </div>
                </div>

                {/* Falsity Slider */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-semibold text-rose-400">Falsity (F)</label>
                    <span className="text-rose-300 font-mono bg-rose-500/10 px-2 py-0.5 rounded">
                      {falsity.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={falsity}
                    onChange={(e) => setFalsity(parseFloat(e.target.value))}
                    style={{ background: "linear-gradient(90deg, rgba(244, 63, 94, 0.2), rgba(244, 63, 94, 0.8))" }}
                  />
                  <div className="flex justify-between text-[10px] text-surface-500 mt-1 uppercase tracking-wider">
                    <span>Not False</span>
                    <span>Factually Incorrect/Biased</span>
                  </div>
                </div>

                {/* Notes */}
                <div>
                  <label className="input-label">Reasoning Notes (Optional)</label>
                  <textarea
                    className="input-field bg-surface-900/50"
                    rows={4}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Document why these values were assigned..."
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-6 mt-4 border-t border-surface-700/50">
                <button
                  className="btn-secondary flex-1"
                  onClick={() => currentIndex < total - 1 && setCurrentIndex(currentIndex + 1)}
                  disabled={currentIndex === total - 1}
                >
                  Skip
                  <SkipForward size={16} />
                </button>
                <button
                  className="btn-primary flex-[2] justify-center"
                  onClick={handleSaveAndNext}
                  disabled={saving}
                >
                  <Save size={16} />
                  {saving ? "Saving..." : "Save & Next"}
                  <ChevronRight size={16} className="-ml-1" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
