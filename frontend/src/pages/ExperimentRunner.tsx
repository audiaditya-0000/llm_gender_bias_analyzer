import { useState, useEffect } from "react";
import { Play, Activity, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { experimentsApi, scenariosApi, scaffoldsApi, runnerApi } from "../api/client";
import type { Experiment, Scenario, Scaffold } from "../types";

export default function ExperimentRunner() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scaffolds, setScaffolds] = useState<Scaffold[]>([]);
  const [loading, setLoading] = useState(true);
  const [progressData, setProgressData] = useState<Record<string, { completed: number; total: number; status: string }>>({});

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    // Poll progress for running experiments
    const runningExps = experiments.filter((e) => e.status === "running" || progressData[e.id]?.status === "running");
    if (runningExps.length === 0) return;

    const interval = setInterval(() => {
      runningExps.forEach(async (exp) => {
        try {
          const res = await runnerApi.status(exp.id);
          setProgressData((prev) => ({ ...prev, [exp.id]: res }));
          
          if (res.status !== "running") {
            // Refresh to get final status if it stopped running
            loadAll();
          }
        } catch (err) {
          console.error(`Failed to poll status for ${exp.id}:`, err);
        }
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [experiments, progressData]);

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
      
      // Load initial progress for all running experiments
      expData.forEach(async (exp) => {
        if (exp.status === "running") {
          try {
            const res = await runnerApi.status(exp.id);
            setProgressData((prev) => ({ ...prev, [exp.id]: res }));
          } catch (err) {
            // Ignore
          }
        }
      });
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStart(id: string) {
    try {
      // Optimistically update React state immediately so Running badge and progress appear instantly
      setExperiments((prev) =>
        prev.map((e) => (e.id === id ? { ...e, status: "running" } : e))
      );
      const targetExp = experiments.find((e) => e.id === id);
      const totalCalls = targetExp ? targetExp.num_replicates * 2 : 40;
      setProgressData((prev) => ({
        ...prev,
        [id]: { completed: 0, total: totalCalls, status: "running" },
      }));

      await runnerApi.start(id);
      loadAll();
    } catch (err: any) {
      alert(`Failed to start experiment: ${err.message}`);
      loadAll();
    }
  }

  if (loading && experiments.length === 0) {
    return <div className="text-center py-20 text-surface-500">Loading...</div>;
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-surface-50">Experiment Runner</h1>
          <p className="text-sm text-surface-400 mt-1">
            Execute configured experiments and track progress
          </p>
        </div>
      </div>

      {experiments.length === 0 ? (
        <div className="glass-card-static p-12 text-center">
          <Play size={40} className="mx-auto text-surface-600 mb-4" />
          <h3 className="text-lg font-semibold text-surface-300 mb-2">No experiments ready</h3>
          <p className="text-sm text-surface-500 mb-6">
            Configure an experiment first to run it here.
          </p>
        </div>
      ) : (
        <div className="grid gap-6">
          {experiments.map((exp) => {
            const scenario = scenarios.find((s) => s.id === exp.scenario_id);
            const scaffold = scaffolds.find((s) => s.id === exp.scaffold_id);
            const prog = progressData[exp.id];
            const isRunning = prog?.status === "running" || exp.status === "running";
            
            let percent = 0;
            if (prog && prog.total > 0) {
              percent = Math.round((prog.completed / prog.total) * 100);
            } else if (exp.status === "completed") {
              percent = 100;
            }

            return (
              <div key={exp.id} className="glass-card p-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-base font-semibold text-surface-100">
                        {scenario?.title || "Unknown Scenario"}
                      </h3>
                      <span className="badge badge-info">{exp.model}</span>
                      {exp.status === "completed" && <span className="badge badge-success">Completed</span>}
                      {exp.status === "failed" && <span className="badge badge-error">Failed</span>}
                      {isRunning && <span className="badge badge-warning">Running</span>}
                      {exp.status === "configured" && !isRunning && <span className="badge badge-neutral">Ready</span>}
                    </div>
                    <div className="text-sm text-surface-400 space-y-1">
                      <div>Scaffold: {scaffold?.name || "Unknown"}</div>
                      <div>
                        Conditions: 2 (Original / Swapped) × {exp.num_replicates} replicates = {exp.num_replicates * 2} total calls
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-3 min-w-[200px]">
                    <button
                      className="btn-primary w-full justify-center"
                      onClick={() => handleStart(exp.id)}
                      disabled={isRunning || exp.status === "completed"}
                    >
                      {isRunning ? (
                        <>
                          <Activity size={16} className="animate-pulse" />
                          Running...
                        </>
                      ) : exp.status === "completed" ? (
                        <>
                          <CheckCircle2 size={16} />
                          Completed
                        </>
                      ) : exp.status === "failed" ? (
                        <>
                          <AlertCircle size={16} />
                          Retry
                        </>
                      ) : (
                        <>
                          <Play size={16} />
                          Start Run
                        </>
                      )}
                    </button>
                    
                    {/* Progress Bar */}
                    {(isRunning || percent > 0) && (
                      <div className="w-full">
                        <div className="flex justify-between text-xs text-surface-400 mb-1">
                          <span>Progress</span>
                          <span>{percent}%</span>
                        </div>
                        <div className="progress-bar">
                          <div className="progress-fill" style={{ width: `${percent}%` }} />
                        </div>
                        {isRunning && prog && (
                          <div className="text-[10px] text-surface-500 text-right mt-1 flex items-center justify-end gap-1">
                            <Clock size={10} />
                            {prog.completed} / {prog.total} calls
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
