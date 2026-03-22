import json
import os
import sys
from pathlib import Path
from graph_builder import save_toon

GRAPH_FILE = "graph_explorer/dependency_data.json"
BITBUCKET_DUMP = "graph_explorer/mrflex_latest_jira.json"
OUTPUT_FILE = "graph_explorer/dependency_data_with_meta.json"
TOON_OUTPUT = "graph_explorer/dependency_data_with_meta.toon"

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit(f"❌ File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    graph = load_json(GRAPH_FILE)
    dump = load_json(BITBUCKET_DUMP)

    bh_meta = dump.get("repository", {}).get("latest_commit_per_script", {})

    enriched = 0
    for node in graph.get("nodes", []):
        id_path = Path(node["id"]).as_posix() # normalise slashes
        try:
            idx = id_path.index("Deploy/")
            key = id_path[idx:]              # "Deploy/SPEScripts/..."
        except ValueError:
            # Not a Deploy/ file - nothing we can match.
            continue

        meta = bh_meta.get(key)
        if meta:
            # Add the three fields that the UI expects.
            node["committer"] = meta.get("committer")
            node["commit_date"] = meta.get("date")
            node["jira_number"] = meta.get("jira_number")
            enriched += 1

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    # Save TOON output
    save_toon(TOON_OUTPUT, graph)

    print(f"✅ Enriched {enriched} nodes with Bitbucket metadata.")
    print(f"📁 Output written to {OUTPUT_FILE} and {TOON_OUTPUT}")

if __name__ == "__main__":
    main()
