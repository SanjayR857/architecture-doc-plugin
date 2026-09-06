---
description: Set up the bundled MCP server for automated AST dependency parsing, route discovery, and Mermaid preview
allowed-tools: Bash, Read, AskUserQuestion
---

# Architecture Doc Setup

Configure the bundled MCP server (`doc-tools`) to enable deterministic AST code analysis, OpenAPI extraction, Mermaid syntax linting, and interactive HTML preview generation.

## Your Task

Guide the user through installing requirements and registering the `doc-tools` MCP server with Claude Code.

## Step 1: Check Current MCP Registration

Check if `doc-tools` is already registered:

```bash
claude mcp list | grep -i doc-tools || echo "doc-tools not registered"
```

If already registered:
- Confirm active tools: `parse_dependencies`, `extract_api_routes`, `validate_mermaid`, `export_html_preview`.
- Report that the plugin is fully equipped for live AST analysis.

## Step 2: Install MCP Dependencies

The bundled server requires Python 3.10+ and the lightweight `mcp` SDK:

```bash
# Install dependencies from the plugin directory
pip install -r mcp/requirements.txt
```

*(Dependencies: `mcp>=1.0.0`)*

## Step 3: Register MCP Server with Claude Code

Register the server with Claude Code using stdio transport:

```bash
# Register with Claude Code
claude mcp add doc-tools --scope user -- python mcp/doc_mcp_server.py
```

*(If running from outside the plugin repository, provide the absolute path to `doc_mcp_server.py`)*

## Step 4: Verify MCP Tools

Run a quick test to confirm the tools are registered:

```bash
claude mcp list | grep -i doc-tools
```

Expected tools:
- `mcp__doc__parse_dependencies` — AST & token-based dependency and circular import analysis
- `mcp__doc__extract_api_routes` — Deterministic REST endpoint discovery for FastAPI, Flask, Express
- `mcp__doc__validate_mermaid` — Mermaid syntax validator and auto-fixer
- `mcp__doc__export_html_preview` — Standalone HTML diagram viewer with SVG export

## Step 5: Test on Sample Project

Test the setup immediately on the bundled sample project:

```bash
python mcp/doc_mcp_server.py --test
```

Report:
```
╔══════════════════════════════════════════════════════════════╗
║             ARCHITECTURE DOC SETUP COMPLETE                 ║
╚══════════════════════════════════════════════════════════════╝

✅ MCP Server: doc-tools (v2.0.0)
✅ Registered Tools:
   - parse_dependencies (AST-level dependency resolution)
   - extract_api_routes (Deterministic route discovery)
   - validate_mermaid   (Zero-error diagram syntax checker)
   - export_html_preview (Interactive browser diagram previewer)

📋 Try it now:
   - /gen-diagram examples/sample_project
   - /api-spec examples/sample_project
   - /explain-file examples/sample_project/services/order_service.py
```
