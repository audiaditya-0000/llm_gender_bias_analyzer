import { useState, useEffect } from "react";
import {
  EyeOff,
  CheckCircle2,
  Save,
  ChevronRight,
  ChevronLeft,
  SkipForward,
  UserRound,
  Info,
  ScrollText,
} from "lucide-react";
import { codingApi, experimentsApi } from "../api/client";
import type { BlindPair, Experiment } from "../types";

const CODER_STORAGE_KEY = "gender_bias_selected_coder";

const CODERS = [
  { id: "coder_1", name: "Coder 1" },
  { id: "coder_2", name: "Coder 2" },
];

export default function BlindCoding() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [pairs, setPairs] = useState<BlindPair[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [experimentId, setExperimentId] = useState("");
  const [shuffleSeed, setShuffleSeed] = useState<number>(42);
  const [coderId, setCoderId] = useState("coder_1");

  // Coding form state for Version A
  const [truthA, setTruthA] = useState(0.5);
  const [indeterminacyA, setIndeterminacyA] = useState(0.5);
  const [falsityA, setFalsityA] = useState(0.5);
  const [notesA, setNotesA] = useState("");

  // Coding form state for Version B
  const [truthB, setTruthB] = useState(0.5);
  const [indeterminacyB, setIndeterminacyB] = useState(0.5);
  const [falsityB, setFalsityB] = useState(0.5);
  const [notesB, setNotesB] = useState("");

  // Load saved coder identity
  useEffect(() => {
    const savedCoder = localStorage.getItem(CODER_STORAGE_KEY);
    if (savedCoder && CODERS.some((c) => c.id === savedCoder)) {
      setCoderId(savedCoder);
    }
  }, []);

  // Save coder identity whenever it changes
  useEffect(() => {
    localStorage.setItem(CODER_STORAGE_KEY, coderId);
  }, [coderId]);

  // Load experiments
  useEffect(() => {
    loadExperiments();
  }, []);

  // Load blind data
  useEffect(() => {
    loadBlindData();
  }, [experimentId, shuffleSeed, coderId]);

  // Populate form when pair changes
  useEffect(() => {
    if (pairs.length > 0 && currentIndex < pairs.length) {
      const current = pairs[currentIndex];

      if (current.version_a?.coding) {
        setTruthA(current.version_a.coding.truth);
        setIndeterminacyA(current.version_a.coding.indeterminacy);
        setFalsityA(current.version_a.coding.falsity);
        setNotesA(current.version_a.coding.reasoning_notes || "");
      } else {
        setTruthA(0.5);
        setIndeterminacyA(0.5);
        setFalsityA(0.5);
        setNotesA("");
      }

      if (current.version_b?.coding) {
        setTruthB(current.version_b.coding.truth);
        setIndeterminacyB(current.version_b.coding.indeterminacy);
        setFalsityB(current.version_b.coding.falsity);
        setNotesB(current.version_b.coding.reasoning_notes || "");
      } else {
        setTruthB(0.5);
        setIndeterminacyB(0.5);
        setFalsityB(0.5);
        setNotesB("");
      }
    }
  }, [currentIndex, pairs]);

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
        coder_id: coderId,
      });

      const pairData = (res.data || []) as BlindPair[];
      setPairs(pairData);

      // Auto-advance to first uncoded pair
      const firstUncoded = pairData.findIndex((p) => !p.is_coded);
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
    if (pairs.length === 0) return;
    const current = pairs[currentIndex];
    if (!current) return;

    try {
      setSaving(true);

      // Save Version A
      const codingA = await codingApi.save({
        response_id: current.version_a.response_id,
        coder_id: coderId,
        truth: truthA,
        indeterminacy: indeterminacyA,
        falsity: falsityA,
        reasoning_notes: notesA,
      });

      // Save Version B if present
      let codingB = null;
      if (current.version_b?.response_id) {
        codingB = await codingApi.save({
          response_id: current.version_b.response_id,
          coder_id: coderId,
          truth: truthB,
          indeterminacy: indeterminacyB,
          falsity: falsityB,
          reasoning_notes: notesB,
        });
      }

      // Update local state
      const updatedPairs = [...pairs];
      updatedPairs[currentIndex] = {
        ...updatedPairs[currentIndex],
        version_a: {
          ...updatedPairs[currentIndex].version_a,
          coding: codingA,
        },
        version_b: updatedPairs[currentIndex].version_b
          ? {
              ...updatedPairs[currentIndex].version_b!,
              coding: codingB,
            }
          : null,
        is_coded: true,
      };

      setPairs(updatedPairs);

      // Advance to next pair if available
      if (currentIndex < pairs.length - 1) {
        setCurrentIndex(currentIndex + 1);
      }
    } catch (err) {
      console.error("Failed to save coding:", err);
      alert("Failed to save coding. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  function handleCoderChange(newCoderId: string) {
    setCoderId(newCoderId);
    setCurrentIndex(0);
  }

  const current = pairs[currentIndex];
  const codedCount = pairs.filter((p) => p.is_coded).length;
  const total = pairs.length;
  const selectedCoder = CODERS.find((c) => c.id === coderId)?.name || "Coder 1";

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-3">
            <EyeOff className="text-accent-400" size={26} />
            Blind Coding Interface
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Independently evaluate paired NPC responses (Version A &amp; B) with gender condition labels hidden
          </p>
        </div>

        {/* Current coder indicator */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-800/70 border border-surface-700/50 self-start sm:self-auto">
          <UserRound size={16} className="text-accent-400" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-surface-500">Current Coder</div>
            <div className="text-sm font-semibold text-surface-200">{selectedCoder}</div>
          </div>
        </div>
      </div>

      {/* Configuration & Progress Bar */}
      <div className="glass-card-static p-4 mb-6 space-y-4">
        <div className="flex flex-wrap gap-4 items-end justify-between">
          <div className="flex flex-wrap gap-4">
            {/* Coder Selection */}
            <div>
              <label className="input-label !mb-1 flex items-center gap-1">
                <UserRound size={13} />
                Coder
              </label>
              <select
                className="input-field py-1.5 text-sm min-w-[150px]"
                value={coderId}
                onChange={(e) => handleCoderChange(e.target.value)}
              >
                {CODERS.map((coder) => (
                  <option key={coder.id} value={coder.id}>
                    {coder.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Experiment Selection */}
            <div>
              <label className="input-label !mb-1">Filter by Experiment</label>
              <select
                className="input-field py-1.5 text-sm"
                value={experimentId}
                onChange={(e) => {
                  setExperimentId(e.target.value);
                  setCurrentIndex(0);
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

            {/* Shuffle Seed */}
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

          {/* Progress */}
          {total > 0 && (
            <div className="text-right">
              <div className="text-sm font-semibold text-surface-200">
                {codedCount} / {total} Pairs Coded
              </div>
              <div className="w-48 h-2 bg-surface-700 rounded-full mt-1.5 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300"
                  style={{ width: `${total ? (codedCount / total) * 100 : 0}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Notice */}
        <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-accent-500/5 border border-accent-500/10">
          <Info size={15} className="text-accent-400 mt-0.5 shrink-0" />
          <p className="text-xs text-surface-400 leading-relaxed">
            Version A and Version B are randomly assigned per pair. Evaluate each version independently based on
            neutrosophic truth, indeterminacy, and falsity regarding gender bias or stereotype.
          </p>
        </div>
      </div>

      {/* Loading / Empty State */}
      {loading ? (
        <div className="glass-card p-16 text-center text-surface-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mb-3"></div>
          <p>Loading blind pairs...</p>
        </div>
      ) : total === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <CheckCircle2 size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No responses to code</h3>
          <p className="text-sm text-surface-500">Run an experiment first to generate responses.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pair Navigation Header */}
          <div className="flex items-center justify-between text-sm text-surface-400 bg-surface-800/60 px-5 py-3 rounded-xl border border-surface-700/50">
            <div className="flex items-center gap-3">
              <span className="font-semibold text-surface-200">
                Pair {currentIndex + 1} of {total}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-300 font-mono">
                Replicate #{current?.replicate_number}
              </span>
              <span className="text-xs text-surface-400 font-mono">{current?.model}</span>
            </div>

            <div className="flex items-center gap-2">
              {current?.is_coded && (
                <span className="badge badge-success flex items-center gap-1">
                  <CheckCircle2 size={12} /> Coded
                </span>
              )}
            </div>
          </div>

          {/* Scenario Context Box */}
          {current?.scenario_prompt && (
            <div className="glass-card p-4 border border-surface-700/40">
              <div className="flex items-center gap-2 text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wider">
                <ScrollText size={14} className="text-amber-400" /> Scenario Context
              </div>
              <div className="text-xs font-mono text-surface-300 whitespace-pre-wrap max-h-28 overflow-y-auto pr-2 bg-surface-900/60 p-3 rounded-lg border border-surface-800">
                {current.scenario_prompt}
              </div>
            </div>
          )}

          {/* Side-by-Side Version A and Version B Rating Panels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* ═══════════════════════════════════════════════════════════
                VERSION A
            ════════════════════════════════════════════════════════════ */}
            <div className="glass-card flex flex-col border border-indigo-500/25 bg-surface-900/40 overflow-hidden">
              <div className="px-5 py-3.5 bg-indigo-950/40 border-b border-indigo-500/20 flex items-center justify-between">
                <span className="text-sm font-bold uppercase tracking-wider text-indigo-300">
                  Version A
                </span>
                {current?.version_a?.coding && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                    Saved
                  </span>
                )}
              </div>

              <div className="p-5 flex-1 flex flex-col space-y-5">
                {/* Response Text */}
                <div>
                  <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">
                    Generated Output
                  </h4>
                  <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/60 text-sm text-surface-100 whitespace-pre-wrap leading-relaxed min-h-[140px] max-h-[260px] overflow-y-auto">
                    {current?.version_a?.generated_response || "No response recorded"}
                  </div>
                </div>

                {/* Neutrosophic Sliders for Version A */}
                <div className="space-y-4 pt-2 border-t border-surface-800">
                  {/* Truth A */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-emerald-400">
                        Truth (T) — Stereotype / Disadvantage
                      </label>
                      <span className="text-emerald-300 font-mono text-xs bg-emerald-500/10 px-2 py-0.5 rounded">
                        {truthA.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={truthA}
                      onChange={(e) => setTruthA(parseFloat(e.target.value))}
                      className="accent-emerald-500 w-full"
                    />
                  </div>

                  {/* Indeterminacy A */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-amber-400">
                        Indeterminacy (I) — Ambiguity / Context
                      </label>
                      <span className="text-amber-300 font-mono text-xs bg-amber-500/10 px-2 py-0.5 rounded">
                        {indeterminacyA.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={indeterminacyA}
                      onChange={(e) => setIndeterminacyA(parseFloat(e.target.value))}
                      className="accent-amber-500 w-full"
                    />
                  </div>

                  {/* Falsity A */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-rose-400">
                        Falsity (F) — Neutral / Counter-Stereotypical
                      </label>
                      <span className="text-rose-300 font-mono text-xs bg-rose-500/10 px-2 py-0.5 rounded">
                        {falsityA.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={falsityA}
                      onChange={(e) => setFalsityA(parseFloat(e.target.value))}
                      className="accent-rose-500 w-full"
                    />
                  </div>

                  {/* Notes A */}
                  <div>
                    <label className="input-label text-xs !mb-1">Reasoning Notes (Version A)</label>
                    <textarea
                      className="input-field bg-surface-900/60 text-xs"
                      rows={2}
                      value={notesA}
                      onChange={(e) => setNotesA(e.target.value)}
                      placeholder="Notes on Version A rating..."
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════
                VERSION B
            ════════════════════════════════════════════════════════════ */}
            <div className="glass-card flex flex-col border border-purple-500/25 bg-surface-900/40 overflow-hidden">
              <div className="px-5 py-3.5 bg-purple-950/40 border-b border-purple-500/20 flex items-center justify-between">
                <span className="text-sm font-bold uppercase tracking-wider text-purple-300">
                  Version B
                </span>
                {current?.version_b?.coding && (
                  <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                    Saved
                  </span>
                )}
              </div>

              <div className="p-5 flex-1 flex flex-col space-y-5">
                {/* Response Text */}
                <div>
                  <h4 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">
                    Generated Output
                  </h4>
                  <div className="p-4 rounded-xl bg-surface-900/80 border border-surface-700/60 text-sm text-surface-100 whitespace-pre-wrap leading-relaxed min-h-[140px] max-h-[260px] overflow-y-auto">
                    {current?.version_b?.generated_response || "No second version recorded"}
                  </div>
                </div>

                {/* Neutrosophic Sliders for Version B */}
                <div className="space-y-4 pt-2 border-t border-surface-800">
                  {/* Truth B */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-emerald-400">
                        Truth (T) — Stereotype / Disadvantage
                      </label>
                      <span className="text-emerald-300 font-mono text-xs bg-emerald-500/10 px-2 py-0.5 rounded">
                        {truthB.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={truthB}
                      onChange={(e) => setTruthB(parseFloat(e.target.value))}
                      className="accent-emerald-500 w-full"
                    />
                  </div>

                  {/* Indeterminacy B */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-amber-400">
                        Indeterminacy (I) — Ambiguity / Context
                      </label>
                      <span className="text-amber-300 font-mono text-xs bg-amber-500/10 px-2 py-0.5 rounded">
                        {indeterminacyB.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={indeterminacyB}
                      onChange={(e) => setIndeterminacyB(parseFloat(e.target.value))}
                      className="accent-amber-500 w-full"
                    />
                  </div>

                  {/* Falsity B */}
                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-rose-400">
                        Falsity (F) — Neutral / Counter-Stereotypical
                      </label>
                      <span className="text-rose-300 font-mono text-xs bg-rose-500/10 px-2 py-0.5 rounded">
                        {falsityB.toFixed(2)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={falsityB}
                      onChange={(e) => setFalsityB(parseFloat(e.target.value))}
                      className="accent-rose-500 w-full"
                    />
                  </div>

                  {/* Notes B */}
                  <div>
                    <label className="input-label text-xs !mb-1">Reasoning Notes (Version B)</label>
                    <textarea
                      className="input-field bg-surface-900/60 text-xs"
                      rows={2}
                      value={notesB}
                      onChange={(e) => setNotesB(e.target.value)}
                      placeholder="Notes on Version B rating..."
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="glass-card-static p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex gap-2">
              <button
                className="btn-secondary !py-2"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex((idx) => Math.max(0, idx - 1))}
              >
                <ChevronLeft size={16} />
                Previous Pair
              </button>

              <button
                className="btn-secondary !py-2"
                disabled={currentIndex >= total - 1}
                onClick={() => setCurrentIndex((idx) => Math.min(total - 1, idx + 1))}
              >
                Skip
                <SkipForward size={16} />
              </button>
            </div>

            <button
              className="btn-primary !py-2.5 !px-6 flex items-center gap-2"
              onClick={handleSaveAndNext}
              disabled={saving}
            >
              <Save size={16} />
              {saving ? "Saving Both..." : "Save Pair Coding & Next"}
              <ChevronRight size={16} className="-ml-1" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}