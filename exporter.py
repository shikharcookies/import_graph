import os
import json
import csv
import pandas as pd
from config import OUTPUT_FILE, CSV_OUTPUT, REPORT_JSON

def save_json(meta, nodes, edges, indirect_dependencies):
    """Saves the main dependency graph as JSON."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "meta": meta,
            "nodes": nodes,
            "edges": edges,
            "indirect_dependencies": indirect_dependencies
        }, f, indent=2)

def save_csv(csv_rows):
    """Saves the import report as CSV."""
    with open(CSV_OUTPUT, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["file", "imported_module", "import_statement", "type"])
        writer.writerows(csv_rows)

def generate_report_json():
    """Converts CSV report into a grouped JSON report."""
    if os.path.exists(CSV_OUTPUT):
        df = pd.read_csv(CSV_OUTPUT)
        grouped = (
            df.groupby("file")
            .apply(lambda g: g[["imported_module", "import_statement", "type"]]
                   .to_dict(orient="records"))
            .to_dict()
        )
        with open(REPORT_JSON, "w") as f:
            json.dump(grouped, f, indent=2)
        return df
    return None
