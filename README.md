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
