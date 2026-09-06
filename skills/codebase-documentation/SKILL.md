---
name: codebase-documentation
description: Guidelines for generating and maintaining codebase documentation. Covers architecture diagrams, API specs, file explanations, documentation standards, and when to auto-generate vs manually write docs. Use when creating, updating, or reviewing project documentation.
allowed-tools: Read, Bash, Glob, Grep
---

# Codebase Documentation Best Practices

A reference guide for creating and maintaining high-quality codebase documentation.

## 1. Documentation Hierarchy

Good documentation operates at multiple levels. Each level serves a different audience:

| Level | Audience | Content | Tool |
|-------|----------|---------|------|
| **Architecture** | New team members, architects | System-level diagrams, module relationships, data flow | `/gen-diagram` |
| **API Reference** | Frontend devs, integrators | Endpoints, parameters, response formats, error codes | `/api-spec` |
| **Runtime Flow** | Developers debugging workflows | Dynamic function call flow, parameter snapshots, sequence lifelines | `/trace-flow` |
| **File/Module** | Developers working on specific features | Detailed code breakdown, gotchas, related files | `/explain-file` |
| **Inline** | Developers reading the code | Comments, JSDoc/docstrings, type annotations | Manual |

### When to Use Each Command

| Situation | Command | Specialized Skill |
|-----------|---------|-------------------|
| Onboarding a new developer | `/gen-diagram` → `/api-spec` → `/explain-file` | `architecture-diagramming` |
| Debugging unexpected test/code behavior | `/trace-flow` | `execution-tracing` |
| Starting a new feature | `/explain-file` on files you'll modify | `codebase-documentation` |
| Code review | `/explain-file` on changed files for context | `codebase-documentation` |
| Planning a refactor | `/gen-diagram` to understand impact | `architecture-diagramming` |
| Writing integration docs | `/api-spec` for endpoint reference | `api-specification` |

---

## 2. Architecture Diagram Standards

### Diagram Types & When to Use

| Type | Best For | Mermaid Syntax |
|------|----------|---------------|
| **Flowchart** | Module dependencies, data flow | `flowchart TD` |
| **Sequence** | Request/response flow, API calls | `sequenceDiagram` |
| **Class** | OOP structure, inheritance | `classDiagram` |
| **ER** | Database schema, relationships | `erDiagram` |
| **State** | Workflow states, lifecycle | `stateDiagram-v2` |

### Diagram Quality Checklist

- ✅ Every node has a clear, descriptive label
- ✅ Arrows show direction of dependency (A → B means A depends on B)
- ✅ Related nodes are grouped in subgraphs
- ✅ External services are visually distinct
- ✅ Diagram fits on one screen (split if >15 nodes)
- ✅ Legend included for non-obvious symbols

---

## 3. API Documentation Standards

### Minimum Required Fields per Endpoint

1. **Method & Path**: `GET /api/users/:id`
2. **Description**: What it does in plain English
3. **Parameters**: Path, query, header params with types
4. **Request Body**: Schema with required/optional fields
5. **Success Response**: Status code + body schema
6. **Error Responses**: Common error codes and meanings
7. **Authentication**: Required or not, what kind

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Paths | kebab-case, plural nouns | `/api/user-profiles` |
| Parameters | camelCase | `userId`, `pageSize` |
| Request bodies | PascalCase (schema name) | `CreateUserRequest` |
| Response schemas | PascalCase | `UserResponse` |

---

## 4. File Explanation Standards

### What to Always Include

1. **One-sentence summary** — What this file does
2. **Architecture role** — Where it fits (controller/service/model/util)
3. **Dependencies** — What it imports and who imports it
4. **Key functions** — Purpose, parameters, return values
5. **Gotchas** — Non-obvious behavior, side effects, edge cases

### What to Skip

- Line-by-line explanation of obvious code
- Implementation details of standard library functions
- Comments that just restate the code (`// increment counter` next to `counter++`)

---

## 5. Documentation Maintenance

### Signs Documentation is Stale

- References to files/functions that no longer exist
- Diagrams that don't match current file structure
- API docs with wrong parameter types or response shapes
- Missing new endpoints or modules

### Keeping Docs Fresh

1. **Run after major refactors**: Re-run `/gen-diagram` and `/api-spec`
2. **Include in PR checklist**: "Did you update docs for changed endpoints?"
3. **Use hooks**: Set up git hooks to auto-check for doc staleness (see `docs/hooks-examples.md`)
4. **Version your docs**: Include generation date and git hash

---

## 6. Writing Good Code Comments

### Comment What, Not How

```python
# BAD: Loop through users and check if active
for user in users:
    if user.is_active:

# GOOD: Filter to only active users — inactive accounts are soft-deleted
#        and should not appear in search results (see JIRA-1234)
for user in users:
    if user.is_active:
```

### When to Comment

| Always Comment | Never Comment |
|---------------|---------------|
| Business logic decisions | Obvious operations |
| Workarounds and hacks (link to issue) | Standard patterns |
| Performance-critical sections | Getters/setters |
| Security-sensitive code | Type annotations (they're self-documenting) |
| Regex patterns | Simple variable assignments |
| Magic numbers/strings | Import statements |

---

## Quick Reference

### Recommended Documentation Workflow

1. 🗺️ **Start big** → `/gen-diagram` for the 10,000-foot view
2. 🌐 **Map the API** → `/api-spec` for all external interfaces
3. 📄 **Deep-dive critical files** → `/explain-file` for complex/important files
4. 📝 **Add inline docs** → Write comments for non-obvious logic
5. 🔄 **Keep fresh** → Re-run after major changes
