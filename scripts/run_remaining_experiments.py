"""
Sequential Batch Runner for Remaining NPC Experiments.

Executes remaining experiments one-by-one using the exact standard runner
pipeline (_run_experiment from backend/routes/runner.py).

Features:
- 100% faithful to manual execution (Ollama NPC generations, gender swapping, canonical params).
- Persists all responses to Neon PostgreSQL (db_insert_batch) and data/responses.json.
- Updates experiment status to 'completed' in Neon and data/experiments.json.
- Live per-replicate progress display.
- Fully resumable and interruptible (Ctrl+C safely finishes or halts).
- Supports --limit N to run a specific number of experiments, or runs all remaining by default.
- Supports --dry-run to inspect the queued experiments.
"""

import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Setup paths to import from backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from storage import read_json, find_by_id
from routes.runner import _run_experiment, _progress


async def monitor_progress(experiment_id: str, stop_event: asyncio.Event, total: int):
    """Periodically print progress updates while an experiment is generating."""
    last_completed = -1
    while not stop_event.is_set():
        prog = _progress.get(experiment_id)
        if prog:
            completed = prog.get("completed", 0)
            if completed != last_completed:
                pairs = completed // 2
                print(f"   [{datetime.now().strftime('%H:%M:%S')}] Generated {completed}/{total} responses ({pairs} pairs)...", flush=True)
                last_completed = completed
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            pass


async def main():
    parser = argparse.ArgumentParser(description="Run remaining NPC experiments sequentially.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of experiments to run in this batch.")
    parser.add_argument("--dry-run", action="store_true", help="Print remaining experiments without running them.")
    args = parser.parse_args()

    experiments = read_json("experiments.json")
    scenarios = {s["id"]: s for s in read_json("scenarios.json")}
    scaffolds = {s["id"]: s for s in read_json("scaffolds.json")}

    # Select experiments that need to be run, sorted in systematic order
    remaining = sorted(
        [e for e in experiments if e.get("status") == "configured"],
        key=lambda e: e.get("created_at", "")
    )

    print("=" * 80)
    print(f"NPC BATCH EXPERIMENT RUNNER")
    print(f"Total experiments configured: {len(experiments)}")
    print(f"Experiments already completed: {len(experiments) - len(remaining)}")
    print(f"Experiments remaining to run:  {len(remaining)}")
    print("=" * 80)

    if args.limit:
        remaining = remaining[:args.limit]
        print(f"Limiting execution to {len(remaining)} experiment(s) as requested.\n")

    if not remaining:
        print("No experiments pending. Everything is completed!")
        return

    if args.dry_run:
        print("DRY RUN QUEUE:")
        for idx, exp in enumerate(remaining, 1):
            sc = scenarios.get(exp.get("scenario_id"), {})
            scaf = scaffolds.get(exp.get("scaffold_id"), {})
            print(f"  {idx:2d}. {exp['id'][:8]} | {sc.get('title', 'Unknown')} | {scaf.get('name', 'Unknown')} ({scaf.get('version', '')}) | {exp.get('model')}")
        print("\nDry run complete. Exiting without changes.")
        return

    total_to_run = len(remaining)
    print(f"Starting batch execution of {total_to_run} experiment(s)...\n")

    for idx, exp in enumerate(remaining, 1):
        exp_id = exp["id"]
        sc = scenarios.get(exp.get("scenario_id"), {})
        scaf = scaffolds.get(exp.get("scaffold_id"), {})
        reps = exp.get("num_replicates", 20)
        total_responses = 2 * reps

        print("-" * 80)
        print(f"[{idx}/{total_to_run}] RUNNING EXPERIMENT {exp_id}")
        print(f"  Scenario:   {sc.get('title', 'Unknown')}")
        print(f"  Scaffold:   {scaf.get('name', 'Unknown')} (v{scaf.get('version', '1.0')})")
        print(f"  Model:      {exp.get('model')}")
        print(f"  Target:     {reps} replicates ({total_responses} responses / {reps} pairs)")
        print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80, flush=True)

        # Start progress monitor
        stop_event = asyncio.Event()
        monitor_task = asyncio.create_task(monitor_progress(exp_id, stop_event, total_responses))

        start_time = datetime.now()
        try:
            await _run_experiment(exp_id)
        except Exception as err:
            stop_event.set()
            await monitor_task
            print(f"  [ERROR] Experiment {exp_id} encountered an error: {err}", flush=True)
            continue
        finally:
            stop_event.set()
            await monitor_task

        elapsed = datetime.now() - start_time
        print(f"  [SUCCESS] Experiment {exp_id} completed in {elapsed.total_seconds():.1f}s.")
        print(f"  Saved {reps} pairs to Neon PostgreSQL and data/responses.json.\n", flush=True)

    print("=" * 80)
    print("BATCH RUN COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Execution interrupted by user. Completed experiments are safely saved.")
        sys.exit(0)
