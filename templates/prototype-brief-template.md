# 可选 Prototype Brief 模板

只有当 PRD/spec 足够复杂、需要先用规划摘要降低歧义时，才使用这个模板。

brief 不是必需的事实来源。PRD/spec 仍然是需求来源，`prototype-content/screens/*.html` 是 HTML 原型事实源。不要强制让它同步每次手工 HTML 编辑或浏览器内改文字。

```markdown
# Prototype Brief: <需求名>

## 1. 展示模式

- **模式**：journey-board
- **可选模式**：interactive-app / mixed（如需要）
- **说明**：默认用多端流程看板讲清路径；只有用户明确要求时生成完整交互模拟。

## 2. 宣讲目标

- 目标读者：开发 / UI / 评审 / 业务方
- 本原型要讲清：
  - <核心路径>
  - <关键状态>
  - <容易误解的规则>

## 3. 宣讲步骤

| Step | 平台 | 页面 / 状态 | 目的 |
| --- | --- | --- | --- |
| 1 | Mobile App | <页面名> | <讲清什么> |
| 2 | Web Page | <页面名> | <讲清什么> |
| 3 | Mobile App | <页面名 / 状态> | <讲清什么> |

## 4. 步骤关系

- Step 1 → Step 2：<点击 / 跳转 / 状态变化>
- Step 2 → Step 3：<返回 / 成功 / 失败 / 异常分支>
- 分支或对比：<如有>

## 5. 每步页面内容

### Step 1：<页面名>

- 导航：<标题、返回、右侧操作>
- 主体：<列表、卡片、文案、空态等>
- 操作：<按钮、开关、入口>
- 状态：<默认 / 选中 / 置灰 / 异常>

## 6. 关键标注

| Step | 标注对象 | 标注文案 | 位置建议 |
| --- | --- | --- | --- |
| 1 | <入口> | <为什么重要> | right / left / top / bottom |

## 7. 轻交互

- 点击 <对象>：<高亮 / 切换状态 / 弹 Toast / 弹 Dialog>

## 8. 参考图与素材

- 项目参考图：`Design/references/<file>`
- 当前需求参考图：`references/<file>`
- 当前需求素材：`assets/<file>`

## 9. 生成备注

- 假设：
- 暂不覆盖：
- 与正式 UI 设计稿边界：
- 与当前 HTML 的关系：<新建 / 更新 / 仅作规划参考>
```

## 提炼建议

- Prefer one clear main journey over many branches.
- If a PRD has many detailed rules, show only the states needed to explain the rule.
- Keep long tables in annotations or summary panels, not inside phone screens.
- For mixed Mobile/Web flows, state the platform per step explicitly.
- Skip this brief for simple PRDs where the main walkthrough is obvious.
- If existing HTML has manual edits, use the brief as planning context only; do not overwrite visual details without user approval.
