# MRFLEX Integration Guide

To use this tool within your MRFLEX project, follow these steps:

## 1. Integration Setup

- Copy the `graph_explorer/` folder, `parse_dependencies.py`, and `.gitignore` into your MRFLEX project root.
- Ensure your structure looks like this:
  ```
  MRFLEX/
  ├── Deploy/            # (Your existing folder with 20-30 subfolders)
  │   ├── SPEScripts/    # (Target folder for search)
  │   └── ...            # (Other folders like FlexEngines, etc.)
  ├── graph_explorer/    # (Visualizer UI)
  └── parse_dependencies.py
  ```

## 2. Generating Data

- Open your terminal in the MRFLEX root.
- Run the parser:
  ```bash
  python3 parse_dependencies.py
  ```
- This will scan all subfolders under `Deploy/` and generate the dependency map in `graph_explorer/dependency_data.json`.

## 3. Using the Visualizer

- Open `graph_explorer/index.html` in your browser.
- **Upload:** Use the upload button to select the `dependency_data.json` you just generated.
- **Search:** Type the name of a file from `SPEScripts` (e.g., `SpePyFixedIncomeFalconSecuredGapping.py`) and press **Enter**.
- **Navigate:** Click on any import node to see its own dependencies and travel through the project.



previous issue : 

**Category 1 — Crashes at runtime:** `process_file()` and** **`build_static()` both open and parse the same file independently — if anything changes between the two calls, the second** **`open()` raises** **`FileNotFoundError`.** **`export()`hardcodes** **`"trace_output.json"` with no** **`os.makedirs()` guard, so it crashes if the working directory is read-only. Both** **`ast.parse()` calls are still missing** **`warnings.catch_warnings()` suppression, which is the exact noisy output from your screenshot.

**Category 2 — Wrong output, silent data bugs:** `add_edge()` has no deduplication check, so the same** **`src→dst` pair gets appended multiple times — the frontend receives redundant edges and draws overlapping arrows.** **`connect_cross_file_calls()` builds** **`call_id` using a different** **`nid()` pattern than** **`process_call()` does, so the node it looks for never exists in the** **`nodes` dict and every cross-file edge is silently dropped by** **`add_edge()`. For** **`from X import Y` statements, only the module** **`X` is recorded — the specific symbol** **`Y` is discarded, meaning two files importing different names from the same module collapse into one identical node and one import is lost.

**Category 3 — Performance and structural waste:** Every file is read and parsed by** **`ast.parse()` twice — once in** **`process_file()` and once in** **`build_static()`. The fix is to parse once and pass the tree as an argument.** **`find_python_files()` is also called twice for directories — once inside** **`run()` and once in** **`process_target()` — meaning two full** **`os.walk()` passes over the same folder. The edge categorisation from the original (`import_edges`,** **`contains_edges`,** **`external_edges`) was removed in the cleanup, so the frontend now gets a flat** **`edges` list with no way to render different visual styles per edge type.

**Category 4 — Missing features:** `YOUR_FILES` is now populated correctly but** **`export()` and the final print still don't use it — the** **`files_processed` and** **`files_list` stats that were in the original output schema are gone from the JSON entirely.
