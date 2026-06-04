# 业务生成区规则

本文件约束 agent 生成的业务内容。复杂需求的主要创作源是 `prototype/prototype-content/screens/*.html` 与 `prototype/prototype-content/content.css`；`prototype/generated-area-fragment.html` 是由 `build-content` 拼出来、用于兼容现有宣讲台的产物。完整 `prototype/index.html` 的宣讲台由 `scripts/protopilot.py scaffold` 根据 `templates/html/prototype-shell.html` 生成；根目录 `templates/prototype-shell.html` 仅作短期兼容 fallback。

## 生成目标

先由 `prototype-plan.json` 做 PRD section 分流：
- `screen`：真实用户可见的页面、状态、弹层、toast 或流程节点，才会进入 `prototype/prototype-content/screens/`。
- `annotation`：贴近具体界面的短说明，必须作为 `.annotation` 放在产品 surface 外。
- `prd_viewer`：背景、目标、概述、规则、规格、字段、验收、SOP、风险、来源说明等长说明，留在 PRD Viewer。
- `delivery_note`：参考图使用、来源缺口、人工判断、发布说明等，写进交付说明。
- `omitted`：明确不做可视化的内容，必须记录原因。

不要为了讲清一段说明而单独造一个手机屏。复杂 PRD 可以有很多真实 screen，但说明型材料不应伪装成产品界面。

复杂需求优先输出 screen 源文件，不是整页 HTML，也不是完整 `.journey-step`：

```html
<!-- prototype/prototype-content/screens/step-1.html -->
<div class="phone-frame" data-proto-id="step-1-phone" data-proto-label="首页手机界面">
  <div class="phone-screen">
    <div class="app-screen" data-proto-id="step-1-screen" data-proto-label="首页界面">
      <!-- Mobile/Web/Desktop 业务原型内容 -->
    </div>
  </div>
</div>
```

screen 文件写完后运行：

```bash
python scripts/protopilot.py build-content <demand-dir>
python scripts/protopilot.py inject --strict <demand-dir>/prototype/index.html <demand-dir>/prototype/generated-area-fragment.html>
python scripts/protopilot.py final-check --require-content --require-complete <demand-dir>
```

构建后的兼容片段形态如下，由脚本生成包装结构：

```html
<div class="proto-area-label"><span class="proto-generated-note">生成区 · xxx 流程</span></div>
<section class="journey-row">
  <div class="journey-step is-active" id="step-1" data-proto-id="step-1" data-proto-label="首页">
    <div class="step-header">
      <span class="step-number">1</span>
      <span class="step-title">首页</span>
    </div>
    <!-- Mobile/Web/Desktop 业务原型内容 -->
  </div>
</section>
```

简单需求或旧稿兼容时，可以直接维护 fragment；完成后把片段保存成临时 HTML，再运行：

```bash
python scripts/protopilot.py inject <index.html> <generated-fragment.html>
```

## 结构规则

- 内容包模式下，`.section-divider`、`.journey-row`、`.journey-step`、`.step-header`、`.step-number`、`.step-title` 都由 `build-content` 生成，screen 文件不要手写这些结构。
- fragment 兼容模式下，用 `.section-divider` 或 `.proto-area-label` 分组，用 `.journey-row` 承载一组步骤，用 `.journey-step` 表示一个讲解节点，并提供稳定 `id`。
- 每个 screen 文件必须替换掉 `init-content` 生成的 placeholder stub，并且有且只有一个主 surface：`.phone-frame` 或 `.web-surface`。
- screen 文件不要写 raw `id`；spotlight 会 clone 当前界面，raw id 会在 DOM 中重复。需要定位时统一使用 `data-proto-id`。
- 需要大改定位的元素加 `data-proto-id` 和 `data-proto-label`。
- 关键业务元素必须加 `data-proto-id` 和 `data-proto-label`：卡片、列表行、按钮、状态块、弹窗、图表、空态、标注都算关键元素。
- 复杂 PRD 手写 fragment 时，`.journey-step[data-proto-id]` 必须使用 `prototype-plan.json` 中的 step id；生成后运行 `validate-fragment --strict` 和 `sync-plan`。不要用自定义 step id 交付，否则计划无法追踪覆盖。
- screen 文件默认禁止 `<script>`、`<style>`、stylesheet `<link>`、inline `on*=` 和 `javascript:` URL。需要少量演示交互时，只能使用声明式 `data-proto-action` 白名单；复杂状态继续拆成多屏。
- 不要在第一个 `.journey-row` 前生成横跨画布的来源说明、背景说明或灰色提示条。需要说明来源时，放到交付说明；需要讲解差异时，用步骤标题或 `.annotation`。

## 声明式轻交互

轻交互服务内部宣讲，不实现真实业务状态机。触发元素必须在 screen 主 surface 内，目标查询只作用于同一 screen/step 范围。

- `data-proto-action="toggle"`：切换目标元素的 `hidden` class。
- `data-proto-action="show"` / `hide`：显示或隐藏目标元素。
- `data-proto-action="toggle-class"` / `add-class` / `remove-class`：对目标元素切换、添加或移除 `data-proto-class` 指定 class，默认 `is-active`。
- `data-proto-action="activate"`：在 `data-proto-group` 指定范围内移除 active class，再给目标添加 active class，适合 tab/panel 演示。
- `data-proto-action="toast"`：显示一次宣讲台 toast，可用 `data-proto-message` 指定文案。

示例：

```html
<button data-proto-id="demo-open" data-proto-action="toggle" data-proto-target="[data-proto-id='demo-panel']">展开</button>
<div class="hidden" data-proto-id="demo-panel">这里是展开后的说明。</div>
```

不要用轻交互承载跨 screen 状态、表单校验、网络请求、复杂输入或真实流程跳转；这些内容仍然拆成独立可讲界面。

## 先定本需求语义块

生成多界面前，先在 `prototype/prototype-content/content.css` 写本需求 scoped 样式和可复用类名，然后各界面复用这些类，而不是每个步骤临时发明一套视觉。fragment 兼容模式可用片段内 `<style>`，但复杂需求优先沉到 `content.css`。

- 先确定 3-8 个产品语义块：导航栏、列表行、主按钮、地图/图片块、统计卡、提示条、弹窗、底部操作区等。
- 类名使用产品或需求前缀，并受 manifest namespace 包裹，例如 `.gi-chat .gi-nav`、`.gi-chat .gi-primary-btn`。不要写裸 `button`、`.card`、`:root`、`*` 等全局选择器，也不要覆盖 `.proto-*`、`.journey-*`、`.step-*`。
- 同一份 PRD 内的背景、导航高度、列表行高度、卡片圆角、按钮圆角、字体层级要保持一致；差异必须能从 PRD 或参考图解释。
- 必须先定状态栏和标题栏基线：默认 `12:30 + 5G`，同一份原型内不要混用 LTE、5G、空白状态栏；平台差异只有在 PRD 或参考图明确要求时才拆开表达。
- 必须先定弹窗基线：弹窗页复用原页面底层 DOM，只叠加遮罩和弹窗；状态栏、标题栏、底层卡片/列表要和未弹窗页面一致。
- 外部原型 skill 或设计工具只作为方法参考：吸收“先定组件再拼页面”的顺序，不引入它们的目录结构、运行时、远端服务或审美口号。

## Journey Board

适合大多数 PRD 宣讲。用一组步骤讲清楚“从入口到结果”的路径。

- 多界面不要为了宣讲美观强行压缩；优先按 PRD 自然结构、平台、状态类型或流程阶段拆成生成块。
- `.journey-row` 视觉上会自动换行；单个生成块步骤很多时，只作为上下文负担提示，不作为布局错误。需要降低生成风险时再拆行或拆块。
- `.journey-row`：同一段流程的多个步骤。
- `.journey-step`：单个讲解节点，必须有稳定 `id`。
- 一个 `.journey-step` 默认只放一个主要手机/页面界面；两个不同界面要拆成两个 `.journey-step`，各自拥有自己的步骤标题。
- `.annotation`：解释规则、风险、状态差异。

## 状态拆屏规则

PRD 里的状态分支默认是“多个可讲界面”，不是“一个手机里的小 App”。

- S1/S2/S3/S4、S2-b 等状态码，默认各自生成独立 `.journey-step`。
- 加载、空态、错误、无权限、过期、有数据、无数据等状态，默认各自生成独立 `.journey-step`。
- 不要把多个状态码写进同一个 `.step-title` 或 `data-proto-label`，例如 `驾驶侦测主页（S1/S3/S4/S2-b）`。
- 不要在手机内用 Tab、Segment、Pill 按钮承载多个 PRD 状态，除非真实产品界面本来就有这样的控件。
- 不要把两个不同页面塞进一个 `.journey-step`，否则 spotlight 单界面放大时会同时带出两个界面。
- 如果状态很多，用 `.section-divider` 按 PRD 自然结构分块；分块服务覆盖追踪和上下文控制，不为固定组数牺牲 PRD 完整性。

## State Comparison

适合讲同一页面的加载、空态、列表、错误、权限、异常状态。

- 默认仍然拆成多个 `.journey-step` 并排对比，而不是手机内切换。
- 关键差异用旁注说明，不要把状态解释塞进页面正文。
- 多状态并排时，保持相同手机尺寸、导航结构和对齐，方便评审比较。
- 只有真实产品页面本身就是 Tab/Segment，才复刻这个控件；控件服务产品表达，不服务压缩原型页数。

## Branch Flow

适合讲条件分支、权限分支、不同用户类型或失败路径。

- 主路径放左到右或上到下。
- 分支路径用标签、分栏或轻量 connector 表达。
- 每个分支说明触发条件和结果，不展开成完整应用。

## Mobile App

- 使用 `.phone-frame`、`.phone-screen`、`.app-screen` 等基础类。
- 基础结构必须是 `.phone-frame > .phone-screen > .app-screen`，`.app-screen` 负责承载完整手机界面并填满手机内部。
- 不要在 `.app-screen` 里面再套一个大圆角、固定高度的白色容器当“整页主界面”；这会造成半截屏、圆角破坏和全屏模式失真。
- 固定手机外框。短页面用普通 `.phone-frame`；只有内容确实超过一屏时才加 `.is-extended`。长页模式下手机黑色外框保持标准高度，内容区向下延展，布局盒子必须为延展内容占位，不能压到下一行原型。
- 长手机页之间必须保留足够画布间距；不要用 `min-height` 把内容硬顶到下一行，也不要让上一个手机的延展内容贴住下一组标题或手机。
- 状态栏、导航栏、底部栏只保留讲需求需要的部分。
- 状态栏默认统一写法为 `<div class="phone-status-bar"><span>12:30</span><span>5G</span></div>`；不要把右侧留空。
- 手机内容必须被 `.phone-screen` / `.app-screen` 裁切；不要用负 margin、超大阴影或外层 fixed 元素破坏圆角。
- 底部 CTA、底部 Tab、home indicator 都放在 `.app-screen` 内部，不能伸出手机屏幕。
- 不把长表格、长规则或管理后台内容塞进手机屏。
- 贴底大卡、底部操作区、地图块、bottom sheet 必须处理完整圆角链路。除非语义上就是半截浮层并带明确类名，否则不要写 `border-radius: xx xx 0 0`，也不要让满宽色块顶破手机底部圆角。

## 业务按钮风格

- 手机内按钮优先复刻 `design.md`、参考图或原界面图的尺寸、圆角、颜色、字重和间距。
- 为业务 UI 创建产品语义类名，例如 `.dd-primary-btn`、`.settings-toggle`、`.risk-pill`，不要直接套宣讲台通用 `primary-btn` / `secondary-btn`。
- 只有完全没有设计参考时，才允许临时使用基础按钮风格；交付说明要写清这是兜底。
- 图标按钮用 Lucide 图标和可理解的 `aria-label`，不要用 emoji。
- 返回、更多、设置、关闭、箭头等常见操作必须用 Lucide；不要用裸 `>`、`...`、`→` 代替 icon。文字箭头只允许出现在真实产品文案里。

## Web Page

- 使用 `.web-surface` 或产品设计语境中的页面容器。
- 直接呈现浏览器内页面，不加假的浏览器外框，除非 PRD 要求。
- 后台、列表、表单、详情页要关注信息密度、筛选、状态、权限和批量操作。

## Desktop Page

- 用大屏布局表达多栏、表格、侧栏、工具栏等复杂信息结构。
- 保持可扫描、可比较、可重复操作的工作台气质。
- 不做营销落地页式的大 hero，除非 PRD 本身就是官网/营销页。

## Annotation Patterns

- 注解用于 PM 讲解：业务规则、验收条件、异常处理、与设计/研发待确认点。
- 注解默认可被宣讲台开关控制。
- 注解文案短而具体，不复述整段 PRD。
- 单个界面默认最多 1-2 个标注；必须给标注加稳定 `data-proto-id` / `data-proto-label`。
- 标注优先放界面外侧留白或不遮挡导航标题的位置；同一界面多标注时采用上下堆叠，不要互相重叠。
- 标注不要放进 `.phone-frame`、`.phone-screen`、`.app-screen` 或 `.app-content` 的正常内容流里。
- 不要把标注夹在两个手机之间，或让标注被手机遮挡；需要解释两个界面的关系时，放在两屏上方或下方的留白。

## Interaction Patterns

可用：

- 真实产品本来存在的状态切换。
- Toast/Dialog。
- 展开收起。
- 单选/多选视觉反馈。
- 简单输入演示。

避免：

- 完整登录、权限、数据保存、后端联动。
- 大量真实业务算法。
- 需要用户学习的新操作体系。
- 把手机弹窗放到 `.journey-step` 或 `body` 下覆盖整个画布。

### 手机内弹层规则

- Toast/Dialog/Sheet 必须作为 `.app-screen`、`.phone-screen` 或 `.web-surface` 的子元素。
- 使用 `.dialog-backdrop` 时，结构应放在对应界面容器内：`<div class="app-screen">...<div class="dialog-backdrop"><div class="dialog">...</div></div></div>`。
- 不要在业务片段里给弹层写 `position: fixed`、`width: 100vw`、`height: 100vh`。
- 移动端确认弹窗宽度控制在屏幕内容区内，按钮不超出 `.dialog`。
- 弹窗步骤优先复用同一屏真实 DOM，在底层界面上叠加遮罩和弹窗；避免单独画一页灰色简化底稿冒充上一屏。若必须简化，标注为“等价底图 / 非真实状态”。

## 图标与素材

- 业务 icon 优先用 Lucide。
- 不使用 emoji 当正式 UI icon。
- 真实素材优先来自产品级/需求级 `assets/` 和 `references/`。
- CDN 失败时，业务原型仍要通过文字和结构可理解。

## 不要生成的内容

- 不生成 `<html>`、`<head>`、`<body>`。
- 内容包 screen 不生成 `.journey-row`、`.journey-step`、`.step-header`、`.section-divider`。
- 不生成 Markdown Viewer、`proto-nav-dock`、改文字/大改面板、spotlight、高光光标。
- 内容包 screen 不写 `<script>`；不要依赖运行时动态加载脚本。
- 不写死 AI PRD 摘要。
- 不复制示例 HTML 当业务原型模板。
- 不复制 `examples/showcase-html` 当真实业务模板；showcase 只用于人工验收和能力展示。
- 不默认生成完整单文件内联版本。

## 反模式

- 为同一个 PRD 生成不同名目录。
- 不读取已有 `Design/design.md`。
- 把长 PRD 表格塞进手机屏幕。
- 只套默认冷钴蓝，不参考产品视觉。
- 每个界面临时发明不同按钮、卡片、导航样式，导致同一份 PRD 内视觉不一致。
- 在画布顶部生成大段背景说明或来源灰条，挤占宣讲区域。
- 把 S1/S3/S4/S2-b 等多个 PRD 状态塞进一个手机内 Tab/Segment。
- 在 `.app-screen` 内用大圆角半截容器承载整页，导致手机屏幕不完整。
- 贴底模块只圆上角、不圆下角，或满宽色块破坏手机底部圆角。
- 大量使用 `primary-btn` / `secondary-btn` 当业务按钮。
- 标注进入手机主内容流、覆盖导航栏，或被两个手机夹住。
- 复杂 PRD 绕过 `prototype-plan.json` 直接手写超长业务 HTML，导致上下文漂移、编码风险或覆盖缩水。
- 只做少数精选屏但没有同步 `prototype-plan.json`，也没有在 `coverage.omitted` 里说明未覆盖 step；这种结果只能算失败样本，不能算部分完成。
## Screen Eligibility

- A screen source file represents a user-visible product surface: page, state, modal/sheet/toast, or a real product flow node.
- Explanation-only material must not become a phone or web product screen. Examples: rule notes, source audit, field definitions, acceptance checklist, implementation notes, background, risk list, PRD summary.
- Short contextual explanation belongs in `.annotation`; long rules, tables, field matrices, and acceptance lists stay in the PRD Viewer or delivery notes.
- If a table/list is itself the product UI, render it as UI. If it is a PRD rule matrix, do not turn it into a product screen.
- Do not limit screen count for real states. The rule is not “fewer screens”; the rule is “product states are screens, explanation material is not.”
