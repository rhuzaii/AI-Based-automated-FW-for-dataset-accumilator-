import csv
import os

def write_metadata(path, row):

    # ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    file_exists = os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "filename",
                "source_url",
                "license",
                "timestamp",
                "category",
                "size_kb"
            ])

        writer.writerow(row)
