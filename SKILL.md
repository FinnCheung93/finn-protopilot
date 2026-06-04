---
name: finn-protopilot
description: Finn ProtoPilot - generate and maintain PRD/spec-driven walkthrough prototypes as a single-demand presentation directory, choosing between HTML content-package screens and editable Excalidraw sketch boards while sharing the same stable presentation shell, PRD Viewer, directory, spotlight, preview, and validation workflow. Use for PM prototype delivery when the desired medium may be HTML, sketch, or undecided.
metadata:
  version: v1.0.0
  updated: 2026-06-04
---

# Finn ProtoPilot

Finn ProtoPilot is a complete independent composite skill. It has one shared presentation Host and two built-in adapters:

- **HTML Adapter**: content-package screens, realistic static interfaces, text-only editing, and "copy to AI" structural revision notes.
- **Sketch Adapter**: Excalidraw board/frame storyboards, freeform visual editing, and save-back to `.excalidraw`.

Use HTML by default for product PRDs and directly presentable UI prototypes. Use Sketch when the user explicitly wants Excalidraw, sketch, wireframe, storyboard, or freeform canvas editing.

## Core Structure

- **PRD/spec** is the requirement source.
- **Host** is the shared presentation shell: PRD Viewer, directory, spotlight, preview, and fixed shell assets.
- The demand folder root contains the user-maintained PRD and a generated `prototype/` folder.
- **HTML prototype source** is `prototype/prototype-content/screens/*.html` plus `prototype/prototype-content/content.css`.
- **Sketch prototype source** is `prototype/prototype-excalidraw/boards/*.excalidraw`.
- `index.html`, `generated-area-fragment.html`, SVG previews, snapshots, and preview state are generated outputs. Rebuild them from the source files instead of treating them as long-term truth.

## Medium Selection

For existing demand folders:

- `prototype/prototype-content/` means continue HTML.
- `prototype/prototype-excalidraw/` means continue Sketch.
- If both exist, run `doctor`; do not guess which source is authoritative.

Adapter packages live under `prototype/`, so check `prototype/prototype-content/` and `prototype/prototype-excalidraw/` in new projects.

If the user does not specify a medium and the input is a product-feature PRD, use HTML.

## Main Workflow

Use the unified script entry:

```text
python scripts/protopilot.py <command> ...
```

HTML happy path:

```text
preflight -> scaffold -> plan -> init-content -> build-content -> inject -> final-check -> quality-check -> preview
```

Sketch happy path:

```text
preflight --adapter sketch -> scaffold --adapter sketch -> plan --adapter sketch -> init-scenes -> build-scenes -> scene-check -> quality-check -> validate -> preview
```

Common commands: `preflight`, `scaffold`, `plan`, `quality-check`, `validate`, `preview`, `stop-preview`, `doctor`, `selfcheck`.

HTML-only commands: `init-content`, `build-content`, `package-check`, `final-check`, `apply-edit-patch`, `inject`.

Sketch-only commands: `init-scenes`, `build-scenes`, `scene-check`, `shell-diff-check`.

For common commands, the dispatcher infers the adapter from the demand folder. Use `--adapter html` or `--adapter sketch` when creating a new project or resolving ambiguity.

## What To Read

- Read `references/composite-architecture.md` for Host/Adapter boundaries and the fixed five-role review record.
- Read `references/workflow.md` before executing a full project flow.
- For HTML generation/editing, read `references/html/workflow.md`, `references/html/generated-prototype-standards.md`, `references/html/generated-area-rules.md`, and `references/html/quality.md`.
- For Sketch generation/editing, read `references/sketch/workflow.md`, `references/sketch/generated-prototype-standards.md`, `references/sketch/prd-to-storyboard-semantics.md`, `references/sketch/excalidraw-storyboard-authoring.md`, and `references/sketch/quality.md`.
- Do not load both adapter rule sets unless you are maintaining the skill itself or reviewing cross-adapter behavior.

## Hard Rules

- Keep the Host stable. Adapters may hook into the shell, but must not rewrite PRD Viewer, directory, spotlight, or preview semantics.
- Do not add a third medium in this version.
- Do not restore `export-static`, project-level prototype centers, multi-user collaboration, comments, permissions, or version databases.
- Do not expose HTML text-edit/big-edit commands in Sketch mode.
- Do not expose Excalidraw board editing as an HTML content-package operation.
- Do not create `node_modules`, package lock files, logs, preview state, caches, or browser profiles in the skill root.
- Showcase examples are validation surfaces, not templates for real PRDs.
- When a real demand fails because screens, boards, plan, or manifest are incomplete, fix the demand folder source files. Do not modify skill templates, showcase, scripts, or shell assets unless the user explicitly asks to maintain the skill itself or `selfcheck` proves the skill is broken.
- Treat "business placeholder" as a demand-source problem, not a missing skill template. HTML placeholders belong in `prototype/prototype-content/screens/*.html`; Sketch sparse or `auto_draft` frames belong in `prototype/prototype-excalidraw/boards/*.excalidraw` and storyboard briefs.

## Local Preview

`preview <demand-dir>` starts or reuses a `127.0.0.1` preview for one demand folder. `stop-preview <demand-dir>` stops the matching preview service. Preview is for local viewing and editing; it is not a team server.

HTML preview can save text edits back to HTML screen source files. Sketch preview can save board edits back to `.excalidraw`.

