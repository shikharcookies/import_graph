import os
import json
import csv
import pandas as pd

def save_json(output_file, meta, nodes, edges, indirect_dependencies, minify=False):
    """Saves the main dependency graph as JSON."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        if minify:
            json.dump({
                "meta": meta,
                "nodes": nodes,
                "edges": edges,
                "indirect_dependencies": indirect_dependencies
            }, f, separators=(',', ':'))
        else:
            json.dump({
                "meta": meta,
                "nodes": nodes,
                "edges": edges,
                "indirect_dependencies": indirect_dependencies
            }, f, indent=2)

def save_toon(output_file, data):
    """
    Saves the data in TOON (Token-Oriented Object Notation) like format.
    This is a simplified implementation to save space for LLM-ready contexts.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    toon_content = _to_toon_format(data)
    with open(output_file, "w") as f:
        f.write(toon_content)

def _to_toon_format(obj, indent=0):
    """Simple recursive TOON encoder."""
    space = '  ' * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{space}{k}:")
                lines.append(_to_toon_format(v, indent + 1))
            else:
                lines.append(f"{space}{k}: {json.dumps(v)}")
        return "\n".join(lines)
    elif isinstance(obj, list):
        if not obj: return f"{space}[]"
        # Check if it's a list of uniform dicts (tabular array)
        if all(isinstance(i, dict) for i in obj) and len(obj) > 1:
            keys = list(obj[0].keys())
            if all(list(i.keys()) == keys for i in obj):
                header = f"{space}[{len(obj)},]{{{','.join(keys)}}}:"
                rows = []
                for i in obj:
                    row = ",".join(json.dumps(i[k]) for k in keys)
                    rows.append(f"{space}  {row}")
                return header + "\n" + "\n".join(rows)
        
        # Default list format
        lines = []
        for i in obj:
            if isinstance(i, (dict, list)):
                lines.append(f"{space}-")
                lines.append(_to_toon_format(i, indent + 1))
            else:
                lines.append(f"{space}- {json.dumps(i)}")
        return "\n".join(lines)
    else:
        return f"{space}{json.dumps(obj)}"

def save_csv(output_file, csv_rows):
    """Saves the import report as CSV."""
    with open(output_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["file", "imported_module", "import_statement", "type"])
        writer.writerows(csv_rows)

def generate_report_json(csv_input, report_output):
    """Converts CSV report into a grouped JSON report."""
    if os.path.exists(csv_input):
        df = pd.read_csv(csv_input)
        grouped = (
            df.groupby("file")
            .apply(lambda g: g[["imported_module", "import_statement", "type"]]
                   .to_dict(orient="records"))
            .to_dict()
        )
        with open(report_output, "w") as f:
            json.dump(grouped, f, indent=2)
        return df
    return None
