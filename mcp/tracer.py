#!/usr/bin/env python3
"""
Zero-Dependency Python Execution Tracer
=======================================

Records function calls, inputs, and return values at runtime using Python's
built-in `sys.settrace`. Filters out internal Python/stdlib/pytest noise to
focus exclusively on workspace application code and tests.

Produces:
  1. Structured JSON trace tree
  2. Syntactically-valid Mermaid.js sequence diagram with true nested lifelines
  3. Step-by-step plain English execution narrative

Usage:
  # Trace a script directly
  python mcp/tracer.py tests/test_order.py

  # Trace with pytest or custom module
  python mcp/tracer.py -m pytest tests/test_order.py

  # Output to specific JSON file
  python mcp/tracer.py --output docs/trace.json tests/test_order.py
"""

import argparse
import inspect
import json
import os
import runpy
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Standard noise directories and modules to ignore
IGNORED_PATH_SUBSTRINGS = (
    "site-packages",
    "dist-packages",
    "<frozen",
    "<string>",
    "importlib",
    "encodings",
    os.path.join("unittest", "case.py"),
    os.path.join("unittest", "suite.py"),
    os.path.join("unittest", "runner.py"),
    os.path.join("unittest", "main.py"),
    "_pytest",
    "pluggy",
    "py._",
)


def safe_repr(val: Any, max_len: int = 48) -> str:
    """Safely format an argument or return value without crashing on complex objects."""
    try:
        if val is None:
            return "None"
        if isinstance(val, (int, float, bool)):
            return str(val)
        if isinstance(val, str):
            clean = val.replace("\r", "").replace("\n", " ")
            if len(clean) > max_len:
                return f"'{clean[:max_len - 3]}...'"
            return f"'{clean}'"
        if isinstance(val, (list, tuple, set)):
            type_name = val.__class__.__name__
            length = len(val)
            if length == 0:
                return f"{type_name}()" if type_name != "list" else "[]"
            first_preview = safe_repr(next(iter(val)), max_len=20)
            return f"[{first_preview}, ... ({length} items)]" if isinstance(val, list) else f"{type_name}({first_preview}, ...)"
        if isinstance(val, dict):
            length = len(val)
            if length == 0:
                return "{}"
            keys = list(val.keys())[:2]
            keys_preview = ", ".join(repr(k) for k in keys)
            return f"{{{keys_preview}, ... ({length} keys)}}"

        cls_name = getattr(val, "__class__", type(val)).__name__
        r = repr(val).replace("\r", "").replace("\n", " ")
        if len(r) > max_len:
            return f"<{cls_name}>"
        return r
    except Exception:
        return f"<{type(val).__name__}>"


def clean_mermaid_str(text: str) -> str:
    """Clean string for Mermaid sequence diagram labels."""
    text = text.replace('"', "'").replace(";", " ").replace("\n", " ").strip()
    text = text.replace("#", "")
    return text


class ExecutionTracer:
    """Zero-dependency runtime execution tracer based on sys.settrace."""

    def __init__(
        self,
        workspace_dir: str,
        max_depth: int = 8,
        max_events: int = 300,
        tracer_file_path: Optional[str] = None,
        allow_string_code: bool = False,
    ):
        self.workspace_dir = os.path.abspath(workspace_dir).replace("\\", "/")
        self.max_depth = max_depth
        self.max_events = max_events
        self.tracer_file_path = (
            os.path.abspath(tracer_file_path or __file__).replace("\\", "/")
        )
        self.allow_string_code = allow_string_code

        self.calls: List[Dict[str, Any]] = []
        self.timeline: List[Dict[str, Any]] = []
        self.call_stack: List[Dict[str, Any]] = []
        self.event_counter = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self.is_tracing = False

        self._path_cache: Dict[str, bool] = {}

    def _should_trace_file(self, filename: str) -> bool:
        """Return True if the file belongs to the user workspace and is not library noise."""
        if not filename:
            return False

        if self.allow_string_code and (filename == "<string>" or filename.startswith("<")):
            return True

        if filename in self._path_cache:
            return self._path_cache[filename]

        norm_file = os.path.abspath(filename).replace("\\", "/")

        # Never trace the tracer itself
        if norm_file == self.tracer_file_path or norm_file.endswith("tracer.py"):
            self._path_cache[filename] = False
            return False

        # Exclude known external noise substrings
        for sub in IGNORED_PATH_SUBSTRINGS:
            if sub in norm_file:
                self._path_cache[filename] = False
                return False

        # Standard library check
        stdlib_prefix = getattr(sys, "base_prefix", sys.prefix)
        norm_stdlib = os.path.abspath(stdlib_prefix).replace("\\", "/")
        if norm_file.startswith(norm_stdlib) and not norm_file.startswith(self.workspace_dir):
            self._path_cache[filename] = False
            return False

        in_workspace = norm_file.startswith(self.workspace_dir)
        self._path_cache[filename] = in_workspace
        return in_workspace

    def _get_caller_info(self, frame) -> Tuple[str, str]:
        """Extract the calling module/class and function name."""
        back = frame.f_back
        while back:
            b_filename = back.f_code.co_filename
            if self._should_trace_file(b_filename):
                func = back.f_code.co_name
                rel_base = os.path.basename(b_filename)

                cls_name = ""
                if "self" in back.f_locals:
                    cls_name = back.f_locals["self"].__class__.__name__
                elif "cls" in back.f_locals and inspect.isclass(back.f_locals["cls"]):
                    cls_name = back.f_locals["cls"].__name__

                if cls_name:
                    return cls_name, f"{cls_name}.{func}"
                if func == "<module>":
                    return rel_base, f"{rel_base}:main"
                return rel_base, f"{rel_base}:{func}"
            back = back.f_back

        return "User/Test", "main"

    def _trace_dispatch(self, frame, event: str, arg: Any):
        """Global trace dispatch function passed to sys.settrace."""
        if not self.is_tracing:
            return None

        co = frame.f_code
        filename = co.co_filename

        # Filter out noise files
        if not self._should_trace_file(filename):
            return None

        # Filter out module bodies and class definition bodies
        if not (co.co_flags & inspect.CO_OPTIMIZED):
            return self._trace_dispatch

        depth = len(self.call_stack)
        if depth > self.max_depth:
            return self._trace_dispatch

        if self.event_counter >= self.max_events:
            return self._trace_dispatch

        func_name = co.co_name
        if func_name.startswith("__") and func_name.endswith("__") and func_name not in ("__init__", "__call__"):
            return self._trace_dispatch

        if event == "call":
            self.event_counter += 1
            rel_file = os.path.relpath(filename, self.workspace_dir).replace("\\", "/")

            cls_name = ""
            if "self" in frame.f_locals:
                cls_name = frame.f_locals["self"].__class__.__name__
            elif "cls" in frame.f_locals and inspect.isclass(frame.f_locals["cls"]):
                cls_name = frame.f_locals["cls"].__name__

            args = {}
            for i in range(co.co_argcount):
                name = co.co_varnames[i]
                if name in ("self", "cls"):
                    continue
                if name in frame.f_locals:
                    args[name] = safe_repr(frame.f_locals[name])

            caller_participant, caller_func = self._get_caller_info(frame)
            callee_participant = cls_name if cls_name else os.path.basename(rel_file)

            call_record = {
                "id": self.event_counter,
                "function": func_name,
                "class_name": cls_name,
                "participant": callee_participant,
                "caller_participant": caller_participant,
                "caller_func": caller_func,
                "file": rel_file,
                "line": frame.f_lineno,
                "depth": depth,
                "args": args,
                "return_value": None,
                "exception": None,
            }

            self.calls.append(call_record)
            self.call_stack.append(call_record)
            self.timeline.append({"type": "call", "record": call_record})
            return self._trace_dispatch

        elif event == "return":
            if self.call_stack:
                matched_call = self.call_stack.pop()
                matched_call["return_value"] = safe_repr(arg)
                self.timeline.append({"type": "return", "record": matched_call})
            return self._trace_dispatch

        elif event == "exception":
            if self.call_stack:
                exc_type, exc_val, _ = arg
                exc_name = exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type)
                val_str = str(exc_val)
                if val_str:
                    clean_val = val_str[:40]
                    self.call_stack[-1]["exception"] = f"{exc_name}('{clean_val}')"
                else:
                    self.call_stack[-1]["exception"] = exc_name
            return self._trace_dispatch

        return self._trace_dispatch

    def start(self):
        """Enable tracing."""
        self.is_tracing = True
        self.start_time = time.perf_counter()
        sys.settrace(self._trace_dispatch)

    def stop(self):
        """Disable tracing."""
        self.is_tracing = False
        sys.settrace(None)
        self.end_time = time.perf_counter()

        # Clean up any unreturned frames on stack
        while self.call_stack:
            unreturned = self.call_stack.pop()
            self.timeline.append({"type": "return", "record": unreturned})

    def generate_mermaid_sequence(self) -> str:
        """Convert chronological timeline into a clean, nested Mermaid sequence diagram."""
        if not self.calls:
            return "sequenceDiagram\n  autonumber\n  Note over User: No workspace calls detected during execution."

        # Collect unique participants preserving order
        participants: List[str] = []
        for call in self.calls:
            cp = call.get("caller_participant", "User")
            p = call.get("participant", "Service")
            if cp not in participants:
                participants.append(cp)
            if p not in participants:
                participants.append(p)

        # Map participants to safe Mermaid aliases
        p_map: Dict[str, str] = {}
        lines = ["sequenceDiagram", "  autonumber"]

        for idx, p in enumerate(participants):
            alias = f"P{idx}"
            p_map[p] = alias
            clean_label = clean_mermaid_str(p)
            if idx == 0 and ("User" in p or "test" in p.lower() or p.endswith(".py")):
                lines.append(f'  actor {alias} as "{clean_label}"')
            else:
                lines.append(f'  participant {alias} as "{clean_label}"')

        lines.append("")

        # Stream timeline events in true chronological order
        for item in self.timeline:
            event_type = item["type"]
            rec = item["record"]
            caller = p_map.get(rec.get("caller_participant", "User"), "P0")
            callee = p_map.get(rec.get("participant", "Service"), "P1")
            func = rec.get("function", "run")

            if event_type == "call":
                args_list = [f"{k}={v}" for k, v in rec.get("args", {}).items()]
                args_str = ", ".join(args_list)
                if len(args_str) > 40:
                    args_str = args_str[:37] + "..."
                call_label = clean_mermaid_str(f"{func}({args_str})")
                lines.append(f"  {caller}->>+{callee}: {call_label}")

            elif event_type == "return":
                exc = rec.get("exception")
                ret = rec.get("return_value")
                if exc:
                    exc_label = clean_mermaid_str(f"Raises {exc}")
                    lines.append(f"  {callee}--x-{caller}: {exc_label}")
                elif ret is not None and ret != "None":
                    ret_label = clean_mermaid_str(f"return {ret}")
                    lines.append(f"  {callee}-->>-{caller}: {ret_label}")
                else:
                    lines.append(f"  {callee}-->>-{caller}: done")

        return "\n".join(lines)

    def generate_narrative(self) -> List[str]:
        """Generate a numbered step-by-step plain English narrative of the flow."""
        narrative = []
        for idx, call in enumerate(self.calls, start=1):
            caller = call.get("caller_participant", "Caller")
            callee = call.get("participant", "Callee")
            func = call.get("function", "func")
            args = call.get("args", {})
            ret = call.get("return_value")
            exc = call.get("exception")

            args_str = ", ".join(f"`{k}={v}`" for k, v in args.items()) if args else "no arguments"
            step_text = f"**Step {idx}:** `{caller}` calls `{callee}.{func}` with {args_str}."

            if exc:
                step_text += f" Raised `{exc}`."
            elif ret is not None and ret != "None":
                step_text += f" Returns `{ret}`."
            narrative.append(step_text)
        return narrative

    def to_dict(self) -> Dict[str, Any]:
        """Return full structured trace result."""
        duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        return {
            "total_events": len(self.calls),
            "duration_ms": duration_ms,
            "workspace_dir": self.workspace_dir,
            "calls": self.calls,
            "mermaid_diagram": self.generate_mermaid_sequence(),
            "narrative": self.generate_narrative(),
        }


def run_and_trace_script(
    target_path: str,
    script_args: List[str],
    workspace_dir: str,
    max_depth: int = 8,
    max_events: int = 300,
    is_module: bool = False,
) -> Dict[str, Any]:
    """Execute a target Python script, module, or code string while tracing execution."""
    is_code_eval = (target_path == "-c")
    tracer = ExecutionTracer(
        workspace_dir=workspace_dir,
        max_depth=max_depth,
        max_events=max_events,
        allow_string_code=is_code_eval,
    )

    clean_target = target_path.strip('"\'')
    abs_target = os.path.abspath(clean_target) if (not is_module and not is_code_eval) else target_path

    orig_argv = sys.argv[:]
    orig_path = sys.path[:]
    sys.argv = [target_path] + script_args

    if not is_module and not is_code_eval:
        target_dir = os.path.dirname(abs_target)
        if target_dir not in sys.path:
            sys.path.insert(0, target_dir)
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)

    exit_code = 0
    error_msg = None

    tracer.start()
    try:
        if is_code_eval:
            code_str = script_args[0] if script_args else ""
            compiled = compile(code_str, "<string>", "exec")
            exec(compiled, {"__name__": "__main__", "__file__": "<string>"})
        elif is_module:
            runpy.run_module(target_path, run_name="__main__", alter_sys=True)
        else:
            runpy.run_path(abs_target, run_name="__main__")
    except SystemExit as se:
        exit_code = se.code if isinstance(se.code, int) else 0
    except Exception as e:
        exit_code = 1
        error_msg = f"{type(e).__name__}: {str(e)}"
    finally:
        tracer.stop()
        sys.argv = orig_argv
        sys.path = orig_path

    res = tracer.to_dict()
    res["target"] = target_path
    res["exit_code"] = exit_code
    if error_msg:
        res["error"] = error_msg

    return res


def main():
    parser = argparse.ArgumentParser(
        description="Zero-Dependency Execution Tracer & Sequence Diagram Generator"
    )
    parser.add_argument("target", nargs="?", default=None, help="Target Python script or module to trace")
    parser.add_argument("target_args", nargs="*", help="Arguments passed to the target script")
    parser.add_argument("-c", "--code", help="Inline Python code string to execute and trace")
    parser.add_argument("-o", "--output", help="Path to write JSON trace output")
    parser.add_argument("-w", "--workspace", default=".", help="Workspace root directory")
    parser.add_argument("-d", "--max-depth", type=int, default=8, help="Max call depth to trace")
    parser.add_argument("-e", "--max-events", type=int, default=300, help="Max events to capture")
    parser.add_argument("-m", "--module", action="store_true", help="Treat target as a module name (like python -m)")
    parser.add_argument("--mermaid-only", action="store_true", help="Output only the Mermaid diagram")

    args, unknown = parser.parse_known_args()
    all_target_args = args.target_args + unknown

    if args.code:
        target = "-c"
        target_args = [args.code] + all_target_args
    elif args.target:
        target = args.target
        target_args = all_target_args
    else:
        parser.print_help()
        sys.exit(1)

    res = run_and_trace_script(
        target_path=target,
        script_args=target_args,
        workspace_dir=args.workspace,
        max_depth=args.max_depth,
        max_events=args.max_events,
        is_module=args.module,
    )

    if args.mermaid_only:
        print(res["mermaid_diagram"])
        return

    json_str = json.dumps(res, indent=2)
    if args.output:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_str, encoding="utf-8")
        print(f"Trace result saved to: {out_path}")
        print(f"Events captured: {res['total_events']}")
        print(f"Duration: {res['duration_ms']} ms")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
