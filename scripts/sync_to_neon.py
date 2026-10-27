"""
Synchronization script: pushes local JSON data to Neon PostgreSQL.

Actions:
1. Scenarios: ensures all 20 scenarios are upserted into Neon DB.
2. Experiments: synchronizes the exact 120 experiments (60 baseline + 60 salient)
   and cleans up any stale/orphaned experiments in Neon so total count is exactly 120.
3. Responses: ensures all 4,880 responses (2,480 baseline + 2,400 salient) are
   persisted into Neon DB.
"""

import os
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from database import is_db_configured, get_db_connection, db_upsert_record, get_table_columns

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def sync_data():
    if not is_db_configured():
        print("[ERROR] DATABASE_URL is not configured in .env!")
        return

    print("Connecting to Neon PostgreSQL...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        print("Connected to Neon DB successfully!\n")
    except Exception as e:
        print(f"[ERROR] Could not connect to Neon DB: {e}")
        return

    # ── 1. Sync Scenarios ────────────────────────────────────────────────────────
    print("=== 1. Syncing Scenarios ===")
    scenarios_file = DATA_DIR / "scenarios.json"
    with open(scenarios_file, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    for s in scenarios:
        db_upsert_record("scenarios", s)
    print(f"Upserted {len(scenarios)} scenarios into Neon DB.\n")

    # ── 2. Sync Experiments ──────────────────────────────────────────────────────
    print("=== 2. Syncing Experiments ===")
    experiments_file = DATA_DIR / "experiments.json"
    with open(experiments_file, "r", encoding="utf-8") as f:
        experiments = json.load(f)

    valid_exp_ids = set(e["id"] for e in experiments)
    print(f"Local experiments to sync: {len(experiments)}")

    for e in experiments:
        db_upsert_record("experiments", e)

    # Clean up stale/duplicate experiments in Neon DB not in valid_exp_ids
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM experiments;")
            db_exp_ids = set(row["id"] for row in cur.fetchall())
            stale_ids = db_exp_ids - valid_exp_ids
            if stale_ids:
                print(f"Removing {len(stale_ids)} stale experiment records from Neon DB...")
                cur.execute("DELETE FROM experiments WHERE id = ANY(%s);", (list(stale_ids),))
                print(f"Removed {len(stale_ids)} stale records.")

            cur.execute("SELECT COUNT(*) as count FROM experiments;")
            final_exp_count = cur.fetchone()["count"]
            print(f"Final experiments count in Neon DB: {final_exp_count}\n")

    # ── 3. Sync Responses ────────────────────────────────────────────────────────
    print("=== 3. Syncing Responses ===")
    responses_file = DATA_DIR / "responses.json"
    with open(responses_file, "r", encoding="utf-8") as f:
        responses = json.load(f)

    print(f"Local responses total: {len(responses)}")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM responses;")
            existing_resp_ids = set(row["id"] for row in cur.fetchall())
            print(f"Existing responses in Neon DB: {len(existing_resp_ids)}")

            missing_responses = [r for r in responses if r["id"] not in existing_resp_ids]
            print(f"Responses to upload to Neon DB: {len(missing_responses)}")

            if missing_responses:
                valid_cols = get_table_columns("responses")
                batch_size = 500
                total_inserted = 0

                for i in range(0, len(missing_responses), batch_size):
                    batch = missing_responses[i : i + batch_size]
                    cleaned_batch = []
                    for r in batch:
                        cl = {k: v for k, v in r.items() if k in valid_cols}
                        cleaned_batch.append(cl)

                    keys = list(cleaned_batch[0].keys())
                    cols = ", ".join(keys)
                    placeholders = ", ".join(["%s"] * len(keys))
                    sql = f"INSERT INTO responses ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING;"

                    values = [[row.get(k) for k in keys] for row in cleaned_batch]
                    cur.executemany(sql, values)
                    total_inserted += len(batch)
                    print(f"  -> Uploaded {total_inserted}/{len(missing_responses)} responses...")

            cur.execute("SELECT COUNT(*) as count FROM responses;")
            final_resp_count = cur.fetchone()["count"]
            print(f"Final responses count in Neon DB: {final_resp_count}\n")

    # ── 4. Sync Codings ──────────────────────────────────────────────────────────
    print("=== 4. Syncing Codings ===")
    coding_file = DATA_DIR / "coding.json"
    if coding_file.exists():
        with open(coding_file, "r", encoding="utf-8") as f:
            codings = json.load(f)

        print(f"Local codings total: {len(codings)}")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM responses;")
                db_resp_ids = set(row["id"] for row in cur.fetchall())

                cur.execute("SELECT response_id, coder_id FROM codings;")
                existing_pairs = set((row["response_id"], row["coder_id"]) for row in cur.fetchall())
                print(f"Existing codings in Neon DB: {len(existing_pairs)}")

                missing_codings = [
                    c for c in codings 
                    if c["response_id"] in db_resp_ids and (c["response_id"], c["coder_id"]) not in existing_pairs
                ]
                print(f"Codings to upload to Neon DB: {len(missing_codings)}")

                if missing_codings:
                    cols = ["id", "response_id", "coder_id", "truth", "indeterminacy", "falsity", "reasoning_notes", "coded_at"]
                    col_str = ", ".join(cols)
                    placeholders = ", ".join(["%s"] * len(cols))
                    sql = f"""
                        INSERT INTO codings ({col_str})
                        VALUES ({placeholders})
                        ON CONFLICT (response_id, coder_id) DO UPDATE SET
                            truth = EXCLUDED.truth,
                            indeterminacy = EXCLUDED.indeterminacy,
                            falsity = EXCLUDED.falsity,
                            reasoning_notes = EXCLUDED.reasoning_notes,
                            coded_at = EXCLUDED.coded_at;
                    """
                    batch_size = 500
                    total_uploaded = 0
                    for i in range(0, len(missing_codings), batch_size):
                        batch = missing_codings[i : i + batch_size]
                        values = [[row.get(k) for k in cols] for row in batch]
                        cur.executemany(sql, values)
                        total_uploaded += len(batch)
                        print(f"  -> Uploaded {total_uploaded}/{len(missing_codings)} codings...")

                cur.execute("SELECT COUNT(*) as count FROM codings;")
                final_coding_count = cur.fetchone()["count"]
                print(f"Final codings count in Neon DB: {final_coding_count}\n")

    print("======================================================")
    print("   NEON POSTGRESQL & LOCAL STORAGE ARE NOW FULLY IN SYNC! ")
    print("======================================================")

if __name__ == "__main__":
    sync_data()
