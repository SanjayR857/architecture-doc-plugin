---
description: Scan endpoints and functions to draft OpenAPI or Markdown API documentation
allowed-tools: Read, Bash, Glob, Grep, mcp__doc__extract_api_routes
---

# API Spec Generator

Scan the codebase for API endpoints, functions, and interfaces, then generate structured API documentation (Markdown or OpenAPI 3.0 YAML).

## Your Task

Analyze the codebase to discover API endpoints and produce clear, comprehensive API documentation.

**Arguments**: `$ARGUMENTS` (can be empty, a directory path, `openapi`, `markdown`, or `both`)

---

## Step 1: Detect Endpoints (MCP vs. Pattern Scan)

Check if the `doc-tools` MCP server is connected:

### If MCP is Available (`mcp__doc__extract_api_routes`):
1. Target directory: `.` (or path passed in `$ARGUMENTS`).
2. Call `mcp__doc__extract_api_routes`:
   ```json
   { "directory": "[target_directory]" }
   ```
3. The tool returns deterministic endpoint metadata:
   - `framework`: FastAPI, Flask, Express/Hono
   - `method`: GET, POST, PUT, DELETE, etc.
   - `path`: URL route path
   - `handler`: Name of the controller/handler function
   - `parameters`: Function argument list

### If MCP is Not Available:
Fall back to Claude Code native `Glob` and `Grep` tools:
- Search for route declarations across files:
  - **FastAPI / Flask**: `@(app|router)\.(get|post|put|delete|patch)` or `@app\.route`
  - **Express / Hono**: `(app|router)\.(get|post|put|delete|patch)\(`
  - **Django**: `path\(`, `urlpatterns`
  - **Go (Gin/Fiber)**: `\.(GET|POST|PUT|DELETE)\(`

---

## Step 2: Extract Endpoint Metadata

For each discovered endpoint, inspect the handler source code to document:
1. **Summary / Description**: From docstring or comment above the route
2. **Path Parameters**: URL parameters like `{order_id}` or `:user_id`
3. **Query Parameters**: Optional filters, search keys, pagination (`page`, `limit`)
4. **Request Body Schema**: Pydantic models, TypeScript interfaces, or JSON payloads
5. **Response Models & Status Codes**: 200, 201, 400, 401, 404, 500

---

## Step 3: Format the Output

Based on `$ARGUMENTS`, output in the requested format:

### Format A: Markdown Reference (Default)

```markdown
# API Reference

## Authentication

### `POST /api/v1/auth/login`
Authenticate credentials and obtain an access token.

- **Request Body** (`application/json`):
  | Field | Type | Required | Description |
  |-------|------|----------|-------------|
  | `email` | string | Yes | Customer email address |
  | `password` | string | Yes | Account password |

- **Responses**:
  - `200 OK`:
    ```json
    { "access_token": "jwt_token_here", "token_type": "bearer" }
    ```
  - `401 Unauthorized`: Invalid credentials
```

### Format B: OpenAPI 3.0 YAML
If `$ARGUMENTS` contains `openapi` or `yaml`:

```yaml
openapi: 3.0.3
info:
  title: API Documentation
  version: 1.0.0
paths:
  /api/v1/auth/login:
    post:
      summary: User authentication
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: Successful authentication
```

---

## Step 4: Output Summary

```
╔══════════════════════════════════════════════════════════════╗
║                   API SPECIFICATION                         ║
║  Framework: [FastAPI / Express / etc.]                       ║
║  Endpoints discovered: [count]                              ║
║  Output format: [Markdown / OpenAPI / Both]                  ║
╚══════════════════════════════════════════════════════════════╝
```

Present the documentation, and suggest saving to `docs/api.md` or `docs/openapi.yaml`.
