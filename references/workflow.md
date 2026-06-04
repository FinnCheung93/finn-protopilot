# Finn ProtoPilot Composite Workflow

This file is the top-level route map. Use it to choose HTML or Sketch, then read only the matching adapter workflow:

- HTML: `references/html/workflow.md`
- Sketch: `references/sketch/workflow.md`

## 1. Decide Medium

Use HTML by default for product PRDs, mobile/Web screens, realistic static interfaces, or prototypes where the user may want to edit text.

Use Sketch when the user explicitly asks for Excalidraw, sketch, wireframe, storyboard, low-fidelity flow discussion, or freeform canvas editing.

For existing folders, let the source package decide:

- `prototype/prototype-content/` -> HTML.
- `prototype/prototype-excalidraw/` -> Sketch.
- both -> conflict; ask the user which source should remain authoritative.

New generated demand folders keep the PRD at the root and put all prototype files in `prototype/`:

```text
demand/
  demand.md
  prototype/
    index.html
    generated-area-fragment.html
    prototype-plan.json
    prototype-base.css
    prototype-shell.js
    prototype-content/ or prototype-excalidraw/
```

## 2. Discover Sources

Always start with the PRD/spec. If a nearby `Design/design.md`, `Design/README.md`, token file, `assets/`, or `references/` exists, inspect it before authoring prototype content.

Missing reference images are not a default blocker. Continue with PRD + design context and record the source status. Ask only when the user requests pixel-level recreation or the PRD cannot be interpreted without an original screen.

## 3. HTML Flow Summary

```text
python scripts/protopilot.py preflight <prd-or-demand-dir>
python scripts/protopilot.py scaffold <prd-path>
python scripts/protopilot.py plan <demand-dir>
python scripts/protopilot.py init-content <demand-dir>
python scripts/protopilot.py build-content <demand-dir>
python scripts/protopilot.py inject --strict <demand-dir>/prototype/index.html <demand-dir>/prototype/generated-area-fragment.html
python scripts/protopilot.py final-check --require-content --require-complete <demand-dir>
python scripts/protopilot.py quality-check --strict <demand-dir>
python scripts/protopilot.py preview <demand-dir>
```

Authoring happens in `prototype/prototype-content/screens/*.html` and `prototype/prototype-content/content.css`. The generated fragment and `index.html` live under `prototype/`.

Read `references/html/workflow.md` before authoring or modifying HTML screens.

## 4. Sketch Flow Summary

```text
python scripts/protopilot.py preflight --adapter sketch <prd-or-demand-dir>
python scripts/protopilot.py scaffold --adapter sketch <prd-path>
python scripts/protopilot.py plan --adapter sketch <demand-dir>
python scripts/protopilot.py init-scenes <demand-dir>
python scripts/protopilot.py build-scenes <demand-dir>
python scripts/protopilot.py scene-check <demand-dir>
python scripts/protopilot.py quality-check --strict <demand-dir>
python scripts/protopilot.py validate <demand-dir>
python scripts/protopilot.py preview <demand-dir>
```

Authoring happens in `prototype/prototype-excalidraw/boards/*.excalidraw`. The presentation HTML and SVG previews live under `prototype/`.

Sketch presentation grouping follows `plan.groups`, matching HTML. Sketch `boards` only partition editing and storage.

Read `references/sketch/workflow.md` before authoring or modifying Sketch boards.

## 5. Preview And Editing

`preview` starts or reuses a local `127.0.0.1` service for one demand folder.

- HTML: "改文字" saves safe text edits back to screen source files.
- Sketch: edit mode opens the Excalidraw board and saves back to `.excalidraw`.

Use `stop-preview <demand-dir>` when finished. Do not keep `.protopilot-preview.json` in the skill tree.

## 6. Recovery

Run `doctor <demand-dir>` whenever the next step is unclear. It reports the detected adapter and only suggests commands that match the current source package.

If `doctor` reports both HTML and Sketch source packages, stop and decide which source should own the prototype before continuing.

Do not repair a real demand by editing the skill. If a check reports placeholders, sparse boards, stale manifests, or incomplete plans, update the demand folder source files and rerun the matching build/check commands. Only edit the skill when the user asks for skill maintenance or `selfcheck` shows the shared tools are broken.

Use these terms consistently:

- **Skill template missing**: the skill's shell/template/assets are absent or broken. Confirm with `selfcheck` before changing the skill.
- **Business placeholder**: generated demand content is still a stub, skeleton, `auto_draft`, or showcase-like placeholder. Fix the demand source files.

Repeated output from the same PRD, same design context, and same plan/reset strategy is expected deterministic behavior. If the user wants a different direction or an improved second attempt, change the PRD, add revision notes, adjust the plan, or edit the prototype source. Similar output across different PRDs is a quality risk and should be handled by quality review.
