# Excalidraw ProtoPilot Workflow

## Goal

Create PRD walkthrough prototypes with the stable ProtoPilot shell and editable Excalidraw storyboard boards. The shell is the stage; board frames are the replaceable business prototype source.

The generation path starts from the PRD. `Design/design.md` plus `Design/references/*` are not hard dependencies, but they are mandatory inputs when present. If they exist, read them before authoring boards and extract platform, navigation, component, density, modal, and visual rhythm hints.

New demand folders keep the user-maintained PRD at the root and put all prototype files under `prototype/`:

```text
feature-name/
  feature-name.md
  prototype/
    index.html
    prototype-plan.json
    generated-area-fragment.html
    prototype-excalidraw/
      manifest.json
      boards/
```

## State Handling

- **Bare PRD**: run `preflight --adapter sketch`, then `scaffold --adapter sketch`; scaffold moves the PRD into the demand folder so the folder owns the single working PRD file and creates initial semantic board skeletons. The next step is not delivery; open the plan and boards for a semantic authoring pass.
- **Demand folder without boards**: run `plan --adapter sketch`, read the semantic frame specs, author boards from the PRD/design context, then run `init-scenes` and `build-scenes`.
- **PRD changed**: rerun `plan --adapter sketch`, run `init-scenes`, review created/preserved boards, run `quality-check`, then rebuild.
- **Board edited manually**: run `scene-check`; if hashes are stale, run `init-scenes`.
- **Browser preview or editing needed**: run `preview`; open the served `index.html`, enter edit mode when needed, click a prototype, edit, and save. `serve-edit` remains as a compatibility alias.
- **Save service unavailable**: use the automatic `.excalidraw` download fallback and replace the board file manually if needed.

## Fixed Script Flow

Default happy path:

```bash
python scripts/protopilot.py preflight --adapter sketch <prd-or-demand-dir>
python scripts/protopilot.py scaffold --adapter sketch <prd-path>
python scripts/protopilot.py plan --adapter sketch <demand-dir>
python scripts/protopilot.py init-scenes <demand-dir>
python scripts/protopilot.py build-scenes <demand-dir>
python scripts/protopilot.py scene-check <demand-dir>
python scripts/protopilot.py quality-check <demand-dir> --strict
python scripts/protopilot.py validate <demand-dir-or-index>
python scripts/protopilot.py shell-diff-check
python scripts/protopilot.py preview <demand-dir>
```

Local preview serves only the demand folder on `127.0.0.1`, writes `.protopilot-preview.json`, reuses a live matching service, and defaults to a 240 minute TTL. Stop it with:

```bash
python scripts/protopilot.py stop-preview <demand-dir>
```

If `python` is not on PATH, run the same commands with the available Python interpreter reported by `doctor` or by the Codex workspace dependency runtime.

## Planning Rules

`plan` writes schema version 4. It must separate PRD sections into prototype steps, storyboard boards, semantic frame specs, auto-draft storyboard briefs, and coverage disposition:

- user-visible pages, mobile pages, overlays, toasts, drawers, key flows, state comparisons, permission branches, and list/table operations become scene steps;
- documentation purpose, revision history, background, goals, terminology, reference links, long specs, SOP, and delivery notes stay in coverage disposition;
- rule-only sections should usually attach to nearby UI frames instead of becoming standalone diagrams;
- new Sketch projects split large storyboard flows into multiple boards; each board should contain at most 6 frames so editing stays manageable;
- every frame records platform, surface kind, frame intent, primary UI regions, key copy, state data, source evidence, design hints, and a storyboard brief with screen role, surface archetype, component inventory, visible copy, data examples, states, jumps, annotations, design refs, and must-not-draw exclusions.

Showcase output is only a capability demo. Do not use its seven scene types as a rotation template for real PRDs.
Real projects must not rotate through `flow/state/web/overlay/decision/table/mobile`; frame type comes from PRD semantics and `semantic_frame_spec`.

Do not collapse planner, brief, and board authoring into one step:

- Planner: coverage, grouping, platform, surface kind, frame intent, and PRD evidence.
- Storyboard brief: screen role, surface archetype, component inventory, visible copy, data examples, states, jumps, annotations, design refs, and must-not-draw exclusions.
- Board authoring: draw only from the reviewed brief, using the PRD heading as trace metadata.

Before using generated skeleton boards as final output, perform a fourth-layer pass using `references/sketch/prd-to-storyboard-semantics.md`. Replace sparse flow/matrix placeholders with product surfaces whenever the PRD describes a page, state, list, setting, overlay, detail, message, or mobile app screen. Treat auto-draft `storyboard_brief` as a review target, not proof that authoring is finished.

If a real PRD feels like it has "no template", continue from the semantic frame spec and storyboard brief. Do not add a new skill template during demand generation. The fix is to author better board/frame content in `prototype/prototype-excalidraw/boards/*.excalidraw`, not to change the skill.

## Done Definition

- Design context was read when present, or confirmed absent.
- Every frame's semantic spec has been reflected in the `.excalidraw` board.
- Skeleton copy and repeated skeleton structure have been replaced where they would otherwise dominate.
- Showcase patterns did not leak into the real project.
- `quality-check --strict` passes together with `scene-check`, `validate`, and `shell-diff-check`.

## Preview And Editing

- The default presentation preview is official `exportToSvg` output rendered in the browser.
- The generated inline SVG is a static fallback, not the source of truth.
- The editor modal uses the official Excalidraw component.
- In board/frame mode, previews export only the frame bound to a `.journey-step`.
- Presentation sections follow `plan.groups` so HTML and Sketch walkthroughs share the same PRD/module grouping.
- Sketch boards are editing partitions only; Part 1 / Part 2 must not appear as presentation group titles or card text.
- Excalidraw frames stay in the real board source for editor navigation and stable export bounds, but generated frames use a white border and no extra caption so they do not visually duplicate the shell title.
- Do not hide frames with SVG-layer tricks, transparent bounds rectangles, forced `viewBox` changes, or reduced frame opacity. The source board should carry the intended presentation result.
- The editor modal opens the whole board so related frames can be edited together.
- Saving writes the `.excalidraw` board, refreshes manifest hashes, and regenerates the generated area fallback.
- `preview` is the normal local viewing and editing service. It can serve static files and handle the Excalidraw save API.
- `serve-edit` is kept only for older habits; prefer `preview` in new instructions and handoffs.

## Layer Discipline

- Flow problems belong in `scripts/protopilot.py` or this workflow reference.
- Excalidraw preview/edit/save problems belong in `prototype-excalidraw.js/css`.
- Business prototype quality belongs in the `.excalidraw` boards and frames.
- Semantic generation quality belongs in `quality-check`; shell validation belongs in `validate` and `shell-diff-check`.
- Shell problems belong in the base shell assets only when the shell itself is broken.

Do not solve scene or adapter problems by rewriting PRD Viewer, navigation, spotlight, or shell layout code.

## Authoring Safety

This skill is still pre-launch, so default generated structure can be tightened without old-project compatibility branches. Within a single run, still preserve the user's current hand edits unless they explicitly ask to rebuild.
