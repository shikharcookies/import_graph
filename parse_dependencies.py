import os
import ast
import json
import warnings

# MRFLEX Project Integration: Scan under 'Deploy/' folder
# This will auto-discover the 20-30 folders you mentioned
SCAN_ROOT = "Deploy" 
FOCUS_FOLDER = "SPEScripts" # Primary folder for user entry
OUTPUT_FILE = "graph_explorer/dependency_data.json"
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
    indirect_dependencies = {}
    folder_colors = {os.path.basename(f): i for i, f in enumerate(all_folders)}

    def resolve_module(module_name):
        if module_name in module_registry:
            return module_registry[module_name]
        return None

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

    # 3. Process all files in the SCAN_ROOT
    for folder in all_folders:
        folder_name = os.path.basename(folder)
        for root, _, files in os.walk(folder):
            for file in files:
                if not file.endswith(".py"): continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            tree = ast.parse(source_code)
                except Exception as e:
                    # Optional: print(f"Skipping {file_path} due to error: {e}")
                    continue

                nodes.append({
                    "id": file_path,
                    "label": file,
                    "folder": folder_name,
                    "folder_index": folder_colors.get(folder_name, -1),
                    "type": "internal",
                    "full_path": file_path
                })

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
                            # Only include if the root is a known direct import
                            if root_obj in direct_imports:
                                file_indirect_deps.add(chain)

                if file_indirect_deps:
                    indirect_dependencies[file_path] = sorted(list(file_indirect_deps))

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
            "edges": unique_edges,
            "indirect_dependencies": indirect_dependencies
        }, f, indent=2)
    
    print(f"--- SUCCESS! ---")
    print(f"Generated {OUTPUT_FILE}")
    print(f"Scanned {len(all_folders)} folders and found {len(unique_edges)} dependencies.")

if __name__ == "__main__":
    parse_dependencies()
