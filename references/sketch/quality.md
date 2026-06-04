# Excalidraw ProtoPilot Quality Checks

## Required Checks

For normal project delivery, run:

- `python scripts/protopilot.py scene-check <demand-dir>`
- `python scripts/protopilot.py quality-check <demand-dir> --strict`
- `python scripts/protopilot.py validate <demand-dir-or-index>`
- `python scripts/protopilot.py shell-diff-check`
- `python scripts/protopilot.py preview <demand-dir>` when the user needs to view or edit locally.

When modifying this skill itself, also run:

- `python scripts/protopilot.py selfcheck`
- `python scripts/protopilot.py build-showcase`

`shell-diff-check` compares against the bundled shell baseline snapshot in this skill. It must not read sibling HTML skills or git paths, because this skill is physically independent.

Treat strict quality as a required detection check, not a mathematical proof of final quality. Human review must still confirm that every approved storyboard brief is specific and reflected in the board.

Use the bundled or system Python available in the local environment.
If `python` is not on PATH, use the interpreter shown by `doctor` / `selfcheck` rather than changing the skill directory to install dependencies.

## Residue Check

Before important iterations, the skill tree must not contain runtime residue:

- `.protopilot-preview.json`
- `*.log`
- `__pycache__/`, `*.pyc`
- `node_modules/`
- package manager files such as `package.json`, lockfiles, or temporary package metadata

`selfcheck` includes this hygiene check so local previews and test runs do not quietly become bundled skill artifacts.

## Shell Stability

The base shell must remain close to this skill's bundled stable-shell baseline.

Allowed differences:

- the left author tool is an Excalidraw edit-mode action,
- the template adds Excalidraw CSS/runtime hooks,
- the template adds the editor modal mount,
- generated area contains Excalidraw cards instead of HTML screens.

Not allowed:

- rewriting PRD Viewer,
- rewriting navigation,
- rewriting spotlight,
- moving generated-area markers,
- exposing annotation buttons in the Excalidraw skill,
- exposing HTML small-edit/big-edit panels,
- mixing Excalidraw adapter styles into `prototype-base.css`,
- mixing Excalidraw adapter logic into `prototype-shell.js`.

## Scene And Board Checks

- Manifest covers all plan steps.
- Every manifest file exists under `prototype/prototype-excalidraw/boards/` in board/frame mode.
- Every file is valid JSON with `type: "excalidraw"` and an `elements` array.
- Board/frame mode has valid `frame_id` references for every manifest scene entry.
- Frames are non-empty and visually dense enough to be useful.
- Generated elements carry traceable `customData`.
- Manifest hashes match board/scene files before delivery.
- Generated presentation sections must follow `plan.groups`; storyboard boards remain editing partitions and must stay out of visible card text.
- Multi-board projects must keep valid board/frame metadata on every card so editing still opens the correct board.
- Presentation previews should keep stable sizing by preserving real Excalidraw frames in the board source, while generated frames use a white border, full opacity, and no extra caption. Do not weaken the prototype content colors to hide the frame.
- No orphan scene files remain in generated showcase.

## Generation Quality Checks

`quality-check` is the semantic check for PRD-to-storyboard generation. It must catch:

- old plan schema without v4 semantic frame specs,
- strict-mode output that still uses scene entries without frame ids,
- old per-step scene files that remain after board/frame generation,
- missing context summary,
- missing platform, surface kind, frame intent, component baseline, or semantic frame spec,
- missing or weak `storyboard_brief`,
- design context discovered but not reflected in plan hints,
- documentation-only sections generated as frames,
- concept definitions or terminology generated as frames,
- mechanical rotation through showcase scene types,
- frame text dominated by generic template labels,
- visible copy polluted by iframe embeds, TODOs, Axure links, raw URLs, or other non-product text,
- placeholder-heavy mobile frames where the phone exists but the product surface is not specific,
- heavy mobile inner boundaries that overpower the actual product content,
- key values or labels truncated with ellipses, especially speeds, thresholds, counts, and times,
- all preview cards remaining as fallback snapshots without browser confirmation of official render/editing,
- real project plans where most storyboard briefs remain `auto_draft`,
- frames with too little PRD-specific evidence,
- repeated text/structure signatures across many frames,
- repeated layout families that make a storyboard feel like cloned summary cards,
- separate sparse scene files for each step in real projects,
- internal generation labels leaking into drawings,
- missing `scene_type_reason` or `source_evidence`.
- HTML card mounts that do not match manifest board/frame entries.

Use `scene-check` for file and manifest structure, `validate` for shell structure, and `quality-check` for whether the generated prototype actually follows the PRD.

## Browser Checks

Open the generated showcase through `preview`:

- PRD Viewer loads or shows the maintained failure hint.
- Navigation jumps between steps.
- Spotlight opens and is not blank.
- Preview cards show non-empty official SVG previews or clear fallback snapshots.
- Editor opens with visible Excalidraw toolbar/canvas.
- Editor loading shows clear phases and does not stay indefinitely on a generic loading message.
- Save persists through `preview`.
- Without a running preview/save service, save downloads the current `.excalidraw` file.
- `stop-preview` removes the local service state and does not stop unrelated local servers.

For real project checks, open at least the first frame, the last frame, and any user-flagged frame in edit mode. Confirm the editor canvas appears, make one tiny edit, save, refresh, and verify the board-backed preview updates.

## Showcase Checks

The showcase must demonstrate multiple Excalidraw-native prototype forms, not feature explanation cards. It must include at least seven non-empty frame types across storyboard boards.

Showcase frames are examples for capability testing only. Real PRDs must choose frame type from PRD semantics, not from showcase order.
