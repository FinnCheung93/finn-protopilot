# HTML ProtoPilot Workflow

This workflow is for HTML content-package prototypes inside the composite `finn-protopilot` skill. It assumes the medium has already been selected as HTML.

## Goal

Turn a PRD into one demand-folder prototype that can be presented locally. The Host provides PRD Viewer, directory, spotlight, preview, and author tools. The HTML Adapter owns the business UI screens.

## Standard Demand Folder

```text
Product/
  feature-name/
    feature-name.md
    prototype/
      index.html
      prototype-base.css
      prototype-shell.js
      prototype-plan.json
      generated-area-fragment.html
      prototype-content/
        manifest.json
        content.css
        screens/
    assets/
    references/
```

`prototype/prototype-content/screens/*.html` and `prototype/prototype-content/content.css` are the long-term HTML source files. `prototype/generated-area-fragment.html` and `prototype/index.html` are generated outputs.

## Happy Path

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

When the next step is unclear, run:

```text
python scripts/protopilot.py doctor <demand-dir>
```

## Source Reading

Before authoring screens, read the available sources:

1. The PRD/spec.
2. Nearby `Design/design.md`, `Design/README.md`, token files, assets, and reference images when present.
3. Existing `prototype-plan.json`.
4. Existing `prototype/prototype-content/manifest.json`, `content.css`, and screen source files when revising.

Missing reference images are not a default blocker. Continue with PRD + design context unless the user requested pixel-level recreation or the PRD cannot be interpreted without original screens.

## Content Package Rules

- `init-content` creates screen stubs only. A stub is not deliverable and is not evidence that the skill lacks a template.
- If `build-content`, `package-check`, or `final-check` reports placeholder/stub content, replace the matching `prototype/prototype-content/screens/*.html` with PRD-specific UI and update the plan if needed. Do not edit the skill templates or copy showcase screens into the real project.
- Generate real product pages, states, overlays, toasts, and key flow nodes as screens.
- Keep background, goals, long rules, fields, acceptance criteria, and SOP-style text in PRD Viewer, coverage disposition, delivery notes, or short annotations.
- Do not create a phone screen just to explain a rule.
- Screen files must not contain full page shells, shell DOM, `<script>`, `<style>`, stylesheet links, inline handlers, or `javascript:` URLs.
- `content.css` must be scoped by the content namespace and must not override `body`, `.proto-*`, `.journey-*`, `.step-*`, or `#proto-*`.
- Build screens through `build-content`; do not hand-maintain a large fragment for complex PRDs.

## Editing

Use `preview <demand-dir>` for local viewing and text editing.

- "改文字" saves safe visible text edits back to `prototype/prototype-content/screens/*.html`.
- Structural changes use "复制给 AI" notes or direct source-file edits.
- Legacy fragment-only prototypes can be viewed, but they cannot pretend to save text edits back to source files.

Stop the preview when finished:

```text
python scripts/protopilot.py stop-preview <demand-dir>
```

## Completion Checks

For complex HTML prototypes, run:

```text
python scripts/protopilot.py package-check --strict <demand-dir>
python scripts/protopilot.py build-content --check <demand-dir>
python scripts/protopilot.py final-check --require-content --require-complete <demand-dir>
python scripts/protopilot.py quality-check --strict <demand-dir>
```

`final-check` verifies the deterministic package/plan/index state. `quality-check` is the broader presentation-quality scan. Passing both does not replace human review of the prototype effect.

## Showcase

`examples/showcase-html/` is a validation surface and capability demo. It is not a template for real PRDs.

Refresh it with:

```text
python scripts/protopilot.py build-showcase
```
