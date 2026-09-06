"""
Unit Tests for Architecture Doc MCP Server
===========================================
Tests AST dependency parsing, TypeScript path alias resolution,
REST API endpoint discovery, Mermaid syntax linting, and HTML export.
"""

import os
import sys
import unittest
from pathlib import Path

# Add mcp/ to Python path
PLUGIN_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "mcp"))

from doc_mcp_server import (
    parse_dependencies_impl,
    extract_api_routes_impl,
    validate_mermaid_impl,
    export_html_preview_impl,
    load_tsconfig_paths,
)


class TestDocMcpServer(unittest.TestCase):
    """Test suite for doc_mcp_server tools."""

    @classmethod
    def setUpClass(cls):
        cls.sample_project = str(PLUGIN_ROOT / "examples" / "sample_project")

    def test_parse_dependencies(self):
        """Test that Python and TypeScript files are analyzed into a graph."""
        res = parse_dependencies_impl(self.sample_project)
        self.assertNotIn("error", res)
        self.assertGreaterEqual(res["total_files_analyzed"], 10)
        self.assertGreaterEqual(res["total_dependencies_found"], 14)
        self.assertEqual(len(res["circular_dependencies"]), 0, "Clean sample project should have no cycles")

        # Verify layer categorization
        layers = res["layers"]
        self.assertTrue(any("auth_routes" in f for f in layers["routes"]))
        self.assertTrue(any("order_service" in f for f in layers["services"]))
        self.assertTrue(any("user.py" in f for f in layers["models"]))
        self.assertTrue(any("database.py" in f for f in layers["db"]))
        self.assertTrue(any("api_client.ts" in f for f in layers["frontend"]))

    def test_typescript_alias_resolution(self):
        """Test that tsconfig.json path aliases (@/...) resolve to target files."""
        aliases = load_tsconfig_paths(Path(self.sample_project))
        self.assertIn("@", aliases)
        self.assertEqual(aliases["@"], "frontend")

        res = parse_dependencies_impl(self.sample_project)
        edges = res["edges"]

        # Verify that @/types was resolved to frontend/types.ts
        alias_edges = [
            e for e in edges
            if e["from"] == "frontend/api_client.ts" and e["to"] == "frontend/types.ts"
        ]
        self.assertGreaterEqual(len(alias_edges), 1, "Should resolve @/types import alias")

    def test_extract_api_routes(self):
        """Test deterministic REST endpoint discovery for FastAPI."""
        res = extract_api_routes_impl(self.sample_project)
        self.assertNotIn("error", res)
        self.assertEqual(res["total_routes_discovered"], 8)

        routes = res["routes"]
        paths = [r["path"] for r in routes]
        methods = [r["method"] for r in routes]

        self.assertIn("/health", paths)
        self.assertIn("/register", paths)
        self.assertIn("/login", paths)
        self.assertIn("/{order_id}", paths)
        self.assertIn("GET", methods)
        self.assertIn("POST", methods)
        self.assertIn("DELETE", methods)

    def test_mermaid_validation_valid(self):
        """Test valid Mermaid diagram passes without errors."""
        code = "flowchart TD\n  A --> B"
        res = validate_mermaid_impl(code)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["errors"]), 0)

    def test_mermaid_validation_unquoted_parens(self):
        """Test that unquoted parentheses in node labels are caught and auto-fixed."""
        code = "flowchart TD\n  A[Auth Service (JWT)] --> B[Database (PostgreSQL)]"
        res = validate_mermaid_impl(code)
        self.assertTrue(res["valid"])
        self.assertGreaterEqual(len(res["warnings"]), 1)
        self.assertIn('A["Auth Service (JWT)"]', res["fixed_diagram"])
        self.assertIn('B["Database (PostgreSQL)"]', res["fixed_diagram"])

    def test_mermaid_validation_mismatched_subgraphs(self):
        """Test that unclosed subgraphs trigger validation errors."""
        code = "flowchart TD\n  subgraph Core\n    A --> B"
        res = validate_mermaid_impl(code)
        self.assertFalse(res["valid"])
        self.assertGreaterEqual(len(res["errors"]), 1)

    def test_html_preview_generation(self):
        """Test generation of interactive HTML preview file."""
        code = "flowchart TD\n  APP --> DB"
        out_path = str(PLUGIN_ROOT / "docs" / "test-preview.html")
        res = export_html_preview_impl(code, title="Test Architecture", output_path=out_path)
        self.assertTrue(res["success"])
        self.assertTrue(Path(out_path).exists())

        content = Path(out_path).read_text(encoding="utf-8")
        self.assertIn("mermaid.initialize", content)
        self.assertIn("Test Architecture", content)

        # Cleanup test preview
        try:
            os.remove(out_path)
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main()
