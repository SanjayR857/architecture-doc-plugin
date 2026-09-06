---
description: Create a detailed breakdown of a file for onboarding and understanding
allowed-tools: Read, Bash, Glob, Grep, mcp__doc__parse_dependencies
---

# Explain File

Create a comprehensive, detailed breakdown of a file to help with developer onboarding and understanding complex code.

## Your Task

Analyze the specified file and produce a detailed architecture, dependency, and logic breakdown.

**File to explain**: `$ARGUMENTS`

---

## Step 1: Validate & Locate File

1. If `$ARGUMENTS` is empty, ask the user:
   ```
   Which file would you like me to explain?
   Please provide the path (e.g., src/services/auth.ts or app/models/order.py)
   ```
2. If the path does not exist, use `Glob` to search for matching file basenames across the repository:
   - Example: `Glob("**/*" + basename + "*")`
3. Read the file using the `Read` tool.

---

## Step 2: Multi-Dimensional Analysis

Analyze the file across 5 key dimensions:

### 2A: Metadata & Role
- **Path & Language**: Where it sits in the project hierarchy
- **Lines of Code**: Total lines vs. logic lines
- **Architectural Role**: Entry point, Route handler, Business Service, Data Model, Database abstraction, or Utility
- **Blast Radius**: What system features would fail if this file was deleted or broken?

### 2B: Dependency Map (Inbound & Outbound)
- **Outbound Imports**: What external packages and internal modules does this file consume?
- **Inbound Dependents**: Which other files import and call this file?
  - *If MCP `mcp__doc__parse_dependencies` is available*: Read direct coupling and dependent files from the dependency graph.
  - *If MCP is not available*: Use `Grep` to search for the module name or filename stem across the repository.

### 2C: Code Structure & Logic
Break down the internals:
- **Classes**: Class name, responsibilities, base classes, methods
- **Key Functions / Methods**: Parameters, return types, error conditions
- **Data Shapes**: Pydantic models, TypeScript interfaces, or DTOs
- **Side Effects**: Module-level database connections, environment reads, or initialization logic

### 2D: Critical Paths & Complex Algorithms
- Trace the most important execution flow inside this file.
- Highlight any non-obvious business rules, state machines, or calculations.

### 2E: Gotchas & Edge Cases
- Concurrency or thread-safety considerations
- Error handling patterns (does it throw exceptions or return None/null?)
- Assumptions about environment variables or external services

---

## Step 3: Present Structured Explanation

```
╔══════════════════════════════════════════════════════════════╗
║                   FILE BREAKDOWN                             ║
║  File: [relative path]                                       ║
║  Layer: [Service / Route / Model / DB / Util]                ║
║  Size: [lines of code]                                       ║
╚══════════════════════════════════════════════════════════════╝
```

### 1. Executive Summary
- 2–3 sentences explaining the single responsibility of this file.

### 2. Architecture & Role
- Where it fits in the data flow.
- Blast radius and failure modes.

### 2. Dependency Overview
| Direction | Module / File | Purpose |
|---|---|---|
| **Depends on** | `models/user.py` | Imports User schema |
| **Used by** | `routes/auth_routes.py` | Called to authenticate logins |

### 3. Key Components & Functions
- Detailed breakdown of classes and functions.

### 4. Step-by-Step Execution Flow
- Numbered sequence showing what happens when the primary function is invoked.

### 5. Edge Cases, Gotchas & Maintenance Tips
- Things new developers might overlook when modifying this file.
