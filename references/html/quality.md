# 宣讲台契约与质量检查

本文件约束 Finn ProtoPilot HTML 宣讲台的维护契约和验收检查。宣讲台应由 `templates/html/prototype-shell.html`、`prototype-shell.js`、`prototype-base.css` 和 `scripts/protopilot.py` 生成/维护，不让 agent 每次手写。根目录 `templates/prototype-shell.html` 仅作短期兼容 fallback，不作为新的维护入口。

## 宣讲台范围

宣讲台包括：

- PRD 演讲模式与 Markdown Viewer。
- 左侧目录 `proto-nav-dock`。
- 标注开关。
- 改文字/大改作者工具。
- 高光光标。
- 单界面放大 spotlight。
- `prototype-base.css` / `prototype-shell.js` 引用。

业务原型内容最终只允许放在 `.proto-generated-area` 的 `PROTO_GENERATED_AREA_START/END` 插槽内。复杂需求的创作源优先放在 `prototype/prototype-content/`；`prototype/generated-area-fragment.html` 与 `prototype/index.html` 是构建/注入产物。

## Markdown Viewer 状态

Markdown Viewer 是宣讲台内的独立长期维护模块，必须具备固定状态，不允许空白：

- 自动读取绑定 PRD：从 `.proto-prd-viewer[data-prd-src]` 读取同目录 Markdown。
- 渲染方式：Marked 解析 Markdown，`.proto-prd-markdown.typora-preview` 承载普通 DOM，视觉由 ProtoPilot 自维护 Typora 风格 CSS 控制。
- 加载中：显示“正在加载 PRD…”。
- 成功：显示 PRD 内容。
- 失败：显示固定提示，包含绑定路径、可能原因和处理建议。
- 手动选择：允许用户临时选择 `.md` / `.markdown` 文件，用 `FileReader` 渲染；不修改 `index.html`，不改变绑定路径。

失败提示必须提到：

- 是否可能直接用 `file://` 打开。
- PRD 与 `index.html` 的相对路径是否正确。
- Marked CDN 或本地文件读取是否被阻止。
- 可通过本地 HTTP 或手动选择同目录 Markdown 解决。

## 模板契约

`templates/html/prototype-shell.html` 是 HTML 模板事实源；`templates/prototype-shell.html` 仅是短期 fallback。HTML 模板必须包含：

- `{{title}}`、`{{lang}}`、`{{prd_viewer_src}}`、`{{design_context}}`、`{{generated_area}}` 占位符。
- `PROTO_GENERATED_AREA_START` / `PROTO_GENERATED_AREA_END` 插槽标记。
- `#prd-drawer`、`.proto-prd-viewer`、`#prd-markdown-output`、`#prd-viewer-fallback`、`#prd-file-input`。
- `#proto-nav-dock`、`#proto-nav-scroll`、`#proto-nav-trigger`。
- `#float-prd-btn`、`#annotation-toggle`、`#presentation-laser-toggle`。
- `#float-edit-btn`、`#float-revision-btn`。
- `#proto-step-spotlight`。
- `#proto-generated-area` 必须是 `<main class="proto-page">` 内唯一主业务区；宣讲台 JS 的目录、改文字/大改、PRD 左列预览都应优先查询这个主业务区，避免误读 spotlight 挂载区。
- `#proto-spotlight-mount` 必须同时带 `proto-generated-area` class，确保全屏 spotlight 仍命中业务区作用域 CSS；该挂载点在 DOM 上位于 `<main class="proto-page">` **之外**。因此 **`prototype-base.css` 里凡是在 `body.proto-prd-mode` 下仅用于「左列预览只保留当前焦点步骤」的规则，只能选择器限定为 `main.proto-page .proto-generated-area`（及同源 `.journey-row` / `.journey-step.is-prd-focus` 链路），不得匹配 `#proto-spotlight-mount`。

## 脚本契约

`scripts/protopilot.py` 提供统一子命令：

- `prepare <prd>`：整理 PRD 文件夹、复制宣讲台资产、发现 `design.md` 和参考素材。
- `preflight <prd-or-demand-dir>`：生成前检查设计上下文、需求级参考图、原界面图提示和后续动作。
- `scaffold <prd>`：prepare 后渲染宣讲台 `index.html`。
- `plan <demand-dir-or-prd-inside-it>`：生成或更新 `prototype-plan.json`，记录来源、preflight 处理、分组、步骤、覆盖、参考图、校验和修订历史；默认 merge 旧计划，`--reset` 才重建。
- `init-content <demand-dir>`：根据 `prototype/prototype-plan.json` 创建或刷新 `prototype/prototype-content/manifest.json`、`content.css`、`screens/` 和 screen stub。
- `package-check <demand-dir>`：检查内容包源文件、manifest、screen 文件、CSS 作用域和 plan 对齐；`--strict` 用于完成前检查。
- `build-content <demand-dir>`：从内容包构建 `generated-area-fragment.html`，统一生成 journey 包装并同步 plan；`--check` 只检查 fragment 是否新鲜。
- `validate-plan <prototype-plan.json>`：检查计划覆盖、参考图/原界面图处理、未覆盖状态和 strict 结果。
- `render-fragment <prototype-plan.json>`：legacy/占位能力，按计划生成 `generated-area-fragment.html`，使用 UTF-8 写入并补齐关键 `data-proto-id`；输出会标记为 placeholder，不可作为复杂完成版。
- `validate-fragment <fragment.html>`：在注入前检查业务片段；`--strict` 会把乱码、非法结构、缺关键 `data-proto-id` 等真实质量问题升级为失败。
- `sync-plan <prototype-plan.json> <fragment.html>`：手写 fragment 严格通过后，按精确 step id 把匹配的计划步骤标记为 rendered；遇到 plan 外 step id 失败，不猜测覆盖、不自动补 omitted。
- `final-check <demand-dir>`：最终交付前检查，同时检查 plan、content package、fragment 和 index，输出 `complete | partial | draft | failed` 状态；复杂交付使用 `--require-content --require-complete`。
- `preview <demand-dir>`：启动或复用 `127.0.0.1` 本地 HTTP 预览，记录 `.protopilot-preview.json`、PID、端口和 TTL。
- `stop-preview <demand-dir>`：停止目录/token 匹配的 ProtoPilot 本地预览服务，并清理预览状态。
- `doctor <demand-dir>`：只读诊断当前需求目录，报告下一步该跑什么。
- `inject <index.html> <fragment.html>`：只替换生成区插槽，不改宣讲台；`--strict` 会先校验片段，失败则不注入。
- `migrate-legacy <legacy-dir> <demand-dir>`：从真实存在的旧草稿目录抽取业务区片段，可选择立即注入；避免 agent 手抄大段 HTML。
- `validate <index.html>`：检查模板插槽、固定 DOM、Markdown Viewer fallback、宣讲台资产和绑定 PRD；`--strict` 会把关键业务质量退化升级为失败。
- `selfcheck`：临时生成最小原型并跑注入与校验，用于替代长期维护示例 HTML。
- `build-showcase`：刷新 `examples/showcase-html/` 的操作手册式样板原型，用于人工验收和能力展示。

## 默认检查

完成前至少检查：

- `scripts/protopilot.py scaffold` 能生成标准需求文件夹和 `index.html`。
- `scripts/protopilot.py preflight` 能在生成前提示需求级参考图和原界面图检查。
- 复杂新建、多屏、多状态、迁移旧稿能生成 `prototype-plan.json`，并通过 `validate-plan`。
- 内容包链路能通过：`init-content`、替换 screen stub、`package-check --strict`、`build-content`、`build-content --check`。
- `scripts/protopilot.py render-fragment` 作为 legacy/占位能力仍能按计划生成 UTF-8 业务片段，`validate-fragment --strict` 通过。
- 手写复杂 fragment 时，`validate-fragment --strict` 通过后必须运行 `scripts/protopilot.py sync-plan`，并确认未匹配 step 没有被误标完成。
- `scripts/protopilot.py inject` 只替换 `PROTO_GENERATED_AREA_START/END` 插槽；复杂需求使用 `inject --strict`。
- `scripts/protopilot.py validate` 通过；复杂需求还要 `scripts/protopilot.py final-check --require-content --require-complete <demand-dir>` 通过。基础 `validate` 只代表宣讲台结构可用，不代表计划覆盖完成。
- `index.html` 引用同目录 `prototype-base.css` 和 `prototype-shell.js`。
- Markdown Viewer 绑定源 PRD，且有 `#prd-markdown-output`、`#prd-viewer-fallback` 和 `#prd-file-input`。
- 没有要求 agent 手写宣讲台 DOM。
- 需要查看时，`preview <demand-dir>` 返回可打开的本地 URL；完成查看后可用 `stop-preview <demand-dir>` 停止服务。

## Markdown Viewer 检查

- 本地 HTTP 下能自动显示绑定源 PRD。
- 绑定路径错误或 Marked 不可用时，显示固定提示，不空白。
- `file://` 打开时，提示使用本地 HTTP 或手动选择 Markdown。
- 手动选择 `.md` / `.markdown` 后能临时渲染内容。
- 手动选择不修改 `index.html`，也不改变绑定 PRD 路径。
- Viewer 中没有无来源的 AI PRD 摘要。
- 标题、列表、引用、代码块、图片和表格使用同一套 Typora 风格；宽表格只能在 PRD 面板内横向滚动，不能撑破宣讲台。

## 本地预览检查

- `preview <demand-dir>` 返回 `url`、`port`、`pid`、`demand_dir`、`status` 和 `stop_command`。
- 重复运行 `preview` 复用仍然存活且目录/token 匹配的服务，不重复占用端口。
- 状态过期或进程退出时，`.protopilot-preview.json` 会被清理并重建。
- `stop-preview <demand-dir>` 只停止匹配的 ProtoPilot 预览服务，不误杀其他本地服务。
- 本地 HTTP 下目录、PRD Viewer、标注、spotlight 和改文字入口可正常使用。
- 本地 HTTP 下改文字保存必须写回 `prototype/prototype-content/screens/*.html`，并自动重建 `prototype/generated-area-fragment.html` 与注入 `prototype/index.html`；非 preview 或 legacy fragment 不能假装保存。

## 生成原型验收

- `final-check` 状态定义：
  - `complete`：strict 通过，plan final 通过，没有未解释遗漏。
  - `partial`：strict 通过，未渲染 step 都有 `coverage.omitted` 解释。
  - `draft`：HTML 可打开但计划或 strict 未闭合；不应作为完成版交付。
  - `failed`：缺文件、strict 失败、来源状态未记录、plan final 失败、内容包不合法、fragment 落后于 screen 源文件，或 plan/index step id 不一致。
- PRD 路径正确，`index.html` 位于需求文件夹的 `prototype/` 子目录。
- 若产品级 `Design/design.md` 存在，已读取并在结果说明中提到。
- 若 preflight 输出 `design_context_warning` 或 `recommended_design_context`，已读取推荐的 README/token 文件，并说明为什么不直接套用 `design.md`。
- 已检查产品级和需求级 assets/references 中的参考图或素材。
- 参考图不是只被发现：交付说明列出了打开过的图片和具体借鉴点。
- `.proto-generated-area` 只包含业务原型内容。
- 视觉优先匹配 `design.md` 和参考图，而不是只套默认冷钴蓝。
- 复杂新建、多屏、多状态、迁移旧稿已先产出并确认基于 `prototype-plan.json` 的生成计划卡，没有在无真实 legacy fragment 时计划迁移。
- 复杂需求默认存在 `prototype-content/manifest.json`、`content.css` 和 `screens/*.html`；每个 screen 只写界面主体，不写完整网页壳或 journey 包装。
- screen stub 已替换；screen 文件不包含 `<script>`、`<style>`、stylesheet link、inline handler、`javascript:` URL 或 raw `id`。
- `content.css` 选择器受 namespace 约束，没有裸元素、`:root`、`*` 或 shell class/id 覆盖。
- `prototype/generated-area-fragment.html` 已由 `build-content` 生成且 `build-content --check` 通过；`prototype/index.html` 的生成区与 fragment 一致。
- `prototype-shell.js` 暴露幂等的 `window.ProtoPilotShell.refresh()`、`resetModes()`/`reset()`、`serializeCleanHtml()`/`serialize()`；重复 refresh 不应重复绑定目录事件，也不应默认退出 PRD mode 或 spotlight。
- 轻交互只能使用声明式白名单 `data-proto-action`，如 `toggle`、`show`、`hide`、`toggle-class`、`activate`、`toast`；不允许 screen 私有 JS 或业务状态机。
- 主线验收只认 `prototype-content`、fragment、index 和本地 preview；其他编辑绘制能力不在本 skill 维护。
- 复杂 PRD 没有出现“plan 很大、HTML 只做少数精选屏、plan 未同步且 omitted 为空”的伪完成状态。
- 多界面已按 PRD 自然结构、平台、状态类型或流程阶段组织；不硬控 group 数量。单个 `.journey-row` 超过 4 个界面只作为上下文提示，不作为 strict 失败。
- PRD 状态码、加载、空态、错误、过期、有数据等状态已拆成独立 `.journey-step`，没有被折叠进单个手机内 Tab/Segment。
- 单个 `.journey-step` 默认只有一个主要手机/页面界面；两个不同界面不能共用一个标题。
- 手机界面是完整屏结构：`.phone-frame > .phone-screen > .app-screen` 填满手机内部，没有大圆角半截主容器。
- 同一份 PRD 内复用一组产品语义块和局部样式，导航、按钮、列表、卡片、提示条和弹窗视觉一致。
- 状态栏和标题栏一致；默认状态栏是 `12:30 + 5G`，没有 LTE/5G/空白混用。
- 关键业务元素有稳定 `data-proto-id`，改文字/大改能选中。
- 业务按钮优先匹配产品/参考图风格，没有大量套用宣讲台通用 `primary-btn` / `secondary-btn`。
- 中文 PRD 的可见文案、注解、按钮尽量中文。
- Lucide icon 正常；没有用 emoji，也没有用裸 `>`、`...`、`→` 代替正式 UI icon。
- Mobile/Web/Desktop 表达方式正确。
- 长规则和表格没有塞进手机屏幕。
- 手机弹窗、遮罩、底部操作区都限制在 `.app-screen` / `.phone-screen` 内，没有覆盖整个宣讲台画布。
- 弹窗状态复用同一页面底层 DOM，只叠加遮罩和弹窗；弹窗底下界面没有变成另一版布局。
- 长手机页没有拉长手机壳，只让内容延展。
- 长手机页和下一行/下一组之间保留足够画布间距。
- 短页面没有滥用 `.is-extended`；只有内容确实超过一屏时才启用长页模式。
- 标注优先在手机外侧留白，没有进入手机主内容流、夹在两个手机之间或遮挡导航/主要内容。
- 没有额外生成横跨画布的背景说明灰条；来源说明应在交付说明中表达。
- 文字不重叠、不溢出按钮或卡片。

## 改文字/大改验收

- 改文字和大改互斥；进入时关闭 PRD 模式且不跳动页面。
- 改文字只用于安全可见文本修订；进入后右上角显示“重置 / 保存 / 退出”，不显示旧侧边操作面板，不提供删除入口。
- 改文字保存只在 `preview` 下可用，保存时带原文校验，失败时不覆盖源文件、不重建。
- 大改用于结构、布局、规则、状态分支等备注；按钮文案为“复制给 AI”，复制内容必须带明确执行指令和校验链路。
- 重置、退出等常见操作可用 icon-only，并有 `title`/`aria-label`。

## 宣讲台回归

改动宣讲台后：

1. 跑 `scripts/protopilot.py selfcheck`。
2. 用本地 HTTP 打开自检原型（或任一标准 `index.html`），检查 Markdown Viewer、目录、标注、高光光标、spotlight、改文字、大改。**进入 PRD 演讲模式 → 点击「全屏放大当前界面」**：放大区不得空白，须与左侧预览同款结构；改版 `prototype-base.css` 时须确认 PRD 模式下的收起规则仅限 `main.proto-page .proto-generated-area`，不误伤 `#proto-spotlight-mount`。
3. 跑 `node --check prototype-shell.js`。
4. 跑 skill 校验。

## Showcase 验收

`examples/showcase-html/` 是人工验收面，不是业务生成模板。维护它时：

- 运行 `scripts/protopilot.py build-showcase`，不要手工同步整份 `index.html`。
- 运行 `scripts/protopilot.py validate examples/showcase-html/index.html`。
- 运行 `scripts/protopilot.py validate --strict examples/showcase-html/index.html`。
- 本地 HTTP 打开后检查：PRD Viewer 能读 `proto-pilot-manual.md`，目录能跳转，PRD 模式左侧有单界面，spotlight 不空白，改文字/大改能选中关键元素。
- 检查样板覆盖：多状态拆屏、长页面、弹窗复用底层页、标注避让、Web/PC 工作台、验收对照。
- 不把 showcase HTML 复制到真实业务需求里；真实需求仍必须读 PRD、`Design/design.md` 和参考图。
## Quality Check

`final-check` remains the deterministic final delivery check. It checks package integrity, freshness, plan coverage, fragment/index consistency, and complete/partial/draft status.

`quality-check <demand-dir|index.html> [--render] [--strict]` is a generic quality radar. It should be used before polished handoff, but it does not replace `final-check`.

- Static checks read the plan when available and detect explanation-only screens, missing section disposition/annotation coverage, annotation contract issues, long annotations, dangerous generated CSS, and authoring-state residue.
- `--render` adds browser geometry checks when Playwright is available: collapsed surfaces, surface overflow, annotation overlap, and button/badge overflow.
- Default mode reports warnings; `--strict` turns quality blockers into failures.
- Checks must stay domain-neutral. Do not encode Chat, CRM, approval, support, map, finance, or other business-specific rules.

## Text Edit Handoff

- Text edit is text-only. It may adjust safe visible text such as titles, buttons, labels, list rows, messages, empty states, and hints.
- Removing cards, deleting modules, changing layout, or structural edits must go through big-change notes or source-file edits.
- For content package demands opened with `preview`, saving text edits writes a `replace_text` patch back to `prototype/prototype-content/screens/*.html`, then rebuilds and injects the page.
- `apply-edit-patch <demand-dir> <patch-file>` remains a CLI fallback for copied patches, but the main user flow is preview save.
- Clean HTML/patch output must not retain `contenteditable`, selected-state classes, edit popovers, `data-editable-text`, `data-edit-removable`, or `data-proto-auto`; content patches only emit `replace_text`.
