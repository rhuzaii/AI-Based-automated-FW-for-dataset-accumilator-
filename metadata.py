import csv
import os
from pathlib import Path


METADATA_HEADERS = [
    "filename",
    "license_type",
    "status",
    "date_classified",
    "matched_label",
    "confidence",
]


def write_metadata(csv_path: str, row: list) -> None:
    path = Path(csv_path)
    write_header = not path.exists() or path.stat().st_size == 0

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(METADATA_HEADERS)
        writer.writerow(row)


def read_metadata(csv_path: str) -> list:
    path = Path(csv_path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metadata_summary(datasets_root: str = "datasets") -> dict:
    summary = {}
    root = Path(datasets_root)
    for csv_file in root.rglob("metadata.csv"):
        category = csv_file.parent.parent.name   # datasets/<category>/metadata.csv
        rows = read_metadata(str(csv_file))
        summary[category] = len(rows)
    return summary