import ast
import os

# --- Configuration ---
EXCLUDE = {"migrations", "static", "templates", "scripts", "__pycache__"}
BASE_DIR = "app"
SKIP_ROOT = True

# Specify which top-level variables/aliases to include
INCLUDE_VARIABLES = {"DB"}  # add other aliases you want exposed


# --- Helper function ---
def get_public_names(file_path: str) -> list[str]:
    """
    Return all public classes, functions, and selected top-level variables.
    Skips names starting with _ and ignores other variables.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        node = ast.parse(f.read(), filename=file_path)

    names: list[str] = []

    for n in node.body:
        # classes and functions
        if isinstance(n, (ast.ClassDef, ast.FunctionDef)):
            if not n.name.startswith("_"):
                names.append(n.name)

        # top-level variables (selective)
        elif isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id in INCLUDE_VARIABLES:
                    names.append(target.id)

    return names


# --- Walk directories ---
for root, dirs, files in os.walk(BASE_DIR):
    if any(ex in root.split(os.sep) for ex in EXCLUDE):
        continue
    if SKIP_ROOT and os.path.abspath(root) == os.path.abspath(BASE_DIR):
        continue

    py_files = [f for f in files if f.endswith(".py") and f != "__init__.py"]
    if not py_files:
        continue

    init_path = os.path.join(root, "__init__.py")
    module_map: dict[str, list[str]] = {}

    for file in py_files:
        file_path = os.path.join(root, file)
        names = get_public_names(file_path)
        if names:
            module_name = os.path.splitext(file)[0]
            module_map[module_name] = names

    if not module_map:
        continue

    # --- Build __init__.py content ---
    content_lines: list[str] = []

    # Imports first (merge per module)
    for module, names in sorted(module_map.items()):
        names_str = ", ".join(names)
        content_lines.append(f"from .{module} import {names_str}\n")

    content_lines.append("\n")

    # __all__ at the bottom
    all_names = [name for names in module_map.values() for name in names]
    content_lines.append(f"__all__ = {all_names!r}\n")

    # Write the __init__.py
    with open(init_path, "w", encoding="utf-8") as f:
        f.writelines(content_lines)

    print(f"Created {init_path} with {len(all_names)} public items")
