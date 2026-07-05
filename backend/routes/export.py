"""
Export route.
Generates a ZIP file containing all data files and analysis summary.
"""

import io
import json
import zipfile
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from storage import read_json
from routes.analysis import _compute_metrics

router = APIRouter(prefix="/api/export", tags=["export"])

DATA_FILES = [
    ("scenarios.json", "scenarios.json"),
    ("scaffolds.json", "scaffolds.json"),
    ("experiments.json", "experiments.json"),
    ("responses.json", "responses.json"),
    ("coding.json", "coding.json"),
    ("custom_word_pairs.json", "custom_word_pairs.json"),
]


@router.get("")
def export_all():
    """
    Export all experiment data as a ZIP archive.
    Includes all JSON data files plus a computed analysis summary.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all data files
        for filename, archive_name in DATA_FILES:
            data = read_json(filename)
            zf.writestr(
                f"data/{archive_name}",
                json.dumps(data, indent=2, ensure_ascii=False),
            )

        # Generate and add analysis summary
        analysis = _compute_metrics()
        zf.writestr(
            "analysis/summary.json",
            json.dumps(analysis, indent=2, ensure_ascii=False),
        )

        # Add per-experiment analysis
        responses = read_json("responses.json")
        experiment_ids = list(
            set(r.get("experiment_id") for r in responses if r.get("experiment_id"))
        )
        per_experiment = []
        for eid in sorted(experiment_ids):
            metrics = _compute_metrics(eid)
            if metrics["total_coded"] > 0:
                per_experiment.append(metrics)

        zf.writestr(
            "analysis/per_experiment.json",
            json.dumps(per_experiment, indent=2, ensure_ascii=False),
        )

        # Add export metadata
        meta = {
            "exported_at": datetime.utcnow().isoformat(),
            "files_included": [f[1] for f in DATA_FILES]
            + ["analysis/summary.json", "analysis/per_experiment.json"],
            "total_scenarios": len(read_json("scenarios.json")),
            "total_scaffolds": len(read_json("scaffolds.json")),
            "total_experiments": len(read_json("experiments.json")),
            "total_responses": len(responses),
            "total_codings": len(read_json("coding.json")),
        }
        zf.writestr(
            "export_metadata.json",
            json.dumps(meta, indent=2, ensure_ascii=False),
        )

    buffer.seek(0)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"bias_research_export_{timestamp}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
