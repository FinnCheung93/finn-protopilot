# Excalidraw Storyboard Authoring

Use Excalidraw as a storyboard board, not as a set of tiny PRD-summary diagrams.

For real PRDs, start from the semantic frame spec in `prototype-plan.json`, then author product surfaces. Script-generated skeletons are starting points, not final quality.

The usable authoring input is the fourth-layer `storyboard_brief`, not the raw PRD heading. A brief must name the surface archetype, inventory the visible components, provide allowed product copy/data, list state variants and jumps, and explicitly exclude non-product artifacts such as iframe embeds, TODOs, Axure links, URLs, and internal generation labels.

## Board Shape

- Prefer one board per functional flow or product module.
- Put multiple Excalidraw `frame` elements on the board.
- Each frame should represent a real page, state, modal, settings surface, list, detail page, or message/notification surface.
- Keep frame titles short and ordered so the board reads left to right, top to bottom.
- Keep flow arrows and rule branches as connectors or callouts unless the PRD is explicitly a process diagram.

## Frame Content

For mobile products, frames should usually include:

- device-like boundary,
- status/navigation area,
- primary content region,
- realistic cards, rows, controls, forms, charts, empty states, or modal content,
- PRD-derived text and data examples.

Mobile storyboard frames should read as a connected product journey. A driving-detection PRD, for example, should become frames such as device entry, driving entry, onboarding, report with data, report empty state, subscription expired state, trip detail, settings, confirmation modal, alert center, and notification settings. Rules and thresholds belong inside those frames as values, badges, helper text, charts, or callouts.

Use only one clear device boundary for mobile frames. Avoid heavy inner outlines that compete with product content; color and emphasis should follow the discovered Design context, product component semantics, and local PRD meaning.

For message, alert, notification, or event-list frames, include enough structure to support discussion: event type, severity or status, time, read/unread state when relevant, and the user-visible jump to detail or related trip. Do not truncate key values such as speeds, thresholds, counts, or times.

For web/admin products, frames should usually include:

- top bar,
- side navigation or toolbar,
- cards/tables/forms,
- state or action areas.

## Anti-Patterns

- Do not make every PRD section a separate sparse flow diagram.
- Do not let showcase frame types determine real project output.
- Do not draw internal generation labels such as `section describes...`, `scene_type_reason`, `Yes`, or `No`.
- Do not let rule-only sections become standalone screens; attach them to the closest UI frame as state, copy, or annotation.
- Do not cycle through showcase scene types for real projects.

## Optional Design Context

When `Design/design.md` or `Design/references/*` exists, index it and require the authoring agent to read it. Use it as guidance for platform, navigation names, component vocabulary, density, modal behavior, and visual rhythm. It is optional as a dependency, but mandatory to inspect when present; do not claim pixel-level ingestion unless the resulting brief and board visibly reflect those references.
