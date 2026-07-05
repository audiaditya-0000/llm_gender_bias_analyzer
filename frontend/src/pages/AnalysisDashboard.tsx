import { useState, useEffect, useMemo } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar, Radar } from "react-chartjs-2";
import { Scale, BarChart3, PieChart, Info } from "lucide-react";
import { analysisApi, experimentsApi } from "../api/client";
import type { AnalysisSummary, Experiment } from "../types";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend
);

// Chart options to match dark theme
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: "#cbd5e1" },
    },
    tooltip: {
      backgroundColor: "rgba(15, 23, 42, 0.9)",
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
      borderColor: "rgba(148, 163, 184, 0.2)",
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      grid: { color: "rgba(148, 163, 184, 0.1)" },
      ticks: { color: "#94a3b8" },
    },
    y: {
      grid: { color: "rgba(148, 163, 184, 0.1)" },
      ticks: { color: "#94a3b8" },
      min: 0,
      max: 1,
    },
  },
};

const radarOptions = {
  ...chartOptions,
  scales: {
    r: {
      grid: { color: "rgba(148, 163, 184, 0.2)" },
      angleLines: { color: "rgba(148, 163, 184, 0.2)" },
      pointLabels: { color: "#94a3b8" },
      ticks: { display: false, min: 0, max: 1 },
    },
  },
};

export default function AnalysisDashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [experimentId, setExperimentId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadExperiments();
  }, []);

  useEffect(() => {
    loadAnalysis();
  }, [experimentId]);

  async function loadExperiments() {
    try {
      const data = await experimentsApi.list();
      setExperiments(data);
    } catch (err) {
      console.error("Failed to load experiments:", err);
    }
  }

  async function loadAnalysis() {
    try {
      setLoading(true);
      const data = await analysisApi.summary(experimentId || undefined);
      setSummary(data);
    } catch (err) {
      console.error("Failed to load analysis:", err);
    } finally {
      setLoading(false);
    }
  }

  const barData = useMemo(() => {
    if (!summary) return null;
    return {
      labels: ["Truth (T)", "Indeterminacy (I)", "Falsity (F)"],
      datasets: [
        {
          label: "Male Condition",
          data: [
            summary.male.avg_truth,
            summary.male.avg_indeterminacy,
            summary.male.avg_falsity,
          ],
          backgroundColor: "rgba(99, 102, 241, 0.8)", // Indigo
          borderColor: "rgb(99, 102, 241)",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Female Condition",
          data: [
            summary.female.avg_truth,
            summary.female.avg_indeterminacy,
            summary.female.avg_falsity,
          ],
          backgroundColor: "rgba(244, 63, 94, 0.8)", // Rose
          borderColor: "rgb(244, 63, 94)",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    };
  }, [summary]);

  const radarData = useMemo(() => {
    if (!summary) return null;
    return {
      labels: ["Truth (T)", "Indeterminacy (I)", "Falsity (F)"],
      datasets: [
        {
          label: "Male Condition",
          data: [
            summary.male.avg_truth,
            summary.male.avg_indeterminacy,
            summary.male.avg_falsity,
          ],
          backgroundColor: "rgba(99, 102, 241, 0.2)",
          borderColor: "rgb(99, 102, 241)",
          pointBackgroundColor: "rgb(99, 102, 241)",
          borderWidth: 2,
        },
        {
          label: "Female Condition",
          data: [
            summary.female.avg_truth,
            summary.female.avg_indeterminacy,
            summary.female.avg_falsity,
          ],
          backgroundColor: "rgba(244, 63, 94, 0.2)",
          borderColor: "rgb(244, 63, 94)",
          pointBackgroundColor: "rgb(244, 63, 94)",
          borderWidth: 2,
        },
      ],
    };
  }, [summary]);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-2">
            <BarChart3 className="text-accent-400" />
            Analysis Dashboard
          </h1>
          <p className="text-sm text-surface-400 mt-1">
            Analyze neutrosophic bias metrics across coded responses
          </p>
        </div>
      </div>

      <div className="glass-card-static p-4 mb-8">
        <label className="input-label !mb-1">Filter by Experiment</label>
        <select
          className="input-field py-2 max-w-md"
          value={experimentId}
          onChange={(e) => setExperimentId(e.target.value)}
        >
          <option value="">Aggregate All Experiments</option>
          {experiments.map((e) => (
            <option key={e.id} value={e.id}>
              {e.model} ({new Date(e.created_at).toLocaleDateString()})
            </option>
          ))}
        </select>
      </div>

      {loading || !summary ? (
        <div className="text-center py-20 text-surface-500">Loading analysis...</div>
      ) : summary.total_coded === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <PieChart size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No coded data</h3>
          <p className="text-sm text-surface-500">
            Use the Blind Coding interface to code responses before analyzing.
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Summary Cards */}
          <div className="lg:col-span-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up">
            <div className="glass-card p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 opacity-10 text-emerald-400">
                <BarChart3 size={48} />
              </div>
              <h3 className="text-sm font-semibold text-surface-400 mb-1">Coded Responses</h3>
              <div className="text-3xl font-bold text-surface-50">
                {summary.total_coded} <span className="text-sm font-normal text-surface-500">/ {summary.total_responses}</span>
              </div>
            </div>

            <div className="glass-card p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 opacity-10 text-accent-400">
                <Scale size={48} />
              </div>
              <h3 className="text-sm font-semibold text-surface-400 mb-1 flex items-center gap-1">
                Bias Score 
                <div className="tooltip" data-tooltip="| avg Truth Male - avg Truth Female |">
                  <Info size={12} className="text-surface-500 cursor-help" />
                </div>
              </h3>
              <div className="text-3xl font-bold text-accent-300">
                {summary.bias_score.toFixed(3)}
              </div>
              <div className="text-xs text-surface-500 mt-2">
                Closer to 0 indicates less gender bias
              </div>
            </div>

            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-surface-400 mb-3">Avg Truth (T)</h3>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">Male</div>
                  <div className="text-xl font-bold text-indigo-400">{summary.male.avg_truth.toFixed(3)}</div>
                </div>
                <div className="w-px h-8 bg-surface-700"></div>
                <div className="text-right">
                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">Female</div>
                  <div className="text-xl font-bold text-rose-400">{summary.female.avg_truth.toFixed(3)}</div>
                </div>
              </div>
            </div>
            
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-surface-400 mb-3">Avg Falsity (F)</h3>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">Male</div>
                  <div className="text-xl font-bold text-indigo-400">{summary.male.avg_falsity.toFixed(3)}</div>
                </div>
                <div className="w-px h-8 bg-surface-700"></div>
                <div className="text-right">
                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">Female</div>
                  <div className="text-xl font-bold text-rose-400">{summary.female.avg_falsity.toFixed(3)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="lg:col-span-3 glass-card p-6 min-h-[400px] animate-slide-up" style={{ animationDelay: "100ms" }}>
            <h3 className="text-base font-semibold text-surface-100 mb-6 text-center">
              Condition Comparison (Averages)
            </h3>
            {barData && <Bar data={barData} options={chartOptions} />}
          </div>

          <div className="lg:col-span-1 glass-card p-6 min-h-[400px] flex flex-col animate-slide-up" style={{ animationDelay: "150ms" }}>
            <h3 className="text-base font-semibold text-surface-100 mb-2 text-center">
              Neutrosophic Profile
            </h3>
            <div className="flex-1 min-h-0">
              {radarData && <Radar data={radarData} options={radarOptions} />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
