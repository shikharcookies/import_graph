import os
import ast
import json

# MRFLEX Project Integration: Scan under 'Deploy/' folder
# This will auto-discover the 20-30 folders you mentioned
SCAN_ROOT = "Deploy" 
FOCUS_FOLDER = "SPEScripts" # Primary folder for user entry
OUTPUT_FILE = "graph_explorer/dependency_data.json"
EXCLUDE_FOLDERS = [".venv", "__pycache__", ".git", "graph_explorer"]

def parse_dependencies():
    # 1. Discover all folders under the scan root
    if not os.path.exists(SCAN_ROOT):
        print(f"Error: '{SCAN_ROOT}' folder not found. Please ensure you're in the MRFLEX root.")
        return

    all_folders = [os.path.join(SCAN_ROOT, d) for d in os.listdir(SCAN_ROOT) 
                   if os.path.isdir(os.path.join(SCAN_ROOT, d)) and d not in EXCLUDE_FOLDERS]
    
    # 2. Build a registry for mapping module names to actual file paths
    # We index files from ALL folders in 'Deploy/'
    module_registry = {}
    for folder in all_folders:
        for root, _, files in os.walk(folder):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    # Support 'import Folder.Module'
                    full_mod = file_path.replace(os.sep, ".").replace(".py", "")
                    if SCAN_ROOT in full_mod:
                        full_mod = full_mod.split(f"{SCAN_ROOT}.")[1]
                    module_registry[full_mod] = file_path
                    
                    # Support 'import Module' (Flat style)
                    base_mod = os.path.splitext(file)[0]
                    if base_mod not in module_registry:
                        module_registry[base_mod] = file_path

    nodes = []
    edges = []
    folder_colors = {os.path.basename(f): i for i, f in enumerate(all_folders)}

    def resolve_module(module_name):
        if module_name in module_registry:
            return module_registry[module_name]
        return None

    # 3. Process all files in the SCAN_ROOT
    for folder in all_folders:
        folder_name = os.path.basename(folder)
        for root, _, files in os.walk(folder):
            for file in files:
                if not file.endswith(".py"): continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                except:
                    continue

                nodes.append({
                    "id": file_path,
                    "label": file,
                    "folder": folder_name,
                    "folder_index": folder_colors.get(folder_name, -1),
                    "type": "internal",
                    "full_path": file_path
                })

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            target = alias.name
                            stmt = f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
                            add_edge(file_path, target, stmt)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            names = ", ".join([a.name for a in node.names])
                            stmt = f"from {node.module} import {names}"
                            add_edge(file_path, node.module, stmt)

    def add_edge(src, target_mod, stmt):
        resolved = resolve_module(target_mod)
        if resolved:
            if resolved == src: return
            edges.append({
                "source": src,
                "target": resolved,
                "type": "internal",
                "import_statement": stmt
            })
        else:
            if target_mod not in [n["id"] for n in nodes]:
                nodes.append({"id": target_mod, "label": target_mod, "folder": None, "folder_index": -1, "type": "leaf"})
            edges.append({"source": src, "target": target_mod, "type": "leaf", "import_statement": stmt})

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
                "total_edges": len(unique_edges)
            },
            "nodes": nodes,
            "edges": unique_edges
        }, f, indent=2)

if __name__ == "__main__":
    parse_dependencies()

if __name__ == "__main__":
    parse_dependencies()
