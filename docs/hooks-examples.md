# Hooks Examples for Architecture Doc Plugin

This guide shows how to set up Claude Code hooks to **automate documentation** tasks using this plugin's commands.

> **Note**: Hooks are configured at the user/project level in `.claude/hooks.json`, not inside the plugin itself. Copy the examples below into your project's hooks configuration.

---

## What Are Hooks?

Hooks are triggers that run commands automatically in response to events like:
- **Pre-commit**: Before a git commit is finalized
- **Post-commit**: After a commit is made
- **On-save**: When a file is saved (editor-specific)
- **Scheduled**: On a cron schedule

---

## Example 1: Auto-Regenerate API Docs on Commit

Regenerate API documentation whenever files in `routes/` or `controllers/` are changed.

```json
{
  "hooks": {
    "pre-commit": [
      {
        "name": "update-api-docs",
        "condition": "git diff --cached --name-only | grep -E '(routes|controllers|handlers)/'",
        "command": "/api-spec markdown",
        "description": "Auto-update API docs when route files change"
      }
    ]
  }
}
```

---

## Example 2: Architecture Diagram on Major Changes

Regenerate the architecture diagram when new modules or directories are added.

```json
{
  "hooks": {
    "post-commit": [
      {
        "name": "update-architecture-diagram",
        "condition": "git diff HEAD~1 --name-only | grep -E '(src|lib|pkg)/[^/]+/' | head -1",
        "command": "/gen-diagram",
        "description": "Regenerate architecture diagram when module structure changes"
      }
    ]
  }
}
```

---

## Example 3: File Explanation for New Files

Automatically generate an explanation for newly created files.

```json
{
  "hooks": {
    "post-commit": [
      {
        "name": "explain-new-files",
        "condition": "git diff HEAD~1 --diff-filter=A --name-only | grep -E '\\.(ts|py|go|rs|java)$'",
        "command": "/explain-file $(git diff HEAD~1 --diff-filter=A --name-only | head -1)",
        "description": "Auto-explain newly added source files"
      }
    ]
  }
}
```

---

## Example 4: Documentation Staleness Check (Weekly)

Run a weekly check to see if documentation is still in sync with code.

```json
{
  "hooks": {
    "scheduled": [
      {
        "name": "doc-staleness-check",
        "cron": "0 9 * * MON",
        "command": "Compare docs/API.md against current /api-spec output and report differences",
        "description": "Weekly check for stale documentation"
      }
    ]
  }
}
```

---

## How to Set Up Hooks

1. Create `.claude/hooks.json` in your project root
2. Copy the relevant examples above
3. Customize the `condition` and `command` fields for your project structure
4. Hooks will run automatically on the specified triggers

## Limitations

- Hook support depends on your Claude Code version
- Complex conditions may need shell scripting
- Hooks run in the project directory context
- Some hooks may require user confirmation before executing
