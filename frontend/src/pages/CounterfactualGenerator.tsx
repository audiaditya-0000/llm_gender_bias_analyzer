import { useState, useEffect } from "react";
import {
  GitCompareArrows,
  Copy,
  Check,
  ArrowRightLeft,
  Plus,
  Trash2,
  Settings,
} from "lucide-react";
import { counterfactualApi } from "../api/client";
import type { CounterfactualResponse, WordPair } from "../types";


export default function CounterfactualGenerator() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<CounterfactualResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedMale, setCopiedMale] = useState(false);
  const [copiedFemale, setCopiedFemale] = useState(false);
  const [showWordPairs, setShowWordPairs] = useState(false);
  const [wordPairs, setWordPairs] = useState<WordPair[]>([]);
  const [newPair, setNewPair] = useState({ male_term: "", female_term: "" });

  useEffect(() => {
    if (showWordPairs) loadWordPairs();
  }, [showWordPairs]);

  async function loadWordPairs() {
    try {
      const pairs = await counterfactualApi.listWordPairs();
      setWordPairs(pairs);
    } catch (err) {
      console.error("Failed to load word pairs:", err);
    }
  }

  async function handleGenerate() {
    if (!prompt.trim()) return;
    try {
      setLoading(true);
      const data = await counterfactualApi.generate({ prompt });
      setResult(data);
    } catch (err) {
      console.error("Failed to generate:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(text: string, which: "male" | "female") {
    await navigator.clipboard.writeText(text);
    if (which === "male") {
      setCopiedMale(true);
      setTimeout(() => setCopiedMale(false), 2000);
    } else {
      setCopiedFemale(true);
      setTimeout(() => setCopiedFemale(false), 2000);
    }
  }

  async function handleAddPair() {
    if (!newPair.male_term.trim() || !newPair.female_term.trim()) return;
    try {
      await counterfactualApi.addWordPair(newPair);
      setNewPair({ male_term: "", female_term: "" });
      loadWordPairs();
    } catch (err) {
      console.error("Failed to add pair:", err);
    }
  }

  async function handleDeletePair(id: string) {
    try {
      await counterfactualApi.deleteWordPair(id);
      loadWordPairs();
    } catch (err) {
      console.error("Failed to delete pair:", err);
    }
  }

  function highlightDifferences(text: string, swaps: CounterfactualResponse["swaps_made"]) {
    let highlighted = text;
    const swappedTerms = swaps.map((s) => s.replaced_with);
    for (const term of swappedTerms) {
      const regex = new RegExp(`\\b(${term})\\b`, "gi");
      highlighted = highlighted.replace(regex, `<mark class="bg-accent-500/30 text-accent-300 px-0.5 rounded">$1</mark>`);
    }
    return highlighted;
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Counterfactual Generator</h1>
          <p className="text-sm text-surface-400 mt-1">
            Generate matched male/female prompt pairs with minimal differences
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => setShowWordPairs(!showWordPairs)}
        >
          <Settings size={16} />
          Word Pairs
        </button>
      </div>

      {/* Word Pairs Panel */}
      {showWordPairs && (
        <div className="glass-card-static p-5 mb-6 animate-slide-up">
          <h3 className="text-sm font-semibold text-surface-200 mb-4">
            Gendered Word Pairs ({wordPairs.length})
          </h3>
          <div className="max-h-60 overflow-y-auto mb-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {wordPairs.map((pair, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 text-xs bg-surface-800/60 rounded-lg px-3 py-2"
                >
                  <span className="text-blue-400">{pair.male_term}</span>
                  <ArrowRightLeft size={10} className="text-surface-600" />
                  <span className="text-pink-400">{pair.female_term}</span>
                  {!pair.builtin && pair.id && (
                    <button
                      className="btn-icon ml-auto !p-0.5"
                      onClick={() => handleDeletePair(pair.id!)}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <input
              className="input-field flex-1"
              placeholder="Male term"
              value={newPair.male_term}
              onChange={(e) => setNewPair({ ...newPair, male_term: e.target.value })}
            />
            <ArrowRightLeft size={16} className="text-surface-500 shrink-0" />
            <input
              className="input-field flex-1"
              placeholder="Female term"
              value={newPair.female_term}
              onChange={(e) => setNewPair({ ...newPair, female_term: e.target.value })}
            />
            <button className="btn-primary shrink-0" onClick={handleAddPair}>
              <Plus size={14} />
              Add
            </button>
          </div>
        </div>
      )}

      {/* Input Section */}
      <div className="glass-card-static p-6 mb-6">

        <div className="mb-4">
          <label className="input-label">Base Prompt</label>
          <textarea
            className="input-field"
            rows={6}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter a prompt containing gendered terms. For example:&#10;&#10;You are a male shopkeeper in a medieval fantasy town. He greets the customer warmly and offers his finest wares."
          />
        </div>

        <button
          className="btn-primary"
          onClick={handleGenerate}
          disabled={loading || !prompt.trim()}
        >
          <GitCompareArrows size={16} />
          {loading ? "Generating..." : "Generate Counterfactual Pair"}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-up">
          {/* Male Prompt */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-400" />
                <h3 className="text-sm font-semibold text-blue-300">Male Prompt</h3>
              </div>
              <button
                className="btn-icon"
                onClick={() => handleCopy(result.male_prompt, "male")}
                title="Copy"
              >
                {copiedMale ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </div>
            <div
              className="text-sm text-surface-300 leading-relaxed font-mono bg-surface-800/60 rounded-lg p-4 whitespace-pre-wrap"
              dangerouslySetInnerHTML={{
                __html: highlightDifferences(result.male_prompt, result.swaps_made),
              }}
            />
          </div>

          {/* Female Prompt */}
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-pink-400" />
                <h3 className="text-sm font-semibold text-pink-300">Female Prompt</h3>
              </div>
              <button
                className="btn-icon"
                onClick={() => handleCopy(result.female_prompt, "female")}
                title="Copy"
              >
                {copiedFemale ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
              </button>
            </div>
            <div
              className="text-sm text-surface-300 leading-relaxed font-mono bg-surface-800/60 rounded-lg p-4 whitespace-pre-wrap"
              dangerouslySetInnerHTML={{
                __html: highlightDifferences(result.female_prompt, result.swaps_made),
              }}
            />
          </div>

          {/* Swap Summary */}
          {result.swaps_made.length > 0 && (
            <div className="lg:col-span-2 glass-card-static p-5">
              <h3 className="text-sm font-semibold text-surface-200 mb-3">
                Swaps Made ({result.swaps_made.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.swaps_made.map((swap, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-xs bg-surface-800/60 rounded-lg px-3 py-2"
                  >
                    <span className="text-surface-400 font-mono">{swap.original}</span>
                    <ArrowRightLeft size={10} className="text-accent-400" />
                    <span className="text-accent-300 font-mono">{swap.replaced_with}</span>
                    <span className="text-surface-600">×{swap.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
