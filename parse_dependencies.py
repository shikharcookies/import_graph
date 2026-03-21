import os
import ast
import json
import warnings
import sys
import csv
import pandas as pd
import enrich_graph


# Programmatically get all Python standard library and built-in module names
# This requires Python 3.10+; for older versions, it defaults to builtin names
STDLIB_MODULES = getattr(sys, "stdlib_module_names", set()) | set(sys.builtin_module_names)

# Configuration
SCAN_ROOT = sys.argv[1] if len(sys.argv) > 1 else "Deploy"
FOCUS_FOLDER = sys.argv[2] if len(sys.argv) > 2 else "SPEScripts"
OUTPUT_FILE = "graph_explorer/dependency_data.json"
CSV_OUTPUT = "graph_explorer/import_report.csv"
EXCLUDE_FOLDERS = [".venv", "__pycache__", ".git", "graph_explorer"]

def get_full_attr(node):
    """Recursive helper to extract full attribute chains like LibFactory.Manager.get"""
    if isinstance(node, ast.Attribute):
        val = get_full_attr(node.value)
        if val:
            return f"{val}.{node.attr}"
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Call):
        return get_full_attr(node.func)
    return None

def parse_dependencies():
    if os.path.isfile(SCAN_ROOT):
        single_file = SCAN_ROOT
        scan_root_dir = os.path.dirname(SCAN_ROOT)
    else:
        single_file = None
        scan_root_dir = SCAN_ROOT

    is_single_file = bool(single_file)

    if not os.path.exists(SCAN_ROOT):
        print(f"Error: '{SCAN_ROOT}' folder not found. Please ensure you're in the MRFLEX root or pass full path.")
        return

    # Discover folders
    if single_file:
        all_folders = [scan_root_dir]
    else:
        all_folders = [os.path.join(SCAN_ROOT, d) for d in os.listdir(SCAN_ROOT)
                       if os.path.isdir(os.path.join(SCAN_ROOT, d)) and d not in EXCLUDE_FOLDERS]

    module_registry = {}
    
    # Map modules to file paths
    for folder in all_folders:
        for root, _, files in os.walk(folder):
            if single_file:
                files = [os.path.basename(single_file)]
                root = os.path.dirname(single_file)
            
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    # Support 'import Folder.Module'
                    full_mod = file_path.replace(os.sep, ".").replace(".py", "")
                    if SCAN_ROOT in full_mod:
                        full_mod = full_mod.split(f"{SCAN_ROOT}.")[1]
                    module_registry[full_mod] = file_path

                    base_mod = os.path.splitext(file)[0]
                    if base_mod not in module_registry:
                        module_registry[base_mod] = file_path

    nodes = []
    edges = []
    csv_rows = []
    indirect_dependencies = {}
    folder_colors = {os.path.basename(f): i for i, f in enumerate(all_folders)}

    def resolve_module(module_name):
        if module_name in module_registry:
            return module_registry[module_name]
        return None

    def add_edge(src, target_mod, stmt):
        # FILTER: Skip standard library and built-in modules
        if target_mod in STDLIB_MODULES:
            return

        file_name = os.path.basename(src)
        
        if not is_single_file:
            resolved = resolve_module(target_mod)
            if resolved:
                if resolved == src:
                    return
                
                edges.append({
                    "source": src,
                    "target": resolved,
                    "type": "internal",
                    "import_statement": stmt
                })
                csv_rows.append([file_name, target_mod, stmt, "internal"])
                return

        # If not resolved or target_mod not in nodes, treat as external/leaf
        if target_mod not in [n["id"] for n in nodes]:
            nodes.append({
                "id": target_mod,
                "label": target_mod,
                "folder": None,
                "folder_index": -1,
                "type": "leaf"
            })
        
        edges.append({
            "source": src,
            "target": target_mod,
            "type": "leaf",
            "import_statement": stmt
        })
        csv_rows.append([file_name, target_mod, stmt, "external"])

    # Collect files to scan
    files_to_scan = []
    if single_file:
        files_to_scan.append(single_file)
    else:
        for folder in all_folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith(".py"):
                        files_to_scan.append(os.path.join(root, file))

    # Parse each file
    for file_path in files_to_scan:
        file_name = os.path.basename(file_path)
        
        # Determine the top-level folder name under SCAN_ROOT for coloring
        rel_path = os.path.relpath(file_path, SCAN_ROOT)
        top_folder_name = rel_path.split(os.sep)[0]
        
        # For the display label, we use the immediate parent folder
        immediate_folder = os.path.basename(os.path.dirname(file_path))
        
        nodes.append({
            "id": file_path,
            "label": file_name,
            "folder": immediate_folder,
            "folder_index": folder_colors.get(top_folder_name, -1),
            "type": "internal",
            "full_path": file_path
        })

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source_code = f.read()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    tree = ast.parse(source_code)
            
            # Track direct imports to filter indirect chains
            direct_imports = set()
            file_indirect_deps = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name
                        direct_imports.add(alias.asname or target)
                        stmt = f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                        add_edge(file_path, target, stmt)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            direct_imports.add(alias.asname or alias.name)
                        names = ", ".join([a.name for a in node.names])
                        stmt = f"from {node.module} import {names}"
                        add_edge(file_path, node.module, stmt)
                
                # Capture Indirect Dependencies (Attribute Chains)
                elif isinstance(node, (ast.Attribute, ast.Call)):
                    chain = get_full_attr(node)
                    if chain:
                        root_obj = chain.split('.')[0]
                        # Only include if the root is a known direct import AND NOT a built-in
                        if root_obj in direct_imports and root_obj not in STDLIB_MODULES:
                            file_indirect_deps.add(chain)

            if file_indirect_deps:
                indirect_dependencies[file_path] = sorted(list(file_indirect_deps))
        except Exception:
            continue

    # Save data
    unique_edges = []
    seen = set()
    for e in edges:
        eid = f"{e['source']}->{e['target']}"
        if eid not in seen:
            unique_edges.append(e)
            seen.add(eid)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "meta": {
                "folders": [os.path.basename(f) for f in all_folders],
                "folder_colors": folder_colors,
                "total_files": len([n for n in nodes if n["type"] == "internal"]),
                "total_edges": len(unique_edges),
                "focus_folder": FOCUS_FOLDER
            },
            "nodes": nodes,
            "edges": unique_edges,
            "indirect_dependencies": indirect_dependencies
        }, f, indent=2)

    with open(CSV_OUTPUT, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["file", "imported_module", "import_statement", "type"])
        writer.writerows(csv_rows)

    print(f"--- SUCCESS! ---")
    print(f"Generated {OUTPUT_FILE}")
    print(f"Generated {CSV_OUTPUT}")
    print(f"Scanned {len(all_folders)} folders and found {len(unique_edges)} dependencies.")

def modify_json(df):
    grouped = (
        df.groupby("file")
        .apply(lambda g: g[["imported_module", "import_statement", "type"]]
               .to_dict(orient="records"))
        .to_dict()
    )
    
    json_str = json.dumps(grouped, indent=2)
    with open("graph_explorer/import_report.json", "w") as f:
        f.write(json_str)

if __name__ == "__main__":
    parse_dependencies()
    
    if os.path.exists(CSV_OUTPUT):
        df = pd.read_csv(CSV_OUTPUT)
        print(df.head(7))
        modify_json(df)
        enrich_graph.main()
        