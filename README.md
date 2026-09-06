# Architecture Doc Plugin (v2.0.0)

A production-grade automated codebase documentation and architecture visualization plugin for Claude Code.

Extract real AST module dependency graphs, discover REST API endpoints deterministically, generate validated Mermaid.js diagrams, export interactive HTML browser previews, and automate documentation freshness with pre-commit hooks.

---

## ⚡ 60-Second Quickstart

### 1. Install Plugin
```bash
/plugin marketplace add ./path/to/architecture-doc-plugin
/plugin install architecture-doc-plugin
```

### 2. (Optional, Recommended) Enable Bundled MCP Server
The plugin includes a dedicated AST code analysis and diagram preview MCP server:
```bash
# Install lightweight dependencies
pip install -r mcp/requirements.txt

# Register MCP server with Claude Code
claude mcp add doc-tools --scope user -- python mcp/doc_mcp_server.py
```

### 3. Immediate Hands-On Test on Bundled Sample Project
```bash
# Generate architecture diagram for the sample microservice:
/gen-diagram examples/sample_project

# Scan and document all REST endpoints:
/api-spec examples/sample_project

# Deep-dive into a specific service file:
/explain-file examples/sample_project/services/order_service.py
```

---

## 📦 What's Included

```
architecture-doc-plugin/
├── .claude-plugin/
│   └── plugin.json                     # Plugin manifest (v2.0.0)
├── commands/
│   ├── gen-diagram.md                  # Mermaid diagram generator + syntax validation & HTML preview
│   ├── api-spec.md                     # Deterministic REST endpoint scanner (Markdown & OpenAPI 3.0)
│   ├── explain-file.md                 # Deep file breakdown (structure, dependencies, logic, gotchas)
│   └── doc-setup.md                    # Setup wizard for bundled MCP tools
├── mcp/
│   ├── doc_mcp_server.py               # AST dependency parser, route extractor, Mermaid validator
│   └── requirements.txt                # Minimal Python dependencies (mcp>=1.0.0)
├── examples/
│   ├── sample_project/                 # Complete multi-layer e-commerce API for testing
│   │   ├── app.py                      # FastAPI entry point
│   │   ├── routes/                     # auth_routes.py, order_routes.py
│   │   ├── services/                   # auth_service.py, order_service.py
│   │   ├── models/                     # user.py, order.py
│   │   └── db/                         # database.py
│   └── hooks.json                      # Drop-in automation hooks template
├── docs/
│   └── hooks-examples.md               # Ready-to-use hooks recipes
└── skills/
    └── codebase-documentation/
        └── SKILL.md                    # Comprehensive documentation engineering standards
```

---

## 🛠️ Commands

| Command | Description | MCP-Enhanced Mode |
|---|---|---|
| `/gen-diagram [dir or type]` | Generates Mermaid.js diagrams (Flowchart, Sequence, Class) | Uses real AST parsing, validates syntax, and exports interactive HTML preview |
| `/api-spec [dir or format]` | Generates Markdown or OpenAPI 3.0 YAML specs | Scans route decorators deterministically across FastAPI, Flask, Express |
| `/explain-file <file_path>` | Creates an onboarding breakdown of complex source files | Inspects inbound and outbound coupling using the project dependency graph |
| `/doc-setup` | Wizard to install dependencies and register the bundled MCP server | Checks environment and connects `doc-tools` to Claude Code |

---

## 🔌 Bundled MCP Server (`mcp/doc_mcp_server.py`)

The included MCP server provides 4 deterministic tools:

1. `parse_dependencies` — AST parsing for Python and token parsing for JS/TS/Go. Identifies circular dependencies and computes architectural coupling without fragile regex pipelines.
2. `extract_api_routes` — Discovers HTTP endpoints, route paths, handlers, docstrings, and parameters across FastAPI, Flask, Express, and Hono.
3. `validate_mermaid` — Checks Mermaid syntax for unquoted parentheses, unclosed subgraphs, and invalid arrow tokens to guarantee zero-error rendering.
4. `export_html_preview` — Generates a self-contained HTML page with embedded Mermaid.js, zoom/pan controls, and print/PDF export at `docs/architecture-preview.html`.

---

## 🪝 Automated Hooks (`examples/hooks.json`)

Copy `examples/hooks.json` to `.claude/hooks.json` in your repository:

- 🔄 **Auto-diagram on architecture changes**: Automatically regenerates diagrams when files in `services/`, `models/`, or `routes/` are modified.
- 📜 **Auto-spec on route changes**: Keeps API documentation up-to-date whenever route handlers change.
- 🛡️ **Pre-commit freshness gate**: Ensures architecture documentation exists and is current before code is committed.

---

## 🤝 Related Plugins

- **[rag-builder-plugin](../rag-builder-plugin)** — Hands-on RAG pipeline development, chunking strategy comparison, and response evaluation for Claude Code.

---

## License

MIT © [SanjayR857](https://github.com/SanjayR857)
