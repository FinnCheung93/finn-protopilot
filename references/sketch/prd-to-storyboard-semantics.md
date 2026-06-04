# PRD To Excalidraw Storyboard Semantics

This is the fourth-layer generation contract for Excalidraw ProtoPilot. It governs the business prototype content inside Excalidraw boards, not the stable presentation shell.

## Source Order

Read sources before authoring boards:

1. PRD/spec.
2. Nearest `Design/design.md`, if it exists.
3. Product or demand `Design/references/*`, `assets/*`, or `references/*` images, if they exist.
4. Existing `.excalidraw` boards when updating.

Design context is optional as a dependency, but mandatory as an input when present. If it exists, extract platform, navigation terms, component vocabulary, density, radius, modal behavior, color rhythm, and repeated UI regions.

## Semantic Frame Spec

Do not jump directly from a PRD heading to drawn shapes. First decide the frame intent:

- `platform`: `mobile` or `web`.
- `surface_kind`: page, list, detail, settings, overlay, state, or entry/flow.
- `frame_intent`: the business question this frame helps discuss.
- `primary_ui_regions`: navigation, content, action, state, modal, table, card, or form regions.
- `key_copy`: PRD-derived visible copy.
- `state_data`: empty/error/loading/success/expired/permission variants.
- `source_evidence`: at least two PRD snippets or headings.
- `design_hints`: design.md and reference observations when present.

## Storyboard Brief

Convert each semantic frame spec into a fourth-layer brief before authoring shapes:

- `screen_role`: why this frame exists in the product journey.
- `surface_archetype`: concrete product surface, such as device home, report dashboard, trip detail, settings, alert center, drawer, confirmation modal, or chat list.
- `component_inventory`: components that must be visible.
- `visible_copy`: product copy that may appear on the canvas.
- `data_examples`: real-looking data values from PRD/design context.
- `state_variants`: empty, enabled, expired, blocked, loading, or error states carried by this frame.
- `interaction_jumps`: where the user goes from this frame.
- `annotations`: rule notes that belong near the UI, not as standalone screens.
- `design_refs`: design context used for platform, navigation, component, and density decisions.
- `must_not_draw`: non-product artifacts such as iframe embeds, TODOs, Axure links, raw URLs, or internal generation labels.

Weak briefs do not proceed to board authoring. Reject briefs that only repeat the Markdown title, only list PRD clauses, use generic `list/detail/settings` without a product surface, contain iframe/TODO/Axure/link text, lack data examples for data-heavy screens, ignore available design refs, or fail to say what the user sees and does next.

## Board And Frame Rules

- One board represents a functional flow or product module.
- One frame represents one real user-visible surface or state.
- Mobile PRDs should become continuous mobile storyboard frames: entry, list/home, detail, settings, modal, empty state, notification, and related states.
- Web/admin PRDs should become web/admin surfaces: top bar, side nav or toolbar, cards, tables, filters, forms, drawers, and modals.
- Flow, matrix, and decision diagrams are supporting explanations. For real products, prefer page/state frames with arrows or callouts over standalone PRD-summary diagrams.
- Rule-only, field-only, and glossary sections attach to the nearest UI frame as callouts or state text; they do not become standalone frames.
- Overlay frames reuse or clone the underlying page surface and add scrim plus modal content.

## Visual Consistency

- Establish board-level component baselines before drawing frames: status/nav bar, list row, card, main button, modal, bottom tab/action area, table row, filter bar, and state block.
- Reuse those baselines across frames in the same board.
- Visible text should come from PRD or design context. Short PM-friendly filler is allowed only for missing copy, never for business rules.
- Every important frame element should carry traceable `customData`: `step_id`, `group_id`, `prd_section`, `board_id`, `frame_id`, and a stable label-like identifier.

## Anti-Patterns

- Cycling through showcase scene types.
- One PRD section equals one sparse `.excalidraw` file.
- Drawing `section describes...`, `scene_type_reason`, `Yes`, `No`, or other internal generation labels.
- Turning version history, project background, goals, glossary, field specs, SOP, or UI reference links into frames.
- Putting all state variants into a tiny tab/segment inside one phone screen when separate frames would be clearer.
