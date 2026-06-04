# Generated Area Rules

`#proto-generated-area` stays compatible with the maintained ProtoPilot shell.

## Required Structure

The generated area must contain:

- `.section-divider` for groups,
- `.journey-row` containers,
- `.journey-step[data-proto-id][data-proto-label]` cards,
- `.step-header` with `.step-number` and `.step-title`,
- `.proto-excalidraw-card[data-scene-src][data-step-id]` inside each step,
- `.proto-excalidraw-preview` inside each Excalidraw card.

The shell navigation, PRD mode, and spotlight depend on the `.journey-step` structure. Do not move the generated-area start/end markers.

## Excalidraw Mount

Inside a step, use only a preview mount and data attributes:

- `data-scene-src` points to `prototype/prototype-excalidraw/boards/*.excalidraw`,
- `data-step-id` matches the step id,
- `data-board-id` identifies the source board when present,
- `data-frame-id` identifies the frame to preview when present,
- `data-scene-title` is display metadata,
- `data-scene-type` is validation metadata.

Do not show scene paths, scene type chips, or per-card edit buttons in the presentation UI. The left author tool controls edit mode.

## Safety

Scene references must be relative. The generated area must not include absolute local paths, `file://` URLs, remote scene URLs, business HTML screens, `prototype-content/`, `content.css`, or HTML fragment patch workflows.
