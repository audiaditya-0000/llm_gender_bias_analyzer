import { useState } from "react";
import { Download, Database, Settings, Activity, FileText, CheckCircle2 } from "lucide-react";
import { exportApi } from "../api/client";

export default function ExportPage() {
  const [downloading, setDownloading] = useState(false);

  function handleDownload() {
    setDownloading(true);
    // Trigger download by setting window location or opening in hidden iframe
    const link = document.createElement("a");
    link.href = exportApi.downloadUrl();
    link.download = "export.zip"; // Actual name is set by Content-Disposition header
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => setDownloading(false), 2000);
  }

  return (
    <div className="animate-fade-in max-w-4xl mx-auto">
      <div className="text-center mb-10">
        <div className="w-16 h-16 rounded-2xl gradient-accent flex items-center justify-center mx-auto mb-4 shadow-lg shadow-accent-500/20">
          <Download size={32} className="text-white" />
        </div>
        <h1 className="text-3xl font-bold text-surface-50 mb-2">Export Data</h1>
        <p className="text-surface-400">
          Download all experiment data, coding, and analysis summaries as a ZIP archive for external use.
        </p>
      </div>

      <div className="glass-card-static p-8 relative overflow-hidden">
        {/* Decorative background elements */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-accent-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <h2 className="text-xl font-bold text-surface-50 mb-6">Archive Contents</h2>
          
          <div className="grid sm:grid-cols-2 gap-4 mb-8">
            <div className="bg-surface-800/80 rounded-xl p-4 flex items-start gap-4 border border-surface-700/50">
              <Settings className="text-blue-400 shrink-0" />
              <div>
                <h4 className="font-semibold text-surface-200">Configurations</h4>
                <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                  scenarios.json<br />
                  scaffolds.json<br />
                  experiments.json
                </p>
              </div>
            </div>
            
            <div className="bg-surface-800/80 rounded-xl p-4 flex items-start gap-4 border border-surface-700/50">
              <Database className="text-emerald-400 shrink-0" />
              <div>
                <h4 className="font-semibold text-surface-200">Raw Data</h4>
                <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                  responses.json<br />
                  coding.json<br />
                  custom_word_pairs.json
                </p>
              </div>
            </div>

            <div className="bg-surface-800/80 rounded-xl p-4 flex items-start gap-4 border border-surface-700/50 sm:col-span-2">
              <Activity className="text-accent-400 shrink-0" />
              <div>
                <h4 className="font-semibold text-surface-200">Computed Analysis</h4>
                <p className="text-xs text-surface-400 mt-1 leading-relaxed">
                  analysis/summary.json (Aggregate metrics)<br />
                  analysis/per_experiment.json (Metrics split by experiment)
                </p>
              </div>
            </div>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-8 flex gap-3">
            <FileText className="text-amber-400 shrink-0" />
            <div className="text-sm text-surface-300">
              <strong className="text-amber-300 block mb-1">JSON Format</strong>
              All files are exported in standard UTF-8 JSON format, ready to be imported into Python (Pandas), R, or other data analysis tools.
            </div>
          </div>

          <div className="flex justify-center">
            <button
              className="btn-primary px-8 py-3 text-base"
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Generating Archive...
                </>
              ) : (
                <>
                  <Download size={20} />
                  Download ZIP Archive
                </>
              )}
            </button>
          </div>
          
          {downloading && (
             <div className="text-center mt-4 text-sm text-emerald-400 flex items-center justify-center gap-2 animate-fade-in">
               <CheckCircle2 size={16} /> Download initiated
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
