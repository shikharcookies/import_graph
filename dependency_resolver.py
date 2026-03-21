import os
import sys

# Programs use config directly
from config import STDLIB_MODULES, SCAN_ROOT

class Resolver:
    def __init__(self, all_folders, single_file=None):
        self.module_registry = {}
        self.all_folders = all_folders
        self.single_file = single_file
        self.build_registry()

    def build_registry(self):
        """Map module names to file paths."""
        for folder in self.all_folders:
            for root, _, files in os.walk(folder):
                if self.single_file:
                    files = [os.path.basename(self.single_file)]
                    root = os.path.dirname(self.single_file)
                
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        # Support 'import Folder.Module'
                        full_mod = file_path.replace(os.sep, ".").replace(".py", "")
                        if SCAN_ROOT in full_mod:
                            full_mod = full_mod.split(f"{SCAN_ROOT}.")[1]
                        self.module_registry[full_mod] = file_path

                        base_mod = os.path.splitext(file)[0]
                        if base_mod not in self.module_registry:
                            self.module_registry[base_mod] = file_path

    def resolve_module(self, module_name):
        return self.module_registry.get(module_name)

    def is_stdlib(self, module_name):
        return module_name in STDLIB_MODULES
