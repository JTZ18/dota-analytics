"""Combine all insights into a single JSON payload for the playground frontend."""

import json
from scripts.config import DATA_PROCESSED


def export_all():
    """Merge insights.json and ml_insights.json into a single frontend payload."""
    with open(DATA_PROCESSED / "insights.json") as f:
        insights = json.load(f)

    ml_path = DATA_PROCESSED / "ml_insights.json"
    if ml_path.exists():
        with open(ml_path) as f:
            ml = json.load(f)
        insights["ml"] = ml
    else:
        insights["ml"] = None

    output_path = DATA_PROCESSED / "frontend_data.json"
    with open(output_path, "w") as f:
        json.dump(insights, f, indent=2, default=str)

    print(f"Frontend data exported to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    export_all()
