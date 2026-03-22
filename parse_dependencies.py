import os
import sys

# Import our custom modules
from ast_parser import analyze_file
from dependency_resolver import Resolver
from graph_builder import save_json, save_toon, save_csv, generate_report_json

# Programmatically get all Python standard library and built-in module names
STDLIB_MODULES = getattr(sys, "stdlib_module_names", set()) | set(sys.builtin_module_names)

# CLI Configuration
SCAN_ROOT = sys.argv[1] if len(sys.argv) > 1 else "Deploy"
FOCUS_FOLDER = sys.argv[2] if len(sys.argv) > 2 else "SPEScripts"

# Paths
OUTPUT_FILE = "graph_explorer/dependency_data.json"
TOON_OUTPUT = "graph_explorer/dependency_data.toon"
CSV_OUTPUT = "graph_explorer/import_report.csv"
REPORT_JSON = "graph_explorer/import_report.json"

# Exclusions
EXCLUDE_FOLDERS = [".venv", "__pycache__", ".git", "graph_explorer"]

def run_pipeline():
    # 1. Initialization
    if not os.path.exists(SCAN_ROOT):
        print(f"Error: '{SCAN_ROOT}' not found. Please ensure you're in the project root.")
        return

    single_file = SCAN_ROOT if os.path.isfile(SCAN_ROOT) else None
    scan_root_dir = os.path.dirname(SCAN_ROOT) if single_file else SCAN_ROOT
    
    # Discover folders
    if single_file:
        all_folders = [scan_root_dir]
    else:
        all_folders = [os.path.join(SCAN_ROOT, d) for d in os.listdir(SCAN_ROOT)
                       if os.path.isdir(os.path.join(SCAN_ROOT, d)) and d not in EXCLUDE_FOLDERS]

    # 2. Setup Resolver
    resolver = Resolver(all_folders, SCAN_ROOT, STDLIB_MODULES, single_file)
    folder_colors = {os.path.basename(f): i for i, f in enumerate(all_folders)}

    nodes = []
    edges = []
    csv_rows = []
    indirect_dependencies = {}
    seen_edges = set()

    # 3. Discovery
    files_to_scan = []
    if single_file:
        files_to_scan.append(single_file)
    else:
        for folder in all_folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith(".py"):
                        files_to_scan.append(os.path.join(root, file))

    # 4. Processing
    for file_path in files_to_scan:
        file_name = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, SCAN_ROOT)
        top_folder_name = rel_path.split(os.sep)[0]
        immediate_folder = os.path.basename(os.path.dirname(file_path))
        
        nodes.append({
            "id": file_path,
            "label": file_name,
            "folder": immediate_folder,
            "folder_index": folder_colors.get(top_folder_name, -1),
            "type": "internal",
            "full_path": file_path
        })

        # AST analysis
        direct_imports, indirect_chains = analyze_file(file_path)

        # Resolve Direct Imports
        for imp in direct_imports:
            target_mod = imp.get("target") or imp.get("module")
            if resolver.is_stdlib(target_mod):
                continue

            resolved_path = resolver.resolve_module(target_mod)
            if resolved_path:
                if resolved_path == file_path: continue
                add_edge(file_path, resolved_path, imp["stmt"], "internal", nodes, edges, seen_edges, csv_rows)
            else:
                add_edge(file_path, target_mod, imp["stmt"], "leaf", nodes, edges, seen_edges, csv_rows)

        # Record Indirect
        if indirect_chains:
            # Filter indirect chains that are from STDLIB
            filtered_chains = [c for c in indirect_chains if c.split('.')[0] not in STDLIB_MODULES]
            if filtered_chains:
                indirect_dependencies[file_path] = filtered_chains

    # 5. Save and Export
    meta = {
        "folders": [os.path.basename(f) for f in all_folders],
        "folder_colors": folder_colors,
        "total_files": len([n for n in nodes if n["type"] == "internal"]),
        "total_edges": len(edges),
        "focus_folder": FOCUS_FOLDER
    }

    # Save JSON (Regular and Minified)
    save_json(OUTPUT_FILE, meta, nodes, edges, indirect_dependencies, minify=False)
    
    # Save TOON (Space Saving)
    save_toon(TOON_OUTPUT, {
        "meta": meta,
        "nodes": nodes,
        "edges": edges,
        "indirect_dependencies": indirect_dependencies
    })
    
    save_csv(CSV_OUTPUT, csv_rows)

    print(f"--- SUCCESS! ---")
    print(f"Scanned {len(all_folders)} folders and found {len(edges)} dependencies.")
    print(f"Output saved to {OUTPUT_FILE} and {TOON_OUTPUT}")

    # Generate additional reports
    df = generate_report_json(CSV_OUTPUT, REPORT_JSON)
    if df is not None:
        print(df.head(7))

def add_edge(src, target, stmt, edge_type, nodes, edges, seen_edges, csv_rows):
    eid = f"{src}->{target}"
    if eid in seen_edges: return
    
    file_name = os.path.basename(src)
    
    if edge_type == "leaf":
        if not any(n["id"] == target for n in nodes):
            nodes.append({
                "id": target,
                "label": target,
                "folder": None,
                "folder_index": -1,
                "type": "leaf"
            })
    
    edges.append({
        "source": src,
        "target": target,
        "type": edge_type,
        "import_statement": stmt
    })
    seen_edges.add(eid)
    csv_rows.append([file_name, target, stmt, edge_type])

if __name__ == "__main__":
    run_pipeline()
