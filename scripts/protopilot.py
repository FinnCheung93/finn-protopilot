#!/usr/bin/env python3
"""Unified Finn ProtoPilot command dispatcher.

The composite skill keeps HTML and Sketch adapters physically inside this
skill, while presenting one command surface to agents.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_SCRIPT = ROOT / "scripts" / "protopilot_html.py"
SKETCH_SCRIPT = ROOT / "scripts" / "protopilot_sketch.py"

HTML_ONLY = {
    "prepare",
    "inject",
    "validate-plan",
    "render-fragment",
    "init-content",
    "package-check",
    "build-content",
    "validate-fragment",
    "sync-plan",
    "apply-edit-patch",
    "final-check",
    "migrate-legacy",
}
SKETCH_ONLY = {
    "init-scenes",
    "build-scenes",
    "scene-check",
    "serve-edit",
    "shell-diff-check",
}
COMMON = {
    "preflight",
    "scaffold",
    "plan",
    "quality-check",
    "validate",
    "preview",
    "stop-preview",
    "doctor",
    "selfcheck",
    "build-showcase",
}
PUBLIC_COMMANDS = sorted(HTML_ONLY | SKETCH_ONLY | COMMON)
TEXT_SCAN_EXTENSIONS = {".md", ".py"}
RESIDUE_NAMES = {
    ".protopilot-preview.json",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".cache",
}
RESIDUE_SUFFIXES = {".pyc", ".log"}


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "status": "failed", "failure": message}, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(code)


def extract_adapter(argv: list[str]) -> tuple[str, list[str]]:
    cleaned: list[str] = []
    adapter = "auto"
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--adapter":
            if i + 1 >= len(argv):
                fail("--adapter requires html, sketch, or auto.")
            adapter = argv[i + 1].strip().lower()
            i += 2
            continue
        if arg.startswith("--adapter="):
            adapter = arg.split("=", 1)[1].strip().lower()
            i += 1
            continue
        cleaned.append(arg)
        i += 1
    if adapter not in {"auto", "html", "sketch"}:
        fail("--adapter must be html, sketch, or auto.")
    return adapter, cleaned


def first_path_arg(args: list[str]) -> Path | None:
    if not args:
        return None
    # Skip command name. The first non-option argument after it is enough for
    # adapter inference across current ProtoPilot commands.
    for arg in args[1:]:
        if arg.startswith("-"):
            continue
        return Path(arg).expanduser()
    return None


def demand_for_path(path: Path) -> Path:
    if path.is_dir():
        resolved = path.resolve()
        return resolved.parent if resolved.name == "prototype" else resolved
    if path.exists():
        parent = path.resolve().parent
        return parent.parent if parent.name == "prototype" else parent
    # For new loose PRD paths, infer from parent only; this intentionally
    # defaults to HTML unless the caller requested --adapter sketch.
    return path.parent.resolve()


def detect_adapter_from_path(path: Path | None) -> tuple[str | None, list[str]]:
    if path is None:
        return None, []
    demand = demand_for_path(path)
    prototype = demand / "prototype"
    has_html = (prototype / "prototype-content").exists()
    has_sketch = (prototype / "prototype-excalidraw").exists()
    warnings: list[str] = []
    if has_html and has_sketch:
        return "conflict", [f"Both prototype-content and prototype-excalidraw exist in {demand}."]
    if has_sketch:
        return "sketch", warnings
    if has_html:
        return "html", warnings
    return None, warnings


def choose_adapter(command: str, requested: str, args: list[str]) -> str:
    if command in HTML_ONLY:
        if requested == "sketch":
            fail(f"{command} is an HTML-only command.")
        return "html"
    if command in SKETCH_ONLY:
        if requested == "html":
            fail(f"{command} is a Sketch-only command.")
        return "sketch"
    if command not in COMMON:
        fail(f"Unknown command: {command}")
    if requested in {"html", "sketch"}:
        return requested

    detected, warnings = detect_adapter_from_path(first_path_arg(args))
    if detected == "conflict":
        payload = {
            "ok": False,
            "status": "conflict",
            "adapter": "unknown",
            "failures": warnings,
            "next_actions": [
                "Run the command again with --adapter html or --adapter sketch after deciding the source of truth.",
                "Keep only one prototype source for a demand folder when possible.",
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(3)
    if detected:
        return detected

    # Default for new PRD/product-feature work: HTML. Sketch must be requested
    # explicitly or inferred from an existing prototype-excalidraw package.
    return "html"


def adapter_script(adapter: str) -> Path:
    script = HTML_SCRIPT if adapter == "html" else SKETCH_SCRIPT
    if not script.is_file():
        fail(f"Missing {adapter} adapter script: {script}")
    return script


def dispatch(adapter: str, args: list[str]) -> int:
    script = adapter_script(adapter)
    final_args = list(args)
    if adapter == "html" and "--skill-root" not in final_args and not any(a.startswith("--skill-root=") for a in final_args):
        final_args = ["--skill-root", str(ROOT), *final_args]
    return subprocess.call([sys.executable, "-B", str(script), *final_args], cwd=str(ROOT))


def composite_structure_check() -> dict[str, object]:
    failures: list[str] = []
    warnings: list[str] = []
    required_paths = [
        "SKILL.md",
        "references/workflow.md",
        "references/composite-architecture.md",
        "references/html/workflow.md",
        "references/html/generated-prototype-standards.md",
        "references/html/generated-area-rules.md",
        "references/html/quality.md",
        "references/sketch/workflow.md",
        "references/sketch/generated-prototype-standards.md",
        "references/sketch/prd-to-storyboard-semantics.md",
        "references/sketch/excalidraw-storyboard-authoring.md",
        "references/sketch/quality.md",
        "templates/html/prototype-shell.html",
        "templates/sketch/prototype-shell.html",
        "templates/prototype-shell.html",
        "examples/showcase-html",
        "examples/showcase-html/prototype/index.html",
        "examples/showcase-html/prototype/prototype-content",
        "examples/showcase-sketch",
        "examples/showcase-sketch/prototype/index.html",
        "examples/showcase-sketch/prototype/prototype-excalidraw",
        "prototype-base.css",
        "prototype-shell.js",
        "prototype-excalidraw.css",
        "prototype-excalidraw.js",
    ]
    for rel in required_paths:
        if not (ROOT / rel).exists():
            failures.append(f"Missing required composite path: {rel}")

    stale_patterns = [
        (re.compile(r"examples/showcase(?!-html|-sketch)"), "old showcase path"),
        (re.compile(r"showcase-html-html"), "duplicated showcase-html path"),
        (re.compile(r"references/prd-to-storyboard-semantics\.md"), "old sketch reference path"),
        (re.compile(r"回归门禁"), "unclear delivery-check term"),
        (re.compile(r"鏀|鈫|鏈|宸ヤ綔娴|鐢熸垚"), "mojibake text"),
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SCAN_EXTENSIONS:
            continue
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"Text file is not valid UTF-8: {rel}")
            continue
        if rel == "scripts/protopilot.py":
            continue
        for pattern, label in stale_patterns:
            if pattern.search(text):
                if label == "mojibake text" and path.suffix.lower() == ".py":
                    warnings.append(f"Possible mojibake remains in script internals: {rel}")
                else:
                    failures.append(f"Found {label} in {rel}")

    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT).as_posix()
        if path.name in RESIDUE_NAMES or path.suffix.lower() in RESIDUE_SUFFIXES:
            failures.append(f"Runtime residue should not be kept in the skill tree: {rel}")

    if (ROOT / "templates" / "prototype-shell.html").exists():
        warnings.append("templates/prototype-shell.html is present only as a short-term fallback; maintain templates/html/prototype-shell.html first.")
    return {
        "ok": not failures,
        "status": "ok" if not failures else "failed",
        "checks": {
            "required_paths": len(required_paths),
            "text_extensions": sorted(TEXT_SCAN_EXTENSIONS),
        },
        "failures": failures,
        "warnings": warnings,
    }


def command_composite_selfcheck() -> int:
    structure = composite_structure_check()
    html_code = dispatch("html", ["selfcheck"])
    result = {
        "ok": structure["ok"] and html_code == 0,
        "structure_check": structure,
        "html_selfcheck_exit_code": html_code,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        parser = argparse.ArgumentParser(description="Finn ProtoPilot composite tooling.")
        parser.add_argument("--adapter", choices=["auto", "html", "sketch"], default="auto", help="Force a prototype adapter for common commands.")
        parser.add_argument("command", nargs="?", choices=PUBLIC_COMMANDS)
        parser.print_help()
        print("\nCommon happy paths:")
        print("  HTML:   preflight -> scaffold -> plan -> init-content -> build-content -> inject -> final-check -> quality-check -> preview")
        print("  Sketch: preflight --adapter sketch -> scaffold --adapter sketch -> plan --adapter sketch -> init-scenes -> build-scenes -> scene-check -> quality-check -> validate -> preview")
        return 0

    requested, cleaned = extract_adapter(argv)
    if not cleaned:
        fail("Missing command.")
    command = cleaned[0]
    if command == "selfcheck" and requested == "auto":
        return command_composite_selfcheck()
    adapter = choose_adapter(command, requested, cleaned)
    return dispatch(adapter, cleaned)


if __name__ == "__main__":
    raise SystemExit(main())
