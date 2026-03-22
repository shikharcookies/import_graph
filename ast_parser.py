import ast
import warnings

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

def analyze_file(file_path):
    """Parses a file and returns its direct imports and indirect dependencies."""
    direct_imports = []
    indirect_chains = set()
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(source_code)
        
        # Track aliases to help filter indirect chains
        import_aliases = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    asname = alias.asname or target
                    import_aliases.add(asname)
                    direct_imports.append({
                        "type": "import",
                        "target": target,
                        "asname": alias.asname,
                        "stmt": f"import {target}" + (f" as {alias.asname}" if alias.asname else "")
                    })
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        import_aliases.add(alias.asname or alias.name)
                    names = ", ".join([a.name for a in node.names])
                    direct_imports.append({
                        "type": "from",
                        "module": node.module,
                        "names": [a.name for a in node.names],
                        "stmt": f"from {node.module} import {names}"
                    })
            
            # Capture Indirect Dependencies (Attribute Chains)
            elif isinstance(node, (ast.Attribute, ast.Call)):
                chain = get_full_attr(node)
                if chain:
                    root_obj = chain.split('.')[0]
                    # Only include if root is an imported alias
                    if root_obj in import_aliases:
                        indirect_chains.add(chain)

        return direct_imports, sorted(list(indirect_chains))
    except Exception:
        return [], []
