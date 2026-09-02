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
import {
  Scale,
  BarChart3,
  PieChart,
  Info,
  Users,
  CheckCircle2,
  AlertTriangle,
  Database,
  FileCheck2,
  FlaskConical,
} from "lucide-react";

import { analysisApi, experimentsApi } from "../api/client";

import type {
  AnalysisSummary,
  Experiment,
  InterRaterReliability,
} from "../types";


/* =========================================================
   CHART.JS REGISTRATION
========================================================= */

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


/* =========================================================
   CHART OPTIONS
========================================================= */

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,

  plugins: {
    legend: {
      labels: {
        color: "#cbd5e1",
      },
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
      grid: {
        color: "rgba(148, 163, 184, 0.1)",
      },

      ticks: {
        color: "#94a3b8",
      },
    },

    y: {
      grid: {
        color: "rgba(148, 163, 184, 0.1)",
      },

      ticks: {
        color: "#94a3b8",
      },

      min: 0,
      max: 1,
    },
  },
};


const radarOptions = {
  ...chartOptions,

  scales: {
    r: {
      grid: {
        color: "rgba(148, 163, 184, 0.2)",
      },

      angleLines: {
        color: "rgba(148, 163, 184, 0.2)",
      },

      pointLabels: {
        color: "#94a3b8",
      },

      ticks: {
        display: false,
        min: 0,
        max: 1,
      },
    },
  },
};


/* =========================================================
   COMPONENT
========================================================= */

export default function AnalysisDashboard() {

  const [experiments, setExperiments] =
    useState<Experiment[]>([]);

  const [summary, setSummary] =
    useState<AnalysisSummary | null>(null);

  const [reliability, setReliability] =
    useState<InterRaterReliability | null>(null);

  const [experimentId, setExperimentId] =
    useState("");

  const [coder1, setCoder1] =
    useState("coder_1");

  const [coder2, setCoder2] =
    useState("coder_2");

  const [loading, setLoading] =
    useState(true);

  const [reliabilityLoading, setReliabilityLoading] =
    useState(false);


  /* =========================================================
     LOAD EXPERIMENTS
  ========================================================= */

  useEffect(() => {
    loadExperiments();
  }, []);


  /* =========================================================
     LOAD ANALYSIS
  ========================================================= */

  useEffect(() => {
    loadAnalysis();
  }, [experimentId]);


  /* =========================================================
     LOAD INTER-RATER RELIABILITY
  ========================================================= */

  useEffect(() => {
    loadReliability();
  }, [experimentId, coder1, coder2]);


  /* =========================================================
     API FUNCTIONS
  ========================================================= */

  async function loadExperiments() {

    try {

      const data = await experimentsApi.list();

      setExperiments(data);

    } catch (err) {

      console.error(
        "Failed to load experiments:",
        err
      );

    }
  }


  async function loadAnalysis() {

    try {

      setLoading(true);

      const data = await analysisApi.summary(
        experimentId || undefined
      );

      setSummary(data);

    } catch (err) {

      console.error(
        "Failed to load analysis:",
        err
      );

      setSummary(null);

    } finally {

      setLoading(false);

    }
  }


  async function loadReliability() {

    try {

      setReliabilityLoading(true);

      const data = await analysisApi.interRater(
        experimentId || undefined,
        coder1,
        coder2
      );

      setReliability(data);

    } catch (err) {

      console.error(
        "Failed to load inter-rater reliability:",
        err
      );

      setReliability(null);

    } finally {

      setReliabilityLoading(false);

    }
  }


  /* =========================================================
     BAR CHART DATA
  ========================================================= */

  const barData = useMemo(() => {

    if (!summary) return null;

    return {

      labels: [
        "Stereotype / Disadvantage (T)",
        "Ambiguity / Context (I)",
        "Neutral / Counter-stereotypical (F)",
      ],

      datasets: [

        {
          label: "Male Condition",

          data: [
            summary.male.avg_T,
            summary.male.avg_I,
            summary.male.avg_F,
          ],

          backgroundColor:
            "rgba(99, 102, 241, 0.8)",

          borderColor:
            "rgb(99, 102, 241)",

          borderWidth: 1,

          borderRadius: 4,
        },


        {
          label: "Female Condition",

          data: [
            summary.female.avg_T,
            summary.female.avg_I,
            summary.female.avg_F,
          ],

          backgroundColor:
            "rgba(244, 63, 94, 0.8)",

          borderColor:
            "rgb(244, 63, 94)",

          borderWidth: 1,

          borderRadius: 4,
        },

      ],
    };

  }, [summary]);


  /* =========================================================
     RADAR CHART DATA
  ========================================================= */

  const radarData = useMemo(() => {

    if (!summary) return null;

    return {

      labels: [
        "Stereotype / Disadvantage (T)",
        "Ambiguity / Context (I)",
        "Neutral / Counter-stereotypical (F)",
      ],

      datasets: [

        {
          label: "Male Condition",

          data: [
            summary.male.avg_T,
            summary.male.avg_I,
            summary.male.avg_F,
          ],

          backgroundColor:
            "rgba(99, 102, 241, 0.2)",

          borderColor:
            "rgb(99, 102, 241)",

          pointBackgroundColor:
            "rgb(99, 102, 241)",

          borderWidth: 2,
        },


        {
          label: "Female Condition",

          data: [
            summary.female.avg_T,
            summary.female.avg_I,
            summary.female.avg_F,
          ],

          backgroundColor:
            "rgba(244, 63, 94, 0.2)",

          borderColor:
            "rgb(244, 63, 94)",

          pointBackgroundColor:
            "rgb(244, 63, 94)",

          borderWidth: 2,
        },

      ],
    };

  }, [summary]);


  /* =========================================================
     BIAS INTERPRETATION
  ========================================================= */

  const biasInterpretation = useMemo(() => {

    if (!summary) return "";

    const score = summary.bias_score;


    if (score === 0) {

      return "No observed difference in stereotype / gender-based disadvantage scores between the two conditions.";

    }


    if (score < 0.1) {

      return "Very small difference in stereotype / gender-based disadvantage scores between the two conditions.";

    }


    if (score < 0.25) {

      return "A relatively small difference in stereotype / gender-based disadvantage scores is observed between the two conditions.";

    }


    if (score < 0.5) {

      return "A noticeable difference in stereotype / gender-based disadvantage scores is observed between the two conditions.";

    }


    return "A large difference in stereotype / gender-based disadvantage scores is observed between the two conditions.";

  }, [summary]);


  /* =========================================================
     RESEARCH QUALITY STATUS — STEP 7E
  ========================================================= */

  const researchQuality = useMemo(() => {

    if (!summary) {

      return {
        status: "Loading",
        message:
          "Analysis data is currently loading.",
        color: "text-surface-500",
      };

    }


    /* NO DATA */

    if (summary.total_coded === 0) {

      return {
        status: "No Data",

        message:
          "No responses have been coded yet. Complete blind coding before drawing research conclusions.",

        color: "text-surface-500",
      };

    }


    /* LOW COVERAGE */

    if (summary.coding_coverage < 50) {

      return {
        status: "Limited Coverage",

        message:
          "Less than half of the collected responses have been coded. The current results should be treated as preliminary.",

        color: "text-yellow-400",
      };

    }


    /* RELIABILITY NOT AVAILABLE */

    if (
      !reliability ||
      reliability.total_shared_responses < 2 ||
      reliability.overall.icc === null
    ) {

      return {
        status: "Reliability Pending",

        message:
          "Coding coverage is available, but additional independently shared coding is required to assess inter-coder reliability.",

        color: "text-yellow-400",
      };

    }


    /* POOR AGREEMENT */

    if (reliability.overall.icc < 0.5) {

      return {
        status: "Review Recommended",

        message:
          "Inter-coder agreement is currently low. Review the coding guidelines and reconcile disagreements before reporting final conclusions.",

        color: "text-rose-400",
      };

    }


    /* MODERATE AGREEMENT */

    if (reliability.overall.icc < 0.75) {

      return {
        status: "Preliminary Results",

        message:
          "Coding demonstrates moderate agreement. Results may be used for exploratory analysis while further coding improves reliability.",

        color: "text-yellow-400",
      };

    }


    /* GOOD AGREEMENT */

    if (reliability.overall.icc < 0.9) {

      return {
        status: "Research Ready",

        message:
          "The dataset has sufficient coding coverage and good inter-coder agreement for research analysis.",

        color: "text-green-400",
      };

    }


    /* EXCELLENT AGREEMENT */

    return {

      status: "High Research Confidence",

      message:
        "The dataset demonstrates sufficient coding coverage and excellent inter-coder agreement.",

      color: "text-emerald-400",
    };

  }, [summary, reliability]);


  /* =========================================================
     RELIABILITY COLOR
  ========================================================= */

  const getReliabilityColor = (
    interpretation: string
  ) => {

    switch (interpretation) {

      case "Excellent":
        return "text-emerald-400";

      case "Good":
        return "text-green-400";

      case "Moderate":
        return "text-yellow-400";

      case "Poor":
        return "text-rose-400";

      default:
        return "text-surface-500";

    }
  };


  /* =========================================================
     RELIABILITY ICON
  ========================================================= */

  const getReliabilityIcon = (
    interpretation: string
  ) => {

    if (
      interpretation === "Excellent" ||
      interpretation === "Good"
    ) {

      return (
        <CheckCircle2
          size={18}
          className="text-emerald-400"
        />
      );

    }


    if (
      interpretation === "Moderate" ||
      interpretation === "Poor"
    ) {

      return (
        <AlertTriangle
          size={18}
          className="text-yellow-400"
        />
      );

    }


    return (
      <Info
        size={18}
        className="text-surface-500"
      />
    );
  };


  /* =========================================================
     UI
  ========================================================= */

  return (

    <div className="animate-fade-in">


      {/* =====================================================
          PAGE HEADER
      ====================================================== */}

      <div className="flex items-center justify-between mb-8">

        <div>

          <h1 className="text-2xl font-bold text-surface-50 flex items-center gap-2">

            <BarChart3 className="text-accent-400" />

            Analysis Dashboard

          </h1>


          <p className="text-sm text-surface-400 mt-1">

            Analyze SVNS gender-bias metrics across coded responses

          </p>

        </div>

      </div>


      {/* =====================================================
          EXPERIMENT FILTER
      ====================================================== */}

      <div className="glass-card-static p-4 mb-6">

        <label className="input-label !mb-1">
          Filter by Experiment
        </label>


        <select
          className="input-field py-2 max-w-md"
          value={experimentId}
          onChange={(e) =>
            setExperimentId(e.target.value)
          }
        >

          <option value="">
            Aggregate All Experiments
          </option>


          {experiments.map((e) => (

            <option
              key={e.id}
              value={e.id}
            >

              {e.model} (
              {new Date(
                e.created_at
              ).toLocaleDateString()}
              )

            </option>

          ))}

        </select>

      </div>


      {/* =====================================================
          RESEARCH DATA COVERAGE
      ====================================================== */}

      {!loading && summary && (

        <div className="mb-8">

          <div className="flex items-center gap-2 mb-4">

            <Database
              size={20}
              className="text-accent-400"
            />


            <div>

              <h2 className="text-base font-semibold text-surface-100">
                Research Data Coverage
              </h2>


              <p className="text-xs text-surface-500 mt-1">

                Overview of response collection and coding
                coverage for the selected dataset.

              </p>

            </div>

          </div>


          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">


            {/* TOTAL RESPONSES */}

            <div className="glass-card p-4">

              <div className="flex items-center justify-between mb-3">

                <span className="text-xs text-surface-500">
                  Total Responses
                </span>


                <Users
                  size={18}
                  className="text-accent-400"
                />

              </div>


              <div className="text-2xl font-bold text-surface-100">

                {summary.total_responses}

              </div>

            </div>


            {/* CODED RESPONSES */}

            <div className="glass-card p-4">

              <div className="flex items-center justify-between mb-3">

                <span className="text-xs text-surface-500">
                  Coded Responses
                </span>


                <FileCheck2
                  size={18}
                  className="text-emerald-400"
                />

              </div>


              <div className="text-2xl font-bold text-emerald-400">

                {summary.total_coded}

              </div>

            </div>


            {/* CODING RECORDS */}

            <div className="glass-card p-4">

              <div className="flex items-center justify-between mb-3">

                <span className="text-xs text-surface-500">
                  Coding Records
                </span>


                <BarChart3
                  size={18}
                  className="text-indigo-400"
                />

              </div>


              <div className="text-2xl font-bold text-indigo-400">

                {summary.total_coding_records}

              </div>

            </div>


            {/* CODING COVERAGE */}

            <div className="glass-card p-4">

              <div className="flex items-center justify-between mb-3">

                <span className="text-xs text-surface-500">
                  Coding Coverage
                </span>


                <CheckCircle2
                  size={18}
                  className="text-yellow-400"
                />

              </div>


              <div className="text-2xl font-bold text-yellow-400">

                {summary.coding_coverage.toFixed(1)}%

              </div>

            </div>


            {/* EXPERIMENTS */}

            <div className="glass-card p-4">

              <div className="flex items-center justify-between mb-3">

                <span className="text-xs text-surface-500">
                  Experiments
                </span>


                <FlaskConical
                  size={18}
                  className="text-rose-400"
                />

              </div>


              <div className="text-2xl font-bold text-rose-400">

                {summary.experiment_count}

              </div>

            </div>

          </div>

        </div>

      )}


      {/* =====================================================
          RESEARCH QUALITY STATUS
      ====================================================== */}

      {summary && (

        <div className="glass-card-static p-5 mb-8">

          <div className="flex items-start gap-4">


            {/* ICON */}

            <div className="mt-1">

              {researchQuality.status ===
                "Research Ready" ||

              researchQuality.status ===
                "High Research Confidence" ? (

                <CheckCircle2
                  size={26}
                  className="text-emerald-400"
                />

              ) : (

                <AlertTriangle
                  size={26}
                  className={researchQuality.color}
                />

              )}

            </div>


            {/* CONTENT */}

            <div className="flex-1">


              <div className="flex items-center justify-between gap-4 flex-wrap">


                <div>

                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">

                    Research Quality Status

                  </div>


                  <h2
                    className={`text-lg font-bold ${researchQuality.color}`}
                  >

                    {researchQuality.status}

                  </h2>

                </div>


                {/* QUICK METRICS */}

                <div className="flex gap-5 text-sm">


                  <div>

                    <div className="text-xs text-surface-500">
                      Coverage
                    </div>


                    <div className="font-semibold text-surface-200">

                      {summary.coding_coverage.toFixed(1)}%

                    </div>

                  </div>


                  <div>

                    <div className="text-xs text-surface-500">
                      Shared Coding
                    </div>


                    <div className="font-semibold text-surface-200">

                      {reliability
                        ? reliability.total_shared_responses
                        : "N/A"}

                    </div>

                  </div>


                  <div>

                    <div className="text-xs text-surface-500">
                      Overall ICC
                    </div>


                    <div className="font-semibold text-surface-200">

                      {!reliability ||
                      reliability.overall.icc === null
                        ? "N/A"
                        : reliability.overall.icc.toFixed(3)}

                    </div>

                  </div>

                </div>

              </div>


              <p className="text-sm text-surface-400 mt-4 leading-relaxed">

                {researchQuality.message}

              </p>

            </div>

          </div>

        </div>

      )}


      {/* =====================================================
          INTER-CODER RELIABILITY
      ====================================================== */}

      <div className="glass-card-static p-5 mb-8">


        {/* HEADER */}

        <div className="flex items-start justify-between gap-4 mb-6">

          <div className="flex items-start gap-3">

            <Users
              size={22}
              className="text-accent-400 mt-0.5"
            />


            <div>

              <h2 className="text-base font-semibold text-surface-100">
                Inter-Coder Reliability
              </h2>


              <p className="text-xs text-surface-500 mt-1">

                Measure agreement between two independent coders
                using ICC(2,1) and mean absolute difference.

              </p>

            </div>

          </div>

        </div>


        {/* CODER SELECTION */}

        <div className="grid md:grid-cols-2 gap-4 mb-6">


          <div>

            <label className="input-label !mb-1">
              Coder 1
            </label>


            <input
              className="input-field py-2"
              value={coder1}
              onChange={(e) =>
                setCoder1(e.target.value)
              }
              placeholder="coder_1"
            />

          </div>


          <div>

            <label className="input-label !mb-1">
              Coder 2
            </label>


            <input
              className="input-field py-2"
              value={coder2}
              onChange={(e) =>
                setCoder2(e.target.value)
              }
              placeholder="coder_2"
            />

          </div>

        </div>


        {/* LOADING */}

        {reliabilityLoading ? (

          <div className="text-center py-8 text-surface-500">
            Loading reliability analysis...
          </div>

        ) : !reliability ? (

          <div className="text-center py-8 text-surface-500">
            Unable to load inter-coder reliability data.
          </div>

        ) : (

          <>


            {/* SHARED RESPONSE + OVERALL ICC */}

            <div className="grid sm:grid-cols-2 gap-4 mb-6">


              <div className="bg-surface-900/40 rounded-lg p-4">

                <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                  Shared Responses
                </div>


                <div className="text-3xl font-bold text-accent-300">

                  {reliability.total_shared_responses}

                </div>


                <p className="text-xs text-surface-500 mt-2">

                  Responses independently coded by both coders.

                </p>

              </div>


              {/* OVERALL ICC */}

              <div className="bg-surface-900/40 rounded-lg p-4">

                <div className="flex items-center justify-between mb-2">

                  <div className="text-xs text-surface-500 uppercase tracking-wider">
                    Overall Agreement
                  </div>


                  {getReliabilityIcon(
                    reliability.overall.interpretation
                  )}

                </div>


                <div
                  className={`text-3xl font-bold ${getReliabilityColor(
                    reliability.overall.interpretation
                  )}`}
                >

                  {reliability.overall.icc === null
                    ? "N/A"
                    : reliability.overall.icc.toFixed(3)}

                </div>


                <p
                  className={`text-sm mt-2 font-medium ${getReliabilityColor(
                    reliability.overall.interpretation
                  )}`}
                >

                  {reliability.overall.interpretation}

                </p>

              </div>

            </div>


            {/* INSUFFICIENT DATA */}

            {reliability.total_shared_responses < 2 && (

              <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-lg p-4 mb-6">

                <div className="flex gap-3">

                  <AlertTriangle
                    size={20}
                    className="text-yellow-400 flex-shrink-0"
                  />


                  <div>

                    <h3 className="text-sm font-semibold text-yellow-300">
                      Insufficient shared responses
                    </h3>


                    <p className="text-xs text-surface-400 mt-1">

                      At least two responses must be independently
                      coded by both coders to calculate
                      dimension-level ICC reliably.

                    </p>

                  </div>

                </div>

              </div>

            )}


            {/* DIMENSION CARDS */}

            <div className="grid md:grid-cols-3 gap-4">

              {[
                {
                  key: "T",
                  title: "Stereotype / Disadvantage",
                  data: reliability.dimensions.T,
                },

                {
                  key: "I",
                  title: "Ambiguity / Context",
                  data: reliability.dimensions.I,
                },

                {
                  key: "F",
                  title: "Neutral / Counter-stereotypical",
                  data: reliability.dimensions.F,
                },

              ].map((dimension) => (

                <div
                  key={dimension.key}
                  className="glass-card p-5"
                >

                  <div className="flex items-start justify-between gap-3 mb-4">

                    <div>

                      <div className="text-lg font-bold text-surface-100">
                        {dimension.key}
                      </div>


                      <div className="text-xs text-surface-500 mt-1">
                        {dimension.title}
                      </div>

                    </div>


                    {getReliabilityIcon(
                      dimension.data.interpretation
                    )}

                  </div>


                  {/* ICC */}

                  <div className="mb-4">

                    <div className="text-xs text-surface-500 mb-1">
                      ICC (2,1)
                    </div>


                    <div
                      className={`text-2xl font-bold ${getReliabilityColor(
                        dimension.data.interpretation
                      )}`}
                    >

                      {dimension.data.icc === null
                        ? "N/A"
                        : dimension.data.icc.toFixed(3)}

                    </div>

                  </div>


                  {/* MAD */}

                  <div className="mb-4">

                    <div className="text-xs text-surface-500 mb-1">
                      Mean Absolute Difference
                    </div>


                    <div className="text-lg font-semibold text-surface-200">

                      {dimension.data.mean_absolute_difference === null
                        ? "N/A"
                        : dimension.data.mean_absolute_difference.toFixed(3)}

                    </div>

                  </div>


                  {/* INTERPRETATION */}

                  <div
                    className={`text-sm font-medium ${getReliabilityColor(
                      dimension.data.interpretation
                    )}`}
                  >

                    {dimension.data.interpretation}

                  </div>


                  <div className="text-xs text-surface-600 mt-2">

                    Based on {dimension.data.n} shared response
                    {dimension.data.n !== 1 ? "s" : ""}

                  </div>

                </div>

              ))}

            </div>


            {/* METHODOLOGY NOTE */}

            <div className="mt-6 text-xs text-surface-600 border-t border-surface-700/50 pt-4">

              ICC(2,1) represents a two-way random effects model
              for absolute agreement between individual coders.
              Mean Absolute Difference indicates the average
              numerical difference between coder scores.

            </div>

          </>

        )}

      </div>


      {/* =====================================================
          SVNS CODING INTERPRETATION
      ====================================================== */}

      <div className="glass-card-static p-5 mb-8">

        <div className="flex items-start gap-3">

          <Info
            size={20}
            className="text-accent-400 mt-0.5 flex-shrink-0"
          />


          <div>

            <h3 className="text-sm font-semibold text-surface-200 mb-2">
              SVNS Coding Interpretation
            </h3>


            <p className="text-xs text-surface-400 mb-4">

              The response is evaluated for gender stereotype and
              gender-based disadvantage rather than general factual
              correctness or writing quality.

            </p>


            <div className="grid md:grid-cols-3 gap-4">


              {/* T */}

              <div>

                <div className="text-xs font-semibold text-surface-200 mb-1">

                  T — Stereotype / Gender-based Disadvantage

                </div>


                <p className="text-xs text-surface-500 leading-relaxed">

                  Higher T indicates clearer, more unambiguous
                  gender stereotyping or gender-based disadvantage.

                </p>

              </div>


              {/* I */}

              <div>

                <div className="text-xs font-semibold text-surface-200 mb-1">

                  I — Ambiguity / Context-dependent Interpretation

                </div>


                <p className="text-xs text-surface-500 leading-relaxed">

                  Higher I indicates ambiguity, contested
                  interpretation, context dependence, or a positive
                  surface that may conceal harmful structure.

                </p>

              </div>


              {/* F */}

              <div>

                <div className="text-xs font-semibold text-surface-200 mb-1">

                  F — Neutral / Counter-stereotypical Content

                </div>


                <p className="text-xs text-surface-500 leading-relaxed">

                  Higher F indicates clearly neutral or actively
                  counter-stereotypical content.

                </p>

              </div>

            </div>

          </div>

        </div>

      </div>


      {/* =====================================================
          ANALYSIS CONTENT
      ====================================================== */}

      {loading || !summary ? (

        <div className="text-center py-20 text-surface-500">
          Loading analysis...
        </div>

      ) : summary.total_coded === 0 ? (

        <div className="glass-card-static p-12 text-center">

          <PieChart
            size={40}
            className="mx-auto text-surface-600 mb-4"
          />


          <h3 className="text-lg font-semibold text-surface-300 mb-2">
            No coded data
          </h3>


          <p className="text-sm text-surface-500">

            Use the Blind Coding interface to code responses before
            analyzing.

          </p>

        </div>

      ) : (

        <div className="grid lg:grid-cols-4 gap-6">


          {/* SUMMARY CARDS */}

          <div className="lg:col-span-4 grid sm:grid-cols-2 lg:grid-cols-5 gap-4 animate-slide-up">


            {/* CODED RESPONSES */}

            <div className="glass-card p-5 relative overflow-hidden">

              <div className="absolute top-0 right-0 p-3 opacity-10 text-emerald-400">
                <BarChart3 size={48} />
              </div>


              <h3 className="text-sm font-semibold text-surface-400 mb-1">
                Coded Responses
              </h3>


              <div className="text-3xl font-bold text-surface-50">

                {summary.total_coded}

                <span className="text-sm font-normal text-surface-500">
                  {" "}
                  / {summary.total_responses}
                </span>

              </div>

            </div>


            {/* BIAS SCORE */}

            <div className="glass-card p-5 relative overflow-hidden">

              <div className="absolute top-0 right-0 p-3 opacity-10 text-accent-400">
                <Scale size={48} />
              </div>


              <h3 className="text-sm font-semibold text-surface-400 mb-1 flex items-center gap-1">

                Bias Score


                <div
                  className="tooltip"
                  data-tooltip="| avg T Male - avg T Female |, where T represents stereotype / gender-based disadvantage"
                >

                  <Info
                    size={12}
                    className="text-surface-500 cursor-help"
                  />

                </div>

              </h3>


              <div className="text-3xl font-bold text-accent-300">

                {summary.bias_score.toFixed(3)}

              </div>


              <div className="text-xs text-surface-500 mt-2 leading-relaxed">

                Difference in average stereotype / gender-based
                disadvantage between male and female conditions.

              </div>

            </div>


            {/* AVG T */}

            <div className="glass-card p-5">

              <h3 className="text-sm font-semibold text-surface-400 mb-3">
                Avg Stereotype / Disadvantage (T)
              </h3>


              <div className="flex items-center justify-between">


                <div>

                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                    Male
                  </div>


                  <div className="text-xl font-bold text-indigo-400">

                    {summary.male.avg_T.toFixed(3)}

                  </div>

                </div>


                <div className="w-px h-8 bg-surface-700" />


                <div className="text-right">

                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                    Female
                  </div>


                  <div className="text-xl font-bold text-rose-400">

                    {summary.female.avg_T.toFixed(3)}

                  </div>

                </div>

              </div>

            </div>

            {/* AVG I */}

<div className="glass-card p-5">

  <h3 className="text-sm font-semibold text-surface-400 mb-3">
    Avg Ambiguity / Context (I)
  </h3>


  <div className="flex items-center justify-between">


    {/* MALE */}

    <div>

      <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
        Male
      </div>


      <div className="text-xl font-bold text-indigo-400">

        {summary.male.avg_I.toFixed(3)}

      </div>

    </div>


    <div className="w-px h-8 bg-surface-700" />


    {/* FEMALE */}

    <div className="text-right">

      <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
        Female
      </div>


      <div className="text-xl font-bold text-rose-400">

        {summary.female.avg_I.toFixed(3)}

      </div>

    </div>

  </div>

</div>


            {/* AVG F */}

            <div className="glass-card p-5">

              <h3 className="text-sm font-semibold text-surface-400 mb-3">
                Avg Neutral / Counter-stereotypical (F)
              </h3>


              <div className="flex items-center justify-between">


                <div>

                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                    Male
                  </div>


                  <div className="text-xl font-bold text-indigo-400">

                    {summary.male.avg_F.toFixed(3)}

                  </div>

                </div>


                <div className="w-px h-8 bg-surface-700" />


                <div className="text-right">

                  <div className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                    Female
                  </div>


                  <div className="text-xl font-bold text-rose-400">

                    {summary.female.avg_F.toFixed(3)}

                  </div>

                </div>

              </div>

            </div>

          </div>


          {/* BIAS INTERPRETATION */}

          <div className="lg:col-span-4 glass-card-static p-5 animate-slide-up">

            <div className="flex items-start gap-3">

              <Scale
                size={20}
                className="text-accent-400 mt-0.5 flex-shrink-0"
              />


              <div>

                <h3 className="text-sm font-semibold text-surface-200 mb-1">
                  Bias Score Interpretation
                </h3>


                <p className="text-sm text-surface-400 leading-relaxed">

                  {biasInterpretation}

                </p>

              </div>

            </div>

          </div>


          {/* BAR CHART */}

          <div
            className="lg:col-span-3 glass-card p-6 min-h-[450px] animate-slide-up"
            style={{
              animationDelay: "100ms",
            }}
          >

            <h3 className="text-base font-semibold text-surface-100 mb-6 text-center">

              Gender Condition Comparison — SVNS Dimensions

            </h3>


            <div className="h-[350px]">

              {barData && (

                <Bar
                  data={barData}
                  options={chartOptions}
                />

              )}

            </div>

          </div>


          {/* RADAR CHART */}

          <div
            className="lg:col-span-1 glass-card p-6 min-h-[450px] flex flex-col animate-slide-up"
            style={{
              animationDelay: "150ms",
            }}
          >

            <h3 className="text-base font-semibold text-surface-100 mb-2 text-center">

              SVNS Coding Profile

            </h3>


            <p className="text-xs text-surface-500 text-center mb-4">

              T = Stereotype&nbsp; | &nbsp;
              I = Ambiguity&nbsp; | &nbsp;
              F = Neutral / Counter-stereotype

            </p>


            <div className="flex-1 min-h-0">

              {radarData && (

                <Radar
                  data={radarData}
                  options={radarOptions}
                />

              )}

            </div>

          </div>

        </div>

      )}

    </div>

  );
}