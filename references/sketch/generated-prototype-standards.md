# Prototype Generation Standards

## General Principles

Generated prototypes should make PRD decisions discussable. Prefer low-fidelity, traceable, editable artifacts over polished but hard-to-change screens.

- Keep the PRD as the fact source.
- Keep one editable storyboard board per functional flow or module; each presentation step previews one frame.
- Create a semantic frame spec before drawing. It must identify platform, surface kind, frame intent, UI regions, key copy, state data, source evidence, and design hints.
- Create a storyboard brief before drawing. It translates the semantic spec into concrete screen role, surface archetype, component inventory, visible copy, data examples, states, jumps, annotations, design refs, and must-not-draw exclusions.
- Choose the representation that fits the PRD: flow, matrix, branch, page wireframe, overlay, list/table, mobile wireframe, or state comparison.
- Do not disguise documentation as product UI.
- Use `design.md` and reference images whenever they are present; they are optional dependencies but mandatory inputs once discovered.
- Do not depend on showcase scenes for real project generation.
- Do not let the presentation shell become the business prototype source.

## Excalidraw Storyboard Guidance

Create clear product discussion boards, not high-fidelity HTML screens.

Good primary frame types include:

- web page wireframes,
- modal/drawer/overlay sketches,
- list/table operation flows,
- mobile app wireframes when the PRD is mobile-contextual,
- empty/error/success state comparisons.

Flow, matrix, and decision diagrams should usually support nearby product surfaces. They are not the default shape for real product PRDs.

Use phone-like frames for mobile products. Do not force phone frames for web/admin products.

## Scene Content

Each frame should be understandable at a glance:

- title or short label,
- primary actors or surfaces,
- important states,
- flow direction or decision points,
- PRD rule notes when they affect behavior.

Real project frames must use PRD-derived wording from `source_evidence`, `business_entities`, `key_copy`, and `states_or_rules`. Generic scaffold phrases are allowed only as fallback labels, not as the main content of multiple frames.

Prefer a few meaningful shapes over dense decorative detail. Use grouping, spacing, arrows, and labels to make relationships obvious.

## Section Disposition

Generate frames only for sections that benefit from a discussable sketch:

- user-visible web or mobile pages,
- modal/drawer/toast/sheet behavior,
- key end-to-end interaction paths,
- state, empty, error, loading, success, or exception comparisons,
- permission or rule branches that shape user behavior,
- list/table/filter/search operations.

Keep these in PRD coverage or attach them to nearby frames instead of making standalone diagrams:

- document purpose, revision history, background, goals, glossary, terminology, UI/reference links,
- concept definitions,
- long field/specification/rule/SOP text,
- implementation or delivery notes.

Do not mechanically rotate through showcase scene types. A real PRD may produce many frames or only a few; the deciding factor is whether the section needs a storyboard frame.

Read `references/sketch/prd-to-storyboard-semantics.md` for the detailed fourth-layer contract.

## Traceability

Generated elements should include:

- `customData.step_id`
- `customData.group_id`
- `customData.prd_section`
- `customData.board_id`
- `customData.frame_id`
- `customData.scene_type_reason`
- `customData.source_evidence`

These fields let validation and later editing connect the drawing back to the PRD plan.
