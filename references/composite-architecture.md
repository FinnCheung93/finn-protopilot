# Composite Architecture

Finn ProtoPilot is a composite skill with one Host and two built-in adapters.

## Five-Role Review Record

This first composite version is an important iteration. The fixed review roles reached these decisions:

- **Product / user view**: one entry is easier than choosing between two similar skills, as long as the default path remains HTML and Sketch is explicit when needed.
- **AI Agent Skill expert**: keep `SKILL.md` short, put adapter details in references, and use script dispatch so agents do not memorize path-specific flows.
- **Senior architect**: make the new skill independent. Copy stable capabilities into this project; do not read old skill folders at runtime.
- **Senior frontend engineer**: keep the presentation Host stable and let adapters hook into it through templates/assets, not by rewriting the shell.
- **Senior QA**: preserve both adapter test paths and add conflict detection for demand folders that contain both prototype sources.

## Layers

- **Governance**: family principles and development log outside this skill.
- **Entry**: `SKILL.md` chooses medium and points to the right reference.
- **Dispatcher**: `scripts/protopilot.py` routes commands to internal adapters.
- **Host**: shared presentation behavior and assets: `prototype-base.css`, `prototype-shell.js`, PRD Viewer, directory, spotlight, and preview lifecycle.
- **HTML Adapter**: `scripts/protopilot_html.py`, content package, HTML quality/final checks.
- **Sketch Adapter**: `scripts/protopilot_sketch.py`, Excalidraw board/frame source, scene checks.
- **Templates**: `templates/html/prototype-shell.html` for HTML and `templates/sketch/prototype-shell.html` for Sketch. The legacy root template is a short-term fallback only.
- **Examples**: `examples/showcase-html` for HTML and `examples/showcase-sketch` for Sketch validation.

## Boundary Rules

- Host capabilities are shared: PRD Viewer, directory, spotlight, preview lifecycle, and presentation layout.
- Host asset source remains at the skill root in this version: `prototype-base.css` and `prototype-shell.js`. Demand-folder copies are derived artifacts.
- Adapter capabilities are medium-specific: HTML text editing does not appear in Sketch mode; Excalidraw editing does not appear in HTML mode.
- HTML-specific rules live in `references/html/`; Sketch-specific rules live in `references/sketch/`. Root references are composite-level only.
- Old `finn-protopilot-html` and `finn-protopilot-sketch` are migration sources only. New runtime code must use files inside this skill.
- Derived artifacts must be rebuilt from their adapter source; do not edit derived `index.html` or fragment as long-term truth.
