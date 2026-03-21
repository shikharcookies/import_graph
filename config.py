import sys

# Programmatically get all Python standard library and built-in module names
STDLIB_MODULES = getattr(sys, "stdlib_module_names", set()) | set(sys.builtin_module_names)

# CLI Configuration
SCAN_ROOT = sys.argv[1] if len(sys.argv) > 1 else "Deploy"
FOCUS_FOLDER = sys.argv[2] if len(sys.argv) > 2 else "SPEScripts"

# Paths
OUTPUT_FILE = "graph_explorer/dependency_data.json"
CSV_OUTPUT = "graph_explorer/import_report.csv"
REPORT_JSON = "graph_explorer/import_report.json"

# Exclusions
EXCLUDE_FOLDERS = [".venv", "__pycache__", ".git", "graph_explorer"]
