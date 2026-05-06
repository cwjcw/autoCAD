"""Generate 10 randomized CSV rows for the Z bracket MCP batch processor.

Output:
    E:\\code\\autoCAD\\data\\batch_params.csv
"""

from __future__ import annotations

import csv
import random
import uuid
from pathlib import Path


OUTPUT_PATH = Path(r"E:\code\autoCAD\data\batch_params.csv")
PROCESS_TYPES = ("miter_45", "butt_joint")


def rounded(value: float) -> float:
    """Keep generated dimensions readable while preserving useful variation."""
    return round(value, 2)


def make_row() -> dict[str, str | float]:
    """Create one physically reasonable parameter row."""
    disk_dia = rounded(random.uniform(40.0, 80.0))
    rod_limit = disk_dia * 0.8
    rod_dia = rounded(random.uniform(6.0, min(24.0, rod_limit - 0.5)))
    post_height = rounded(random.uniform(45.0, 120.0))
    arm_length = rounded(random.uniform(55.0, 160.0))
    return {
        "uid": str(uuid.uuid4()),
        "disk_dia": disk_dia,
        "rod_dia": rod_dia,
        "post_height": post_height,
        "arm_length": arm_length,
        "process_type": random.choice(PROCESS_TYPES),
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = [make_row() for _ in range(10)]
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["uid", "disk_dia", "rod_dia", "post_height", "arm_length", "process_type"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(str(OUTPUT_PATH))


if __name__ == "__main__":
    main()
