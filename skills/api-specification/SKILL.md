---
name: api-specification
description: REST API endpoint discovery, route extraction, and OpenAPI 3.0 specification authoring. Use when scanning web services (FastAPI, Flask, Express, Hono), generating API reference documentation, creating OpenAPI 3.0 YAML or JSON specs, documenting route parameters and payloads, or auditing API attack surfaces.
allowed-tools: Read, Bash, Glob, Grep, mcp__doc__extract_api_routes
---

# API Specification & Route Discovery Playbook

A structured playbook for discovering REST endpoints deterministically across modern web frameworks, creating OpenAPI 3.0 specifications, and writing standardized API reference documentation.

---

## 1. Deterministic Route Discovery

Use the bundled `mcp__doc__extract_api_routes` tool (or native AST inspection) rather than generic string searching.

### Supported Framework Signatures:
- **FastAPI**: `@app.get()`, `@router.post()`, `@api_router.delete()`, dependencies via `Depends(...)`
- **Flask**: `@app.route(..., methods=['GET', 'POST'])`, `@blueprint.route(...)`
- **Express.js**: `app.get()`, `router.post()`, `app.use('/api', router)`
- **Hono**: `app.get()`, `app.post()`, `app.route(...)`

---

## 2. API Reference Documentation Standards

When generating Markdown API references (e.g. `docs/API-SPEC.md`), organize endpoints by resource and provide:

### Endpoint Card Checklist:
1. **HTTP Method & Path**: Clearly demarcated (e.g. `POST /api/v1/orders`)
2. **Summary**: Concise one-line description
3. **Authentication**: `Bearer Token`, `API Key`, or `Public`
4. **Parameters Table**:
   | Name | In | Type | Required | Description |
   |---|---|---|---|---|
   | `order_id` | path | string | Yes | Unique order UUID |
   | `include_items` | query | boolean | No | Include line item details |
5. **Request Body Schema**: JSON preview with type hints
6. **Responses**: Document `200/201` success payloads and `400/401/404/500` error shapes.

---

## 3. OpenAPI 3.0 Standards

When exporting OpenAPI 3.0 specs (`docs/openapi.yaml` or `docs/openapi.json`), enforce:
- Valid `openapi: 3.0.3` header
- Proper `info` block (`title`, `version`, `description`)
- Semantic tags for route grouping
- Reusable schema definitions under `components/schemas`
- Clean `paths` mapping without trailing slash inconsistencies
