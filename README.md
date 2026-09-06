# Architecture Doc Plugin (v2.1.0)

[![CI](https://github.com/SanjayR857/architecture-doc-plugin/actions/workflows/doc-check.yml/badge.svg)](https://github.com/SanjayR857/architecture-doc-plugin/actions/workflows/doc-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A production-grade automated codebase documentation and architecture visualization plugin for Claude Code.

Extract real AST module dependency graphs, resolve TypeScript path aliases (`@/*`), discover REST API endpoints deterministically, generate validated Mermaid.js diagrams, export interactive HTML browser previews, and automate documentation freshness with pre-commit hooks and GitHub Actions CI.

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

### 3. Immediate Usage on Any Repository
```bash
# Generate architecture diagram for your current project:
/gen-diagram

# Scan and document all REST endpoints:
/api-spec

# Deep-dive into any complex file:
/explain-file path/to/any/file.py
```

---

## 📦 What's Included

```
architecture-doc-plugin/
├── .claude-plugin/
│   └── plugin.json                     # Plugin manifest (v2.1.0)
├── .github/
│   └── workflows/
│       └── doc-check.yml               # GitHub Actions CI pipeline
├── commands/
│   ├── gen-diagram.md                  # Mermaid diagram generator + syntax validation & HTML preview
│   ├── api-spec.md                     # Deterministic REST endpoint scanner (Markdown & OpenAPI 3.0)
│   ├── explain-file.md                 # Deep file breakdown (structure, dependencies, logic, gotchas)
│   └── doc-setup.md                    # Setup wizard for bundled MCP tools
├── mcp/
│   ├── doc_mcp_server.py               # AST dependency parser, TS alias resolver, route extractor
│   └── requirements.txt                # Minimal Python dependencies (mcp>=1.0.0)
├── examples/
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
| `/gen-diagram [dir or type]` | Generates Mermaid.js diagrams (Flowchart, Sequence, Class) | Uses real AST parsing + TypeScript alias resolution, validates syntax, and exports interactive HTML preview |
| `/api-spec [dir or format]` | Generates Markdown or OpenAPI 3.0 YAML specs | Scans route decorators deterministically across FastAPI, Flask, Express, Hono |
| `/explain-file <file_path>` | Creates an onboarding breakdown of complex source files | Inspects inbound and outbound coupling using the project dependency graph |
| `/doc-setup` | Wizard to install dependencies and register the bundled MCP server | Checks environment and connects `doc-tools` to Claude Code |

---

## 🔌 Bundled MCP Server (`mcp/doc_mcp_server.py`)

The included MCP server provides 4 deterministic tools:

1. `parse_dependencies` — AST parsing for Python and token parsing for JS/TS/Go. Supports `tsconfig.json` path mapping (`@/*`), identifies circular dependencies, and computes architectural coupling without fragile regex pipelines.
2. `extract_api_routes` — Discovers HTTP endpoints, route paths, handlers, docstrings, and parameters across FastAPI, Flask, Express, and Hono.
3. `validate_mermaid` — Checks Mermaid syntax for unquoted parentheses, unclosed subgraphs, and invalid arrow tokens to guarantee zero-error rendering.
4. `export_html_preview` — Generates a self-contained HTML page with embedded Mermaid.js, zoom/pan controls, and print/PDF export at `docs/architecture-preview.html`.

---

## 🧪 CI/CD & Automated Verification

### GitHub Actions CI Workflow
The repository includes [`.github/workflows/doc-check.yml`](.github/workflows/doc-check.yml):
- Matrix testing across Python 3.10, 3.11, 3.12, 3.13
- Automated Python compilation and MCP self-test validation on every push and PR

Run the self-test locally:
```bash
python mcp/doc_mcp_server.py --test
```

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
