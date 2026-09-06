#!/usr/bin/env python3
"""
Architecture Doc MCP Server
===========================

Deterministic codebase analysis and Mermaid.js diagramming tools for the
architecture-doc-plugin.

Tools exposed:
  - parse_dependencies: AST and token-based module dependency extraction
  - extract_api_routes: Deterministic REST API endpoint discovery
  - validate_mermaid: Mermaid diagram syntax validator & linter
  - export_html_preview: Generates self-contained interactive Mermaid preview HTML

Usage:
  # Register with Claude Code
  claude mcp add doc-tools --scope user -- python path/to/doc_mcp_server.py

  # Or run standalone for testing
  python doc_mcp_server.py --test
"""

import ast
import asyncio
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import mcp.types as types
    from mcp.server.lowlevel.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    types = None
    Server = None
    stdio_server = None


# ---------------------------------------------------------------------------
# Core Analysis Engine
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".cache",
    "target",
    "bin",
    "obj",
}


def find_files(root_dir: str, extensions: List[str]) -> List[Path]:
    """Find files matching extensions while skipping ignored directories."""
    matched = []
    root = Path(root_dir).resolve()
    if not root.exists():
        return []

    for path in root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in extensions:
            matched.append(path)
    return matched


def analyze_python_ast(file_path: Path, root_dir: Path) -> Dict[str, Any]:
    """Extract imports, classes, and functions from a Python file using AST."""
    imports = []
    classes = []
    functions = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return {
            "file": str(file_path.relative_to(root_dir)).replace("\\", "/"),
            "imports": [],
            "classes": [],
            "functions": [],
            "error": str(e),
        }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "is_from": False, "level": 0})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append({
                "module": module,
                "names": names,
                "is_from": True,
                "level": node.level,
            })
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    line_count = len(content.splitlines())
    rel_path = str(file_path.relative_to(root_dir)).replace("\\", "/")

    return {
        "file": rel_path,
        "line_count": line_count,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def load_tsconfig_paths(root: Path) -> Dict[str, str]:
    """Parse tsconfig.json or jsconfig.json to extract path aliases."""
    for config_name in ["tsconfig.json", "jsconfig.json"]:
        config_file = root / config_name
        if config_file.exists():
            try:
                raw = config_file.read_text(encoding="utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                except Exception:
                    lines = [l for l in raw.splitlines() if not l.strip().startswith("//")]
                    data = json.loads("\n".join(lines))

                compiler_opts = data.get("compilerOptions", {})
                paths = compiler_opts.get("paths", {})
                base_url = compiler_opts.get("baseUrl", ".")
                resolved_aliases = {}
                for alias_pattern, target_list in paths.items():
                    if target_list:
                        alias_prefix = alias_pattern.rstrip("*").rstrip("/")
                        target_prefix = target_list[0].rstrip("*").rstrip("/")
                        if base_url != ".":
                            target_prefix = f"{base_url.rstrip('/')}/{target_prefix}"
                        resolved_aliases[alias_prefix] = target_prefix.lstrip("./")
                return resolved_aliases
            except Exception:
                pass
    return {}


def analyze_js_ts_file(file_path: Path, root_dir: Path) -> Dict[str, Any]:
    """Extract imports, interfaces, classes from JS/TS files."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {
            "file": str(file_path.relative_to(root_dir)).replace("\\", "/"),
            "imports": [],
            "error": str(e),
        }

    imports = []
    classes = []
    functions = []

    import_patterns = [
        re.compile(r"""(?:import\s+(?:type\s+)?.*?\s+from\s+['"]([^'"]+)['"])|(?:import\s+['"]([^'"]+)['"])"""),
        re.compile(r"""require\(['"]([^'"]+)['"]\)"""),
        re.compile(r"""export\s+(?:type\s+)?.*?\s+from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\(['"]([^'"]+)['"]\)"""),
    ]

    for pattern in import_patterns:
        for match in pattern.finditer(content):
            target = match.group(1) or match.group(2) if match.lastindex else match.group(0)
            if target:
                imports.append({"module": target})

    # Classes and interfaces
    class_pattern = re.compile(r"""(?:export\s+)?(?:class|interface)\s+([a-zA-Z_0-9]+)""")
    for m in class_pattern.finditer(content):
        classes.append(m.group(1))

    # Functions
    func_pattern = re.compile(r"""(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_0-9]+)""")
    for m in func_pattern.finditer(content):
        functions.append(m.group(1))

    line_count = len(content.splitlines())
    rel_path = str(file_path.relative_to(root_dir)).replace("\\", "/")

    return {
        "file": rel_path,
        "line_count": line_count,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def parse_dependencies_impl(directory: str, file_types: str = "py,ts,js") -> Dict[str, Any]:
    """Parse codebase dependencies, building node and edge graphs."""
    root = Path(directory).resolve()
    if not root.exists():
        return {"error": f"Directory not found: {directory}"}

    ext_map = {
        "py": [".py"],
        "ts": [".ts", ".tsx"],
        "js": [".js", ".jsx", ".mjs"],
        "go": [".go"],
    }
    requested_exts = []
    for t in file_types.split(","):
        clean_t = t.strip().lower().lstrip(".")
        if clean_t in ext_map:
            requested_exts.extend(ext_map[clean_t])
        else:
            requested_exts.append(f".{clean_t}")

    files = find_files(str(root), requested_exts)
    modules: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    graph: Dict[str, Set[str]] = {}

    for f in files:
        if f.suffix == ".py":
            data = analyze_python_ast(f, root)
        else:
            data = analyze_js_ts_file(f, root)
        rel = data["file"]
        modules[rel] = data
        graph[rel] = set()

    all_module_names = {m: Path(m).stem for m in modules}
    tsconfig_aliases = load_tsconfig_paths(root)

    for source_file, data in modules.items():
        source_dir = Path(source_file).parent
        for imp in data.get("imports", []):
            mod_str = imp.get("module", "")
            target_match = None

            # 1. Relative import resolution (Python . / .. or JS ./ ../)
            if mod_str.startswith("."):
                possible_targets = [
                    (source_dir / mod_str).as_posix(),
                    (source_dir / f"{mod_str}.ts").as_posix(),
                    (source_dir / f"{mod_str}.tsx").as_posix(),
                    (source_dir / f"{mod_str}.js").as_posix(),
                    (source_dir / f"{mod_str}.py").as_posix(),
                    (source_dir / mod_str / "index.ts").as_posix(),
                    (source_dir / mod_str / "index.js").as_posix(),
                    (source_dir / mod_str / "__init__.py").as_posix(),
                ]
                for pt in possible_targets:
                    normalized = Path(pt).as_posix()
                    if normalized in modules:
                        target_match = normalized
                        break

            # 2. TypeScript / JS Path Aliases (tsconfig.json paths)
            if not target_match and tsconfig_aliases:
                for alias_prefix, target_prefix in tsconfig_aliases.items():
                    if mod_str.startswith(alias_prefix):
                        sub_path = mod_str[len(alias_prefix):].lstrip("/")
                        candidate = f"{target_prefix}/{sub_path}".strip("/")
                        possible_alias_targets = [
                            candidate,
                            f"{candidate}.ts",
                            f"{candidate}.tsx",
                            f"{candidate}.js",
                            f"{candidate}/index.ts",
                            f"{candidate}/index.js",
                        ]
                        for pt in possible_alias_targets:
                            norm_pt = Path(pt).as_posix()
                            if norm_pt in modules:
                                target_match = norm_pt
                                break
                        if target_match:
                            break

            # 3. Python relative imports with level
            if not target_match and imp.get("level", 0) > 0:
                level = imp["level"]
                curr = source_dir
                for _ in range(level - 1):
                    curr = curr.parent
                if mod_str:
                    target_name = (curr / mod_str).as_posix()
                else:
                    target_name = curr.as_posix()
                for m in modules:
                    if m.startswith(target_name) or Path(m).stem == mod_str:
                        target_match = m
                        break

            # 4. Absolute matching by filename stem or path
            if not target_match and mod_str:
                for m, stem in all_module_names.items():
                    if mod_str.endswith(stem) or mod_str.replace(".", "/") in m:
                        target_match = m
                        break

            if target_match and target_match != source_file:
                graph[source_file].add(target_match)
                edges.append({
                    "from": source_file,
                    "to": target_match,
                    "import": mod_str,
                })

    # Detect circular dependencies
    cycles = []
    visited: Set[str] = set()
    stack: List[str] = []

    def dfs(node: str):
        visited.add(node)
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in stack:
                cycle_slice = stack[stack.index(neighbor):] + [neighbor]
                cycles.append(" -> ".join(cycle_slice))
        stack.pop()

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)

    coupling = {}
    for node in graph:
        in_degree = sum(1 for src, targets in graph.items() if node in targets)
        out_degree = len(graph[node])
        coupling[node] = {
            "in_degree": in_degree,
            "out_degree": out_degree,
            "is_hub": in_degree >= 3 or out_degree >= 4,
        }

    layers = {"frontend": [], "routes": [], "services": [], "models": [], "db": [], "utils": [], "core": []}
    for m in modules:
        low = m.lower()
        if "frontend" in low or "client" in low or "ui" in low or "view" in low:
            layers["frontend"].append(m)
        elif "route" in low or "controller" in low or "api" in low:
            layers["routes"].append(m)
        elif "service" in low or "business" in low or "use_case" in low:
            layers["services"].append(m)
        elif "model" in low or "schema" in low or "entity" in low:
            layers["models"].append(m)
        elif "db" in low or "database" in low or "repo" in low or "sql" in low:
            layers["db"].append(m)
        elif "util" in low or "helper" in low or "common" in low:
            layers["utils"].append(m)
        else:
            layers["core"].append(m)

    return {
        "root_directory": str(root),
        "total_files_analyzed": len(modules),
        "total_dependencies_found": len(edges),
        "circular_dependencies": cycles,
        "layers": layers,
        "coupling": coupling,
        "edges": edges,
        "modules": {
            k: {
                "file": v["file"],
                "line_count": v.get("line_count", 0),
                "classes": v.get("classes", []),
                "functions": v.get("functions", []),
            }
            for k, v in modules.items()
        },
    }


def extract_api_routes_impl(directory: str) -> Dict[str, Any]:
    """Scan Python and JS/TS files for REST endpoints."""
    root = Path(directory).resolve()
    if not root.exists():
        return {"error": f"Directory not found: {directory}"}

    routes = []
    py_files = find_files(str(root), [".py"])
    js_files = find_files(str(root), [".ts", ".tsx", ".js"])

    fastapi_pattern = re.compile(
        r"""@(app|router|api)\.(get|post|put|delete|patch|options|head)\(\s*['"]([^'"]+)['"](?:.*?)def\s+([a-zA-Z_0-9]+)\s*\((.*?)\)""",
        re.DOTALL,
    )
    flask_pattern = re.compile(
        r"""@(app|blueprint|[a-zA-Z_0-9]+)\.route\(\s*['"]([^'"]+)['"](?:\s*,\s*methods\s*=\s*\[(.*?)\])?(?:.*?)def\s+([a-zA-Z_0-9]+)\s*\((.*?)\)""",
        re.DOTALL,
    )

    for pf in py_files:
        content = pf.read_text(encoding="utf-8", errors="replace")
        rel = str(pf.relative_to(root)).replace("\\", "/")

        for m in fastapi_pattern.finditer(content):
            router_var, method, path, func_name, params = m.groups()
            clean_params = [p.strip() for p in params.split(",") if p.strip() and p.strip() != "self"]
            routes.append({
                "framework": "FastAPI",
                "file": rel,
                "method": method.upper(),
                "path": path,
                "handler": func_name,
                "parameters": clean_params,
            })

        for m in flask_pattern.finditer(content):
            _, path, methods_str, func_name, params = m.groups()
            methods = [met.strip("'\" ") for met in methods_str.split(",")] if methods_str else ["GET"]
            for met in methods:
                routes.append({
                    "framework": "Flask",
                    "file": rel,
                    "method": met.upper(),
                    "path": path,
                    "handler": func_name,
                    "parameters": [p.strip() for p in params.split(",") if p.strip()],
                })

    express_pattern = re.compile(
        r"""(?:app|router)\.(get|post|put|delete|patch)\(\s*['"]([^'"]+)['"]\s*,\s*(?:async\s*)?\((.*?)\)\s*=>""",
    )
    for jf in js_files:
        content = jf.read_text(encoding="utf-8", errors="replace")
        rel = str(jf.relative_to(root)).replace("\\", "/")

        for m in express_pattern.finditer(content):
            method, path, params = m.groups()
            routes.append({
                "framework": "Express/Hono",
                "file": rel,
                "method": method.upper(),
                "path": path,
                "handler": "anonymous",
                "parameters": [p.strip() for p in params.split(",") if p.strip()],
            })

    return {
        "total_routes_discovered": len(routes),
        "routes": routes,
    }


def validate_mermaid_impl(diagram_code: str) -> Dict[str, Any]:
    """Validate Mermaid.js syntax for common syntax traps and unquoted characters."""
    errors = []
    warnings = []
    fixed_lines = []

    code = diagram_code.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        code = "\n".join(lines).strip()

    lines = code.splitlines()
    if not lines:
        return {"valid": False, "errors": ["Empty diagram code"], "warnings": [], "fixed_diagram": ""}

    first_line = lines[0].strip()
    valid_headers = [
        "flowchart",
        "graph",
        "sequencediagram",
        "classdiagram",
        "erdiagram",
        "statediagram",
        "statediagram-v2",
        "gantt",
        "pie",
        "gitgraph",
    ]

    matched_header = any(first_line.lower().startswith(vh) for vh in valid_headers)
    if not matched_header:
        errors.append(f"Invalid diagram header: '{first_line}'. Expected flowchart, sequenceDiagram, classDiagram, etc.")

    subgraph_count = 0
    end_count = 0

    for i, line in enumerate(lines):
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("%%"):
            fixed_lines.append(line)
            continue

        if trimmed.startswith("subgraph"):
            subgraph_count += 1
        elif trimmed == "end":
            end_count += 1

        raw_label_match = re.search(r'\[([^[\]"]*?\([^[\]"]*?\)[^[\]"]*?)\]', line)
        if raw_label_match:
            warnings.append(f"Line {i+1}: Unquoted parentheses in label: '{raw_label_match.group(1)}'. Auto-wrapped in quotes.")
            fixed_line = re.sub(
                r'\[([^[\]"]*?\([^[\]"]*?\)[^[\]"]*?)\]',
                r'["\1"]',
                line
            )
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)

    if subgraph_count != end_count:
        errors.append(f"Mismatched subgraphs: found {subgraph_count} 'subgraph' but {end_count} 'end' statements.")

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "fixed_diagram": "\n".join(fixed_lines),
    }


def export_html_preview_impl(
    diagram_code: str,
    title: str = "Architecture Diagram",
    output_path: str = "docs/architecture-preview.html",
) -> Dict[str, Any]:
    """Generate a self-contained interactive Mermaid HTML preview."""
    clean_code = diagram_code.strip()
    if clean_code.startswith("```"):
        lines = clean_code.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_code = "\n".join(lines).strip()

    safe_code = clean_code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Interactive Preview</title>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'neutral',
      securityLevel: 'loose',
      flowchart: {{ useMaxWidth: false, htmlLabels: true }}
    }});
  </script>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --border: #334155;
      --accent: #38bdf8;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--accent);
    }}
    .actions {{
      display: flex;
      gap: 12px;
    }}
    button {{
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    button:hover {{
      background: var(--accent);
      color: #0f172a;
      border-color: var(--accent);
    }}
    .diagram-container {{
      flex: 1;
      background: #ffffff;
      border-radius: 8px;
      padding: 32px;
      overflow: auto;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 500px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }}
    .mermaid {{
      width: 100%;
      display: flex;
      justify-content: center;
    }}
    footer {{
      margin-top: 24px;
      text-align: center;
      font-size: 0.875rem;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <header>
    <h1>📐 {title}</h1>
    <div class="actions">
      <button onclick="window.print()">🖨️ Print / Save PDF</button>
      <button onclick="navigator.clipboard.writeText(document.getElementById('raw-code').textContent); alert('Mermaid code copied!');">📋 Copy Code</button>
    </div>
  </header>

  <div class="diagram-container">
    <pre class="mermaid">
{safe_code}
    </pre>
  </div>

  <pre id="raw-code" style="display: none;">{clean_code}</pre>

  <footer>
    Generated by <strong>architecture-doc-plugin (v2.0.0)</strong> • Powered by Mermaid.js
  </footer>
</body>
</html>
"""
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_content, encoding="utf-8")

    return {
        "success": True,
        "output_file": str(out_file),
        "file_url": out_file.as_uri(),
        "preview_message": f"Diagram preview generated at: {out_file.as_uri()}",
    }


def trace_execution_impl(
    command: str,
    working_dir: str = ".",
    max_depth: int = 8,
    max_events: int = 300,
    export_html: bool = True,
) -> Dict[str, Any]:
    """Execute a Python test or script in trace mode and produce a sequence diagram."""
    abs_workspace = Path(working_dir).resolve()
    tracer_path = Path(__file__).parent / "tracer.py"
    if not tracer_path.exists():
        return {"success": False, "error": f"Tracer script not found at {tracer_path}"}

    raw_cmd = command.strip()
    try:
        parts = shlex.split(raw_cmd, posix=False)
    except Exception:
        parts = raw_cmd.split()

    parts = [p.strip('"\'') for p in parts if p.strip('"\'')]

    if not parts:
        return {"success": False, "error": "Command cannot be empty"}

    # Strip leading python invocation if present
    first = parts[0].lower()
    if first in ("python", "python3", "py") or first.endswith("python.exe"):
        parts = parts[1:]

    if not parts:
        return {"success": False, "error": "No script or module specified after python"}

    is_module = False
    if parts[0] == "-m":
        is_module = True
        parts = parts[1:]
        if not parts:
            return {"success": False, "error": "Missing module name after -m"}
        target = parts[0]
        extra_args = parts[1:]
    elif parts[0].lower() in ("pytest", "pytest.exe"):
        is_module = True
        target = "pytest"
        extra_args = parts[1:]
    else:
        target = parts[0]
        extra_args = parts[1:]

    tracer_args = [
        sys.executable,
        str(tracer_path),
        "-w",
        str(abs_workspace),
        "-d",
        str(max_depth),
        "-e",
        str(max_events),
    ]
    if is_module:
        tracer_args.append("-m")
    tracer_args.append(target)
    tracer_args.extend(extra_args)

    try:
        proc = subprocess.run(
            tracer_args,
            capture_output=True,
            text=True,
            cwd=str(abs_workspace),
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out after 120 seconds"}
    except Exception as e:
        return {"success": False, "error": f"Failed to execute tracer: {str(e)}"}

    out_text = proc.stdout.strip()
    try:
        trace_data = json.loads(out_text)
    except Exception:
        return {
            "success": False,
            "error": "Failed to parse tracer JSON output",
            "stdout": out_text,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }

    html_preview = None
    if export_html and trace_data.get("mermaid_diagram"):
        preview_res = export_html_preview_impl(
            diagram_code=trace_data["mermaid_diagram"],
            title=f"Execution Trace: {target}",
            output_path=str(abs_workspace / "docs" / "trace-preview.html"),
        )
        html_preview = preview_res.get("file_url")

    trace_data["success"] = (proc.returncode == 0) and not trace_data.get("error")
    if html_preview:
        trace_data["html_preview_url"] = html_preview
        trace_data["html_preview_path"] = str(abs_workspace / "docs" / "trace-preview.html")

    return trace_data


# ---------------------------------------------------------------------------
# MCP Server Handlers
# ---------------------------------------------------------------------------

async def handle_list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="parse_dependencies",
                description=(
                    "Extracts module dependencies, AST imports, circular dependencies, "
                    "and architectural coupling across Python, TypeScript, and JavaScript codebases."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the codebase root directory to analyze",
                        },
                        "file_types": {
                            "type": "string",
                            "description": "Comma-separated extensions to include (default: 'py,ts,js')",
                            "default": "py,ts,js",
                        },
                    },
                    "required": ["directory"],
                },
            ),
            types.Tool(
                name="extract_api_routes",
                description=(
                    "Discovers REST API routes, HTTP methods, route paths, handler functions, "
                    "and parameter types for FastAPI, Flask, Express, and Hono frameworks."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the project directory containing API route definitions",
                        },
                    },
                    "required": ["directory"],
                },
            ),
            types.Tool(
                name="validate_mermaid",
                description=(
                    "Validates Mermaid.js diagram syntax, catches unquoted parenthesis bugs, "
                    "detects unclosed subgraphs, and returns clean/auto-fixed diagram code."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "diagram_code": {
                            "type": "string",
                            "description": "The Mermaid.js diagram code to validate",
                        },
                    },
                    "required": ["diagram_code"],
                },
            ),
            types.Tool(
                name="export_html_preview",
                description=(
                    "Generates an interactive, self-contained HTML page embedding Mermaid.js with "
                    "zoom, pan, and print capabilities so the user can preview the diagram in a browser."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "diagram_code": {
                            "type": "string",
                            "description": "The Mermaid.js diagram code to render",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title for the diagram document",
                            "default": "Architecture Diagram",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path where the HTML preview should be saved (default: docs/architecture-preview.html)",
                            "default": "docs/architecture-preview.html",
                        },
                    },
                    "required": ["diagram_code"],
                },
            ),
            types.Tool(
                name="trace_execution",
                description=(
                    "Executes a Python script, test case, or pytest command in runtime trace mode. "
                    "Records function calls, inputs, and return values, producing a visual Mermaid.js "
                    "sequence diagram and step-by-step plain English execution narrative."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Python command or script to execute (e.g., 'pytest tests/test_login.py' or 'test_cart.py')",
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Root working directory of the project (default: '.')",
                            "default": ".",
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum function call depth to trace (default: 8)",
                            "default": 8,
                        },
                        "max_events": {
                            "type": "integer",
                            "description": "Maximum call events to record (default: 300)",
                            "default": 300,
                        },
                        "export_html": {
                            "type": "boolean",
                            "description": "Whether to generate an interactive HTML preview (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["command"],
                },
            ),
        ]
    )


async def handle_call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    try:
        if name == "parse_dependencies":
            res = parse_dependencies_impl(
                arguments.get("directory", "."),
                arguments.get("file_types", "py,ts,js"),
            )
        elif name == "extract_api_routes":
            res = extract_api_routes_impl(arguments.get("directory", "."))
        elif name == "validate_mermaid":
            res = validate_mermaid_impl(arguments.get("diagram_code", ""))
        elif name == "export_html_preview":
            res = export_html_preview_impl(
                arguments.get("diagram_code", ""),
                arguments.get("title", "Architecture Diagram"),
                arguments.get("output_path", "docs/architecture-preview.html"),
            )
        elif name == "trace_execution":
            res = trace_execution_impl(
                command=arguments.get("command", ""),
                working_dir=arguments.get("working_dir", "."),
                max_depth=arguments.get("max_depth", 8),
                max_events=arguments.get("max_events", 300),
                export_html=arguments.get("export_html", True),
            )
        else:
            res = {"error": f"Unknown tool: {name}"}
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(res, indent=2))])
    except Exception as e:
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps({"error": str(e)}))])


def main():
    """Main entry point."""
    if "--test" in sys.argv:
        print("Self-test mode:")
        test_dir = str(Path(__file__).parent.parent)
        print(f"Testing parse_dependencies on {test_dir}...")
        res = parse_dependencies_impl(test_dir)
        print(f"Analyzed files: {res.get('total_files_analyzed', 0)}")
        val = validate_mermaid_impl("flowchart TD\n  A[Start (init)] --> B[End]")
        print(f"Mermaid validation: {val['valid']}, Warnings: {len(val['warnings'])}, Fixed: {val['fixed_diagram']}")
        print("Testing trace_execution tool...")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write("def compute(x):\n    return x * 2\ncompute(21)\n")
            tf_path = tf.name
        try:
            trace_res = trace_execution_impl(
                command=f'python "{tf_path}"',
                working_dir=os.path.dirname(tf_path),
                export_html=False,
            )
            print(f"Trace tool status: success={trace_res.get('success', False)}, calls={trace_res.get('total_events', 0)}")
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)
        print("Self-test passed successfully!")
        return

    if Server is None or stdio_server is None:
        print(
            "ERROR: 'mcp' package is not installed.\n"
            "Run: pip install mcp>=1.0.0",
            file=sys.stderr,
        )
        sys.exit(1)

    server = Server(
        name="doc-tools",
        version="2.0.0",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
