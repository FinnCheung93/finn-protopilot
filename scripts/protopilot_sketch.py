#!/usr/bin/env python3
"""Finn ProtoPilot Sketch command line tools."""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import mimetypes
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PLAN_FILENAME = "prototype-plan.json"
PROTOTYPE_DIRNAME = "prototype"
EXCAL_DIR = "prototype-excalidraw"
SCENES_DIR = "scenes"
BOARDS_DIR = "boards"
SNAPSHOTS_DIR = "snapshots"
MANIFEST_FILENAME = "manifest.json"
PLAN_SCHEMA_VERSION = 4
FRAGMENT_FILENAME = "generated-area-fragment.html"
PREVIEW_STATE_FILENAME = ".protopilot-preview.json"
PREVIEW_SCHEMA_VERSION = 1
PREVIEW_HOST = "127.0.0.1"
PREVIEW_PORT_START = 4310
PREVIEW_PORT_END = 4399
PREVIEW_DEFAULT_TTL_MINUTES = 240
PREVIEW_START_TIMEOUT_SECONDS = 5.0
PREVIEW_HEALTH_PATH = "/.protopilot-preview-health"
PREVIEW_STOP_PATH = "/.protopilot-preview-stop"
MAX_FRAMES_PER_BOARD = 6
START_MARKER = "<!-- PROTO_GENERATED_AREA_START -->"
END_MARKER = "<!-- PROTO_GENERATED_AREA_END -->"
SHELL_ASSETS = ("prototype-base.css", "prototype-shell.js", "prototype-excalidraw.css", "prototype-excalidraw.js")
EXCALIDRAW_SCENE_TYPES = (
    "flow",
    "state_matrix",
    "web_wireframe",
    "overlay",
    "decision_branch",
    "list_table",
    "mobile_wireframe",
)
EXCALIDRAW_TEXT_FONT_FAMILY = 2
PLAN_DISPOSITIONS = {"prototype_step", "annotation", "prd_viewer", "delivery_note", "documentation_only", "omitted"}
HARD_DOCUMENTATION_TERMS = {
    "文档说明",
    "文档目的",
    "修订历史",
    "项目背景",
    "项目目标",
    "ui图连接",
    "ui 图连接",
    "核心概念定义",
    "概述与目标",
    "需求背景与目标",
    "功能概览",
    "版本与范围",
    "平台差异说明",
    "信息架构",
    "时间显示规则",
    "用户角色",
    "字段说明",
    "权限定义",
    "规则定义",
    "术语",
    "定义",
    "字段",
    "验收",
    "审计",
    "版本记录",
    "范围说明",
    "background",
    "goal",
    "overview",
    "acceptance",
    "revision",
}
SPEC_ONLY_TITLE_TERMS = {
    "核心概念",
    "概念定义",
    "术语定义",
    "功能概览",
    "概述与目标",
    "核心规则",
    "业务逻辑与规则",
    "界面元素与功能规格",
    "功能规格详解",
    "模块详细规格",
    "详细规格",
    "自定义错误码",
    "字段说明",
    "版本与范围",
    "平台差异说明",
    "信息架构",
    "时间显示规则",
    "用户角色",
    "角色与特征",
    "权限定义",
    "规则定义",
}
ALWAYS_SPEC_ONLY_TITLE_TERMS = {
    "界面元素与功能规格",
    "字段说明",
    "字段/规则",
    "功能规格详解",
    "模块详细规格",
    "详细规格",
    "处理规范",
}
EXPLICIT_PROTOTYPE_TITLE_TERMS = {
    "页面",
    "界面",
    "主页",
    "首页",
    "列表页",
    "详情页",
    "内容页",
    "tab",
    "入口",
    "交互",
    "流程",
    "状态",
    "弹窗",
    "浮层",
    "抽屉",
    "toast",
    "sheet",
    "通知",
    "推送",
    "权限",
    "分支",
    "条件",
    "登录",
    "认证",
    "下线",
    "升级",
    "删除",
    "转群",
    "个人中心",
    "聊天历史",
    "会话列表",
    "模型选择器",
    "成员管理",
}
GROUP_TITLE_SCENE_TERMS = {
    "页面",
    "界面",
    "主页",
    "首页",
    "列表页",
    "详情页",
    "内容页",
    "入口",
    "流程",
    "状态",
    "弹窗",
    "浮层",
    "抽屉",
    "登录",
    "认证",
    "个人中心",
    "聊天历史",
}
DELIVERY_NOTE_TERMS = {"交付", "发布流程", "sop", "发布", "source", "delivery", "publish"}
ANNOTATION_TERMS = {"限制", "差异", "提示", "注意", "风险", "说明", "note", "edge case"}
PROTOTYPE_TERMS = {
    "页面",
    "界面",
    "主页",
    "首页",
    "列表页",
    "详情页",
    "内容页",
    "弹窗",
    "浮层",
    "抽屉",
    "toast",
    "sheet",
    "通知",
    "入口",
    "交互",
    "流程",
    "状态",
    "空态",
    "错误",
    "加载",
    "失败",
    "成功",
    "权限",
    "登录",
    "认证",
    "会话",
    "聊天",
    "消息",
    "成员",
    "个人中心",
    "删除",
    "升级",
    "下线",
    "转群",
    "搜索",
    "筛选",
    "列表",
    "表格",
    "管理",
    "配置",
    "后台",
    "规则",
    "条件",
    "分支",
    "screen",
    "page",
    "modal",
    "dialog",
    "drawer",
    "state",
    "flow",
}
TEMPLATE_TEXT_TERMS = {
    "触发",
    "判断",
    "动作",
    "结果",
    "把 PRD 规则串成可讨论的端到端路径",
    "默认",
    "加载中",
    "用户输入",
    "系统反馈",
    "可执行操作",
    "骨架",
    "导航 / 搜索 / 操作",
    "确认操作 / 说明弹窗",
    "关键提示或输入区域",
    "是否满足规则",
    "通过路径",
    "拦截/提示",
    "搜索 / 筛选",
    "新建",
    "移动端任务列表",
    "搜索或筛选",
    "当 PRD 明确是移动场景时，使用移动界面线框表达结构；不是所有原型都强制套手机框。",
}

NORMALIZED_TEMPLATE_TEXT_TERMS = {
    re.sub(r"[\W_]+", "", term.lower())
    for term in TEMPLATE_TEXT_TERMS
    if term
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fail(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8"))


def slugify(value: str, fallback: str) -> str:
    value = re.sub(r"([a-z])([A-Z])", r"\1-\2", value)
    tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", value.lower())
    slug = "-".join(tokens[:8])
    return slug or fallback


def stable_id(prefix: str, title: str, fallback: str) -> str:
    slug = slugify(title, fallback)
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{slug}-{digest}"


def html_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def find_prd(target: Path) -> Path:
    target = target.expanduser().resolve()
    if target.is_file() and target.suffix.lower() in {".md", ".markdown"}:
        return target
    if target.is_dir():
        search_root = target.parent if target.name == PROTOTYPE_DIRNAME else target
        if target.name != PROTOTYPE_DIRNAME and (target / PROTOTYPE_DIRNAME).is_dir():
            search_root = target
        same = search_root / f"{search_root.name}.md"
        if same.is_file():
            return same
        md_files = sorted(path for path in search_root.glob("*.md") if path.name.lower() != "generated-area-fragment.md")
        if md_files:
            return md_files[0]
    fail(f"Cannot find PRD Markdown from target: {target}")


def demand_dir_for_prd(prd: Path) -> Path:
    return prd.parent if prd.parent.name == prd.stem else prd.parent / prd.stem


def prototype_dir_for_demand(demand: Path) -> Path:
    demand = demand.expanduser().resolve()
    return demand if demand.name == PROTOTYPE_DIRNAME else demand / PROTOTYPE_DIRNAME


def demand_root_for_prototype(prototype: Path) -> Path:
    prototype = prototype.expanduser().resolve()
    return prototype.parent if prototype.name == PROTOTYPE_DIRNAME else prototype


def demand_dir_for_target(target: Path) -> Path:
    target = target.expanduser().resolve()
    if target.is_dir():
        return target if target.name == PROTOTYPE_DIRNAME else target / PROTOTYPE_DIRNAME
    if target.is_file():
        if target.parent.name == PROTOTYPE_DIRNAME:
            return target.parent
        if target.suffix.lower() in {".md", ".markdown"}:
            return target.parent / PROTOTYPE_DIRNAME
        return target.parent
    fail(f"Target not found: {target}")


def relative_to(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def browser_relative_path(path: Path, base_dir: Path) -> str:
    rel = os.path.relpath(path.resolve(), base_dir.resolve())
    return rel.replace(os.sep, "/")


def browser_local_path(base_dir: Path, ref: str) -> tuple[Path | None, str | None]:
    value = (ref or "").strip()
    if not value:
        return None, "empty"
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        return None, "not_local"
    if "\\" in value or re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("file://"):
        return None, "filesystem_path"
    path_part = unquote(parsed.path)
    if not path_part:
        return None, "empty"
    return (base_dir / path_part).resolve(), None


def plan_prd_source_for_prototype(prototype_dir: Path) -> str | None:
    plan_path = prototype_dir / PLAN_FILENAME
    if not plan_path.is_file():
        return None
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(plan, dict):
        return None
    source = plan.get("source")
    if not isinstance(source, dict):
        return None
    prd_path = source.get("prd_path")
    return str(prd_path) if prd_path else None


def resolve_plan_prd_source(prototype_dir: Path, plan_src: str) -> tuple[Path | None, str | None]:
    value = (plan_src or "").strip()
    if not value:
        return None, "empty"
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return Path(value).expanduser().resolve(), None
    parsed = urlparse(value)
    if parsed.scheme == "file":
        return None, "file_url"
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        return None, "not_local"
    if "\\" in value:
        return None, "backslash_path"
    path_part = unquote(parsed.path)
    if not path_part:
        return None, "empty"
    return (prototype_dir / path_part).resolve(), None


def safe_rel(path: Path, root: Path) -> str:
    try:
        return relative_to(path, root)
    except ValueError:
        return str(path)


def resolve_excalidraw_ref(demand: Path, rel: str) -> tuple[Path | None, str]:
    normalized = unquote(str(rel or "")).replace("\\", "/")
    if not normalized.endswith(".excalidraw"):
        return None, normalized
    target = (demand / normalized).resolve()
    for allowed in ((demand / EXCAL_DIR / SCENES_DIR).resolve(), (demand / EXCAL_DIR / BOARDS_DIR).resolve()):
        try:
            target.relative_to(allowed)
            return target, normalized
        except ValueError:
            continue
    return None, normalized


def paths(demand: Path) -> dict[str, Path]:
    excal = demand / EXCAL_DIR
    return {
        "demand": demand,
        "plan": demand / PLAN_FILENAME,
        "manifest": excal / MANIFEST_FILENAME,
        "excal": excal,
        "scenes": excal / SCENES_DIR,
        "boards": excal / BOARDS_DIR,
        "snapshots": excal / SNAPSHOTS_DIR,
        "fragment": demand / FRAGMENT_FILENAME,
        "index": demand / "index.html",
    }


def design_root_for(demand: Path, prd: Path | None = None) -> Path:
    demand = demand.resolve()
    candidates = [demand / "Design", demand.parent / "Design"]
    if prd:
        prd = prd.resolve()
        candidates.extend([prd.parent / "Design", prd.parent.parent / "Design"])
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[1]


def infer_component_baseline(text: str, platform_hint: str) -> list[str]:
    lowered = text.lower()
    baseline: list[str] = []
    if platform_hint in {"mobile", "mixed"}:
        baseline.extend(["status_bar", "navigation_bar", "content_region", "bottom_action_or_tab"])
    if platform_hint in {"web", "mixed"}:
        baseline.extend(["top_bar", "side_nav_or_toolbar", "content_cards", "table_or_form_region"])
    term_map = {
        "列表": "list_rows",
        "表格": "table_rows",
        "卡片": "cards",
        "弹窗": "modal_overlay",
        "确认": "modal_overlay",
        "设置": "settings_rows",
        "图表": "chart_or_metric_cards",
        "地图": "map_or_location_block",
        "消息": "message_list",
        "聊天": "chat_bubbles",
        "会话": "conversation_list",
        "筛选": "filter_bar",
        "搜索": "search_bar",
        "通知": "notification_rows",
        "权限": "permission_state",
        "空态": "empty_state",
        "错误": "error_state",
        "loading": "loading_state",
    }
    for term, component in term_map.items():
        if term.lower() in lowered:
            baseline.append(component)
    return unique_preserve(baseline or ["navigation", "primary_content", "primary_action"], 12)


def collect_design_hints(demand: Path, prd: Path | None = None) -> dict[str, object]:
    root = design_root_for(demand, prd)
    design_md = root / "design.md"
    references_dir = root / "references"
    reference_files: list[Path] = []
    if references_dir.is_dir():
        reference_files = sorted(
            path
            for path in references_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
        )
    text = read_text(design_md) if design_md.is_file() else ""
    sample = clean_snippet(text[:2400], 1800) if text else ""
    combined = f"{root} {sample}".lower()
    mobile = contains_any(combined, {"mobile", "app", "ios", "android", "手机", "移动", "客户端", "p端", "k端"})
    web = contains_any(combined, {"web", "后台", "admin", "dashboard", "桌面", "管理台"})
    nav_terms = [term for term in ["首页", "设备", "位置", "消息", "设置", "我的", "聊天", "会话", "工作台", "个人中心", "历史", "通知", "报告", "详情"] if term in text]
    platform_hint = "mobile" if mobile and not web else "mixed" if mobile and web else "web" if web else ""
    component_baseline = infer_component_baseline(sample, platform_hint)
    return {
        "available": bool(design_md.is_file() or reference_files),
        "root": str(root) if root.is_dir() else "",
        "design_md": str(design_md) if design_md.is_file() else "",
        "references": [str(path) for path in reference_files[:20]],
        "reference_count": len(reference_files),
        "reference_samples": [str(path) for path in reference_files[:6]],
        "summary": sample,
        "context_policy": "available_design_must_be_read_before_storyboard_authoring" if design_md.is_file() or reference_files else "no_design_context_found",
        "platform_hint": platform_hint,
        "navigation_terms": unique_preserve(nav_terms, 8),
        "component_baseline": component_baseline,
    }


def read_prd_title(prd: Path) -> str:
    for line in read_text(prd).splitlines():
        text = line.strip().lstrip("\ufeff").strip()
        match = re.match(r"^#\s*(.+?)\s*$", text)
        if match:
            return strip_markdown(match.group(1)) or prd.stem
    return prd.stem


def strip_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*]\([^)]+\)", "", value)
    value = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_`#>]+", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -：:|")


def contains_any(value: str, terms: set[str]) -> bool:
    lowered = value.lower()
    return any(term.lower() in lowered for term in terms)


def extract_markdown_sections(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    headings: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,4})\s+(.+?)\s*$", line)
        if match:
            headings.append({"level": len(match.group(1)), "title": strip_markdown(match.group(2)), "line": index})
    stack: list[dict[str, object]] = []
    sections: list[dict[str, object]] = []
    for index, heading in enumerate(headings):
        level = int(heading["level"])
        while stack and int(stack[-1]["level"]) >= level:
            stack.pop()
        stack.append(heading)
        next_line = int(headings[index + 1]["line"]) if index + 1 < len(headings) else len(lines)
        body = "\n".join(lines[int(heading["line"]) + 1 : next_line]).strip()
        path = [str(item["title"]) for item in stack]
        sections.append({"level": level, "title": str(heading["title"]), "path": path, "body": body})
    for section in sections:
        path = section.get("path", [])
        section["has_children"] = any(
            other is not section
            and isinstance(other.get("path"), list)
            and len(other["path"]) > len(path)
            and other["path"][: len(path)] == path
            for other in sections
        )
    return sections


def clean_snippet(value: str, max_len: int = 72) -> str:
    value = strip_markdown(value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" -：:|")
    if len(value) > max_len:
        return value[: max_len - 1].rstrip() + "…"
    return value


def sentence_candidates(body: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in body.splitlines():
        line = clean_snippet(raw_line)
        if not line or set(line) <= {"-", "|", " "}:
            continue
        if len(line) < 3:
            continue
        for chunk in re.split(r"[。；;.!?？]", line):
            snippet = clean_snippet(chunk)
            if 3 <= len(snippet) <= 96:
                candidates.append(snippet)
    return candidates


def unique_preserve(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = clean_snippet(value)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
        if len(result) >= limit:
            break
    return result


NON_PRODUCT_TEXT_TERMS = {
    "<iframe",
    "iframe",
    "frameborder",
    "width=",
    "height=",
    "src=",
    "http://",
    "https://",
    "axure",
    "todo",
    "TODO",
    "id=",
}


PLACEHOLDER_TEXT_TERMS = {"—", "-", "›", "区域", "内容", "说明用途", "待补充"}


def is_non_product_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if any(term.lower() in lowered for term in NON_PRODUCT_TEXT_TERMS):
        return True
    if re.search(r"<[^>]+>", text):
        return True
    if text in PLACEHOLDER_TEXT_TERMS:
        return True
    return False


def product_text_candidates(values: list[object], limit: int, *, max_len: int = 72) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, list):
            result.extend(product_text_candidates(value, limit - len(result), max_len=max_len))
        elif isinstance(value, dict):
            continue
        else:
            text = clean_snippet(str(value or ""), max_len)
            if text and not is_non_product_text(text):
                result.append(text)
        if len(result) >= limit:
            break
    return unique_preserve(result, limit)


def text_contains_any(value: str, terms: list[str] | set[str]) -> bool:
    lowered = str(value or "").lower()
    return any(str(term).lower() in lowered for term in terms if term)


def matching_sections(sections: list[dict[str, object]], terms: list[str], limit: int = 4) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for section in sections:
        haystack = f"{section.get('title', '')}\n{section.get('body', '')}"
        if text_contains_any(haystack, terms):
            matches.append(section)
        if len(matches) >= limit:
            break
    return matches


def snippets_for_terms(sections: list[dict[str, object]], terms: list[str], limit: int = 5) -> list[str]:
    snippets: list[str] = []
    for section in matching_sections(sections, terms, limit=6):
        snippets.append(str(section.get("title") or ""))
        snippets.extend(sentence_candidates(str(section.get("body") or "")))
    return product_text_candidates(snippets, limit, max_len=96)


def infer_feature_storyboard_title(prd_title: str, sections: list[dict[str, object]]) -> str:
    corpus = f"{prd_title}\n" + "\n".join(str(section.get("title") or "") for section in sections)
    for term in ["驾驶侦测", "驾驶检测", "会话", "聊天", "工作台", "消息中心"]:
        if term in corpus:
            return f"{term} Storyboard"
    return "Product Storyboard"


def add_surface_spec(
    specs: list[dict[str, object]],
    *,
    title: str,
    terms: list[str],
    sections: list[dict[str, object]],
    archetype: str,
    screen_role: str,
    surface_kind: str,
    visible_copy: list[str],
    component_inventory: list[str],
    data_examples: list[str] | None = None,
    state_variants: list[str] | None = None,
    interaction_jumps: list[str] | None = None,
    annotations: list[str] | None = None,
) -> None:
    evidence = snippets_for_terms(sections, terms, 5)
    if not evidence and not any(text_contains_any(str(section.get("title", "")), terms) for section in sections):
        return
    specs.append(
        {
            "title": title,
            "terms": terms,
            "source_evidence": unique_preserve([*evidence, *visible_copy], 6),
            "surface_archetype": archetype,
            "screen_role": screen_role,
            "surface_kind": surface_kind,
            "scene_type": "overlay" if surface_kind == "overlay" else "mobile_wireframe",
            "visible_copy": product_text_candidates(visible_copy, 12, max_len=72),
            "component_inventory": component_inventory,
            "data_examples": product_text_candidates(data_examples or [], 8, max_len=72),
            "state_variants": product_text_candidates(state_variants or [], 8, max_len=72),
            "interaction_jumps": product_text_candidates(interaction_jumps or [], 8, max_len=72),
            "annotations": product_text_candidates(annotations or evidence, 8, max_len=96),
            "must_not_draw": ["iframe", "TODO", "Axure", "裸链接", "内部生成字段"],
        }
    )


def derive_storyboard_surface_specs(prd_title: str, sections: list[dict[str, object]]) -> list[dict[str, object]]:
    corpus = f"{prd_title}\n" + "\n".join(f"{section.get('title', '')}\n{section.get('body', '')}" for section in sections)
    specs: list[dict[str, object]] = []

    if "驾驶侦测" in corpus or "驾驶检测" in corpus:
        add_surface_spec(
            specs,
            title="设备主页 · 位置与安全",
            terms=["设备主页", "位置与安全", "驾驶侦测", "SOS"],
            sections=sections,
            archetype="device_safety_home",
            screen_role="entry",
            surface_kind="entry_or_flow",
            visible_copy=["孩子的设备", "位置与安全", "驾驶侦测", "定位设置", "SOS 设置", "Android K 无「定位设置」"],
            component_inventory=["phone_shell", "section_card", "entry_rows"],
            interaction_jumps=["点击「驾驶侦测」进入未开启引导或报告主页"],
        )
        add_surface_spec(
            specs,
            title="定位页 · 驾驶侦测入口",
            terms=["定位页", "驾驶侦测入口", "地图区域"],
            sections=sections,
            archetype="location_entry",
            screen_role="entry",
            surface_kind="entry_or_flow",
            visible_copy=["位置", "[ 地图区域 ]", "驾驶侦测 ›"],
            component_inventory=["phone_shell", "map_area", "bottom_entry_button"],
        )
        add_surface_spec(
            specs,
            title="S1 未开启引导页",
            terms=["未开启引导", "启用驾驶侦测", "启用"],
            sections=sections,
            archetype="onboarding",
            screen_role="onboarding",
            surface_kind="state",
            visible_copy=["驾驶侦测", "记录驾驶行为，识别风险并提醒", "自动记录每一次出行轨迹与时长", "精准捕捉超速、急刹、急加速", "发现风险立即推送到你的手机", "启用"],
            component_inventory=["phone_shell", "hero_illustration", "bullet_list", "primary_button"],
            interaction_jumps=["点启用后总开关默认开，并自动进入驾驶侦测主页"],
        )
        add_surface_spec(
            specs,
            title="S3 报告主页 · 有数据",
            terms=["报告主页", "有数据", "Trips", "四宫格", "柱状图"],
            sections=sections,
            archetype="driving_dashboard_data",
            screen_role="home_state",
            surface_kind="page",
            visible_copy=["驾驶侦测", "‹ 本周 ›", "47 公里 · 最高时速 86 公里/小时", "驾驶次数", "超速", "急加速", "急刹车", "Trips", "96km/h", "2 个风险事件 ›"],
            component_inventory=["phone_shell", "period_switcher", "metric_grid", "bar_chart", "trip_card"],
            data_examples=["47 公里", "86 公里/小时", "96km/h", "2 个风险事件"],
        )
        add_surface_spec(
            specs,
            title="S4 报告主页 · 空数据",
            terms=["空数据", "暂无数据", "S4"],
            sections=sections,
            archetype="driving_dashboard_empty",
            screen_role="empty_state",
            surface_kind="state",
            visible_copy=["驾驶侦测", "‹ 本周 ›", "暂无数据"],
            component_inventory=["phone_shell", "period_switcher", "empty_illustration"],
        )
        add_surface_spec(
            specs,
            title="S2-b 订阅已过期",
            terms=["已过期", "订阅", "暂停", "S2-b"],
            sections=sections,
            archetype="subscription_expired",
            screen_role="expired_state",
            surface_kind="state",
            visible_copy=["驾驶侦测", "此功能已暂停，订阅后可恢复运行 ›", "下方只读展示 S3 或 S4", "驾驶次数", "超速", "急加速", "急刹车"],
            component_inventory=["phone_shell", "warning_banner", "readonly_metrics"],
        )
        add_surface_spec(
            specs,
            title="单次行程详情",
            terms=["单次行程详情", "轨迹", "事件锚点", "最快速度"],
            sections=sections,
            archetype="trip_detail",
            screen_role="detail",
            surface_kind="detail",
            visible_copy=["行程详情", "[ 轨迹 + 事件锚点 ]", "孩子", "○ 家", "▽ 学校", "08:30 - 09:15 · 12 公里", "最快速度\n96 km/h", "超速\n1 次", "急刹车\n0 次", "急加速\n1 次"],
            component_inventory=["phone_shell", "map_area", "address_timeline", "metric_grid"],
            data_examples=["08:30", "09:15", "12 公里", "96 km/h"],
        )
        add_surface_spec(
            specs,
            title="驾驶检测设置",
            terms=["驾驶检测设置", "驾驶侦测设置", "超速阈值", "单位"],
            sections=sections,
            archetype="driving_settings",
            screen_role="settings",
            surface_kind="settings",
            visible_copy=["驾驶检测设置", "基础设置", "启用驾驶侦测", "[ON]", "超速阈值", "80 km/h ›", "单位", "km/h ›", "通知：消息中心 → 消息通知设置 → 驾驶侦测"],
            component_inventory=["phone_shell", "settings_rows", "switch", "value_rows"],
        )
        add_surface_spec(
            specs,
            title="关闭二次确认弹窗",
            terms=["关闭驾驶侦测", "二次确认", "取消", "确定"],
            sections=sections,
            archetype="close_confirm_modal",
            screen_role="overlay",
            surface_kind="overlay",
            visible_copy=["驾驶检测设置", "关闭驾驶侦测", "关闭后将停止记录新的驾驶行为，重新开启后可继续使用。", "取消", "确定"],
            component_inventory=["phone_shell", "modal_card", "secondary_action", "primary_action"],
        )
        add_surface_spec(
            specs,
            title="消息中心 · 警报 Tab",
            terms=["消息中心", "警报", "告警", "车速超过"],
            sections=sections,
            archetype="alert_center",
            screen_role="list",
            surface_kind="list",
            visible_copy=["消息中心", "提醒", "请求", "警报", "孩子车速超过 80 km/h（当前 96 km/h）", "请注意驾驶安全", "今天 14:32", "孩子本次行程检测到急刹车 4 次", "昨天 18:05"],
            component_inventory=["phone_shell", "segmented_tabs", "alert_cards"],
        )
        add_surface_spec(
            specs,
            title="消息通知设置 · 驾驶侦测",
            terms=["消息通知设置", "系统 Push", "统一控制"],
            sections=sections,
            archetype="notification_settings",
            screen_role="settings",
            surface_kind="settings",
            visible_copy=["消息通知设置", "驾驶侦测", "[ON]", "统一控制超速实时 Push 与行程结束聚合 Push"],
            component_inventory=["phone_shell", "settings_row", "switch", "helper_text"],
        )

    if not specs:
        generic_patterns = [
            ("会话列表", ["会话列表", "聊天历史", "历史会话"], "chat_list", "list", ["会话列表", "搜索", "未读", "最近会话"]),
            ("个人会话", ["个人会话", "聊天", "输入框"], "chat_session", "page", ["个人会话", "今天", "输入消息", "发送"]),
            ("协作工作台", ["协作工作台", "工作台"], "workspace", "page", ["协作工作台", "任务", "成员", "最近更新"]),
            ("会话抽屉", ["抽屉", "侧边栏"], "drawer", "overlay", ["会话抽屉", "历史", "新建会话", "关闭"]),
            ("个人中心", ["个人中心", "我的", "设置"], "profile_settings", "settings", ["个人中心", "账号", "通知设置", "退出登录"]),
            ("登录与认证", ["登录", "认证", "账号"], "login", "page", ["登录", "账号", "密码", "继续"]),
        ]
        for title, terms, archetype, surface_kind, copy in generic_patterns:
            add_surface_spec(
                specs,
                title=title,
                terms=terms,
                sections=sections,
                archetype=archetype,
                screen_role=surface_kind,
                surface_kind=surface_kind,
                visible_copy=copy,
                component_inventory=["phone_shell", "navigation", surface_kind],
            )

    return specs


def classify_prd_section(section: dict[str, object], prd_title: str) -> dict[str, str]:
    title = str(section.get("title") or "")
    body = str(section.get("body") or "")
    path = [str(item) for item in section.get("path", []) if item]
    path_text = " ".join(path)
    combined = f"{prd_title} {path_text} {body[:500]}"
    title_text = title.lower()
    ancestor_text = " ".join(path[:-1]).lower()
    surface_verbs = {"点击", "进入", "展示", "显示", "跳转", "选择", "输入", "弹出", "打开", "关闭", "保存", "提交", "删除", "筛选", "搜索", "切换", "查看"}
    has_surface_action = contains_any(body[:900], surface_verbs)
    has_explicit_surface = contains_any(title_text, EXPLICIT_PROTOTYPE_TITLE_TERMS)
    if contains_any(title_text, DELIVERY_NOTE_TERMS):
        return {"disposition": "delivery_note", "reason": "section describes delivery, publishing, or SOP material"}
    if contains_any(title_text, ALWAYS_SPEC_ONLY_TITLE_TERMS):
        return {"disposition": "annotation", "reason": "section is detailed UI/spec text to attach to a nearby frame, not an independent frame"}
    if contains_any(ancestor_text, {"核心概念定义", "概念定义", "术语定义"}):
        return {"disposition": "documentation_only", "reason": "section belongs to concept or terminology definition context"}
    if contains_any(title_text, SPEC_ONLY_TITLE_TERMS) and not (has_explicit_surface and has_surface_action):
        return {"disposition": "annotation", "reason": "section is specification or rule detail to carry as scene evidence, not an independent scene"}
    if section.get("has_children") and not contains_any(title_text, GROUP_TITLE_SCENE_TERMS):
        return {"disposition": "prd_viewer", "reason": "section is a grouping/module overview with child sections"}
    if contains_any(title_text, HARD_DOCUMENTATION_TERMS) and not contains_any(title_text, EXPLICIT_PROTOTYPE_TITLE_TERMS):
        return {"disposition": "documentation_only", "reason": "section is documentation context, not a prototype surface"}
    if has_explicit_surface:
        return {"disposition": "prototype_step", "reason": "section title names a user-visible surface, interaction, state, overlay, or branch"}
    if contains_any(combined, PROTOTYPE_TERMS) and has_surface_action:
        return {"disposition": "prototype_step", "reason": "section describes a user-visible surface, state, flow, overlay, or rule branch"}
    if contains_any(title_text, ANNOTATION_TERMS) and len(title) <= 42:
        return {"disposition": "annotation", "reason": "section is short explanatory context that can be carried by nearby scene notes"}
    return {"disposition": "prd_viewer", "reason": "section is explanatory PRD material and should remain in the PRD viewer"}


def infer_scene_type(section: dict[str, object], prd_title: str) -> tuple[str, str]:
    title = str(section.get("title") or "")
    body = str(section.get("body") or "")
    title_text = title.lower()
    text = f"{prd_title} {' '.join(str(item) for item in section.get('path', []))} {body[:700]}".lower()
    mobile_context = contains_any(text, {"移动", "app", "手机", "客户端", "推送"})
    if contains_any(title_text, {"弹窗", "浮层", "抽屉", "toast", "sheet", "确认", "提示框"}):
        return "overlay", "section describes an overlay, dialog, sheet, toast, or confirmation surface"
    if contains_any(title_text, {"列表", "表格", "筛选", "搜索", "批量", "历史", "会话列表"}):
        return "mobile_wireframe" if mobile_context else "list_table", "section title describes list, table, filtering, or management operations"
    if contains_any(title_text, {"页面", "界面", "主页", "首页", "详情页", "内容页", "个人中心", "tab", "布局", "组件"}):
        return "mobile_wireframe" if mobile_context else "web_wireframe", "section title describes a product page or primary surface"
    if contains_any(title_text, {"状态", "空态", "错误", "加载", "失败", "成功", "过期", "无数据", "异常"}):
        return "state_matrix", "section compares important states or exception outcomes"
    if contains_any(title_text, {"流程", "路径", "机制", "跳转", "下线", "升级", "删除", "转群", "入口"}):
        return "flow", "section title describes an end-to-end path or interaction sequence"
    if contains_any(title_text, {"权限", "条件", "分支", "规则", "限制", "认证", "登录", "免费版", "判断", "角色"}):
        return "decision_branch", "section contains permission, condition, or rule branching"
    if contains_any(text, {"弹窗", "浮层", "抽屉", "toast", "sheet", "确认", "提示框"}):
        return "overlay", "section describes an overlay, dialog, sheet, toast, or confirmation surface"
    if contains_any(text, {"状态", "空态", "错误", "加载", "失败", "成功", "过期", "无数据", "异常"}):
        return "state_matrix", "section compares important states or exception outcomes"
    if contains_any(text, {"列表", "表格", "筛选", "搜索", "批量", "成员管理", "历史"}):
        return "mobile_wireframe" if mobile_context else "list_table", "section describes list, table, filtering, or management operations"
    if contains_any(text, {"流程", "路径", "机制", "跳转", "下线", "升级", "删除", "转群", "入口"}):
        return "flow", "section describes an end-to-end path or interaction sequence"
    if contains_any(text, {"页面", "界面", "主页", "首页", "详情页", "内容页", "个人中心", "tab"}):
        return "mobile_wireframe" if mobile_context else "web_wireframe", "section describes a product page or primary surface"
    if contains_any(text, {"权限", "条件", "分支", "规则", "限制", "认证", "登录", "免费版", "判断", "角色"}):
        return "decision_branch", "section contains permission, condition, or rule branching"
    return "flow", "section is prototype-relevant but has no more specific scene type signal"


def extract_business_entities(section: dict[str, object]) -> list[str]:
    title = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", str(section.get("title") or ""))
    pieces = re.split(r"[\s/()（）:：,，\-—]+", strip_markdown(title))
    stop = {"功能", "说明", "详细", "规格", "机制", "流程", "页面", "界面", "处理", "规则"}
    return unique_preserve([piece for piece in pieces if len(piece) >= 2 and piece.lower() not in stop], 5)


def extract_source_evidence(section: dict[str, object]) -> list[str]:
    path = [str(item) for item in section.get("path", []) if item]
    candidates = [path[-1]] if path else []
    if len(path) >= 2:
        candidates.append(path[-2])
    candidates.extend(sentence_candidates(str(section.get("body") or "")))
    return product_text_candidates(candidates, 5)


def extract_states_or_rules(section: dict[str, object]) -> list[str]:
    keywords = ("状态", "空态", "错误", "加载", "失败", "成功", "权限", "规则", "条件", "限制", "异常", "过期", "无数据")
    candidates = [snippet for snippet in sentence_candidates(str(section.get("body") or "")) if any(key in snippet for key in keywords)]
    return unique_preserve(candidates, 4)


def infer_screen_kind(title: str, scene_type: str, design_hints: dict[str, object]) -> str:
    text = title.lower()
    platform = str(design_hints.get("platform_hint") or "")
    if contains_any(text, {"弹窗", "确认", "提示", "modal", "dialog"}):
        return "modal"
    if contains_any(text, {"设置", "配置", "通知设置"}):
        return "settings"
    if contains_any(text, {"消息", "通知", "警报", "历史", "列表"}):
        return "list"
    if contains_any(text, {"详情", "报告", "主页", "首页", "tab", "个人中心", "会话", "聊天", "工作台"}):
        return "mobile" if platform in {"mobile", "mixed"} or scene_type == "mobile_wireframe" else "web"
    if scene_type in {"overlay"}:
        return "modal"
    if scene_type in {"list_table"}:
        return "list"
    if scene_type in {"mobile_wireframe"} or platform in {"mobile", "mixed"}:
        return "mobile"
    if scene_type in {"web_wireframe"}:
        return "web"
    return "flow_note"


def primary_regions_for(screen_kind: str, step: dict[str, object]) -> list[str]:
    title = str(step.get("title") or "")
    if screen_kind == "modal":
        return ["遮罩层", "弹窗标题", "说明文案", "取消/确认操作"]
    if screen_kind == "settings":
        return ["导航栏", "设置分组", "开关/阈值", "说明文案"]
    if screen_kind == "list":
        return ["导航栏", "筛选/分段", "列表卡片", "状态/操作"]
    if "详情" in title:
        return ["导航栏", "主内容区", "关键指标", "详情列表"]
    if screen_kind == "web":
        return ["顶部栏", "侧边导航", "内容卡片", "数据区"]
    if screen_kind == "flow_note":
        return ["规则标题", "关键条件", "结果状态", "关联界面"]
    return ["状态栏", "导航栏", "内容区", "底部操作"]


def key_copy_for(step: dict[str, object]) -> list[str]:
    brief = step.get("storyboard_brief") if isinstance(step.get("storyboard_brief"), dict) else {}
    semantic = step.get("semantic_frame_spec") if isinstance(step.get("semantic_frame_spec"), dict) else {}
    semantic_brief = semantic.get("storyboard_brief") if isinstance(semantic.get("storyboard_brief"), dict) else {}
    values: list[object] = []
    values.extend(brief.get("visible_copy", []) if isinstance(brief, dict) else [])
    values.extend(semantic_brief.get("visible_copy", []) if isinstance(semantic_brief, dict) else [])
    existing = step.get("key_copy")
    if isinstance(existing, list):
        values.extend(existing)
    values.extend(step_text_items(step, 8))
    return [item for item in product_text_candidates(values, 8) if "section " not in item.lower() and item not in {"Yes", "No"}][:6]


def infer_platform_for_step(title: str, section: dict[str, object], scene_type: str, design_hints: dict[str, object]) -> str:
    text = f"{title} {' '.join(str(item) for item in section.get('path', []))} {str(section.get('body') or '')[:900]}".lower()
    design_platform = str(design_hints.get("platform_hint") or "")
    if contains_any(text, {"后台", "管理台", "web", "dashboard", "桌面", "admin", "表格", "批量"}):
        return "web"
    if contains_any(text, {"移动", "手机", "app", "ios", "android", "客户端", "推送", "底部 tab"}):
        return "mobile"
    if design_platform in {"mobile", "web"}:
        return design_platform
    if design_platform == "mixed":
        return "mobile" if scene_type in {"mobile_wireframe", "overlay", "state_matrix"} else "web"
    if scene_type == "web_wireframe":
        return "web"
    return "mobile" if scene_type == "mobile_wireframe" else "web"


def infer_surface_kind(title: str, scene_type: str, screen_kind: str) -> str:
    text = title.lower()
    if contains_any(text, {"弹窗", "浮层", "抽屉", "toast", "sheet", "确认", "提示框", "modal", "dialog"}):
        return "overlay"
    if contains_any(text, {"设置", "配置", "通知设置", "偏好"}):
        return "settings"
    if contains_any(text, {"详情", "报告", "明细", "行程"}):
        return "detail"
    if contains_any(text, {"列表", "表格", "历史", "消息", "通知", "会话", "成员"}):
        return "list"
    if contains_any(text, {"空态", "无数据", "错误", "失败", "成功", "过期", "加载", "状态"}):
        return "state"
    if contains_any(text, {"流程", "路径", "入口", "引导"}):
        return "entry_or_flow"
    if screen_kind in {"modal", "settings", "list"}:
        return screen_kind
    if scene_type in {"overlay"}:
        return "overlay"
    if scene_type in {"state_matrix"}:
        return "state"
    if scene_type in {"list_table"}:
        return "list"
    return "page"


def component_baseline_for_step(step: dict[str, object], design_hints: dict[str, object]) -> list[str]:
    values: list[str] = []
    platform = str(step.get("platform") or "")
    surface_kind = str(step.get("surface_kind") or "")
    if platform == "mobile":
        values.extend(["status_bar", "navigation_bar", "screen_body"])
    else:
        values.extend(["top_bar", "navigation_or_toolbar", "content_panel"])
    if surface_kind == "overlay":
        values.extend(["base_surface_clone", "scrim", "modal_card", "secondary_and_primary_actions"])
    elif surface_kind == "settings":
        values.extend(["settings_rows", "switch_or_value", "helper_text"])
    elif surface_kind == "list":
        values.extend(["search_or_filter", "list_rows", "row_actions"])
    elif surface_kind == "detail":
        values.extend(["hero_or_summary", "detail_rows", "metric_cards"])
    elif surface_kind == "state":
        values.extend(["state_illustration", "state_copy", "state_action"])
    values.extend(str(item) for item in design_hints.get("component_baseline", []) if item)
    return unique_preserve(values, 12)


def make_context_summary(prd_title: str, sections: list[dict[str, object]], design_hints: dict[str, object]) -> dict[str, object]:
    section_titles = [str(section.get("title") or "") for section in sections]
    return {
        "prd_title": prd_title,
        "prd_section_count": len(section_titles),
        "design_context_status": "available_and_indexed" if design_hints.get("available") else "not_found",
        "design_md": design_hints.get("design_md", ""),
        "reference_count": design_hints.get("reference_count", 0),
        "reference_samples": design_hints.get("reference_samples", []),
        "platform_hint": design_hints.get("platform_hint", ""),
        "navigation_terms": design_hints.get("navigation_terms", []),
        "component_baseline": design_hints.get("component_baseline", []),
        "section_sample": unique_preserve(section_titles, 12),
    }


def make_disposition_record(section: dict[str, object], classification: dict[str, str]) -> dict[str, object]:
    path = [str(item) for item in section.get("path", []) if item]
    return {
        "prd_section": str(section.get("title") or ""),
        "section_path": path,
        "group_title": path[-2] if len(path) >= 2 else "",
        "disposition": classification["disposition"],
        "reason": classification["reason"],
        "decision_source": "auto_section_disposition_v2",
    }


def infer_surface_archetype(title: str, surface_kind: str, scene_type: str) -> str:
    title_text = title.lower()
    if contains_any(title, {"设备主页", "位置与安全"}):
        return "device_safety_home"
    if contains_any(title, {"定位页", "地图"}):
        return "location_entry"
    if contains_any(title, {"未开启", "引导"}):
        return "onboarding"
    if contains_any(title, {"空数据", "暂无数据"}):
        return "driving_dashboard_empty"
    if contains_any(title, {"过期", "订阅"}):
        return "subscription_expired"
    if contains_any(title, {"报告主页", "驾驶侦测主页", "主页"}):
        return "driving_dashboard_data"
    if contains_any(title, {"行程详情", "单次行程"}):
        return "trip_detail"
    if contains_any(title, {"驾驶检测设置", "驾驶侦测设置", "通知设置", "设置"}):
        return "notification_settings" if "通知" in title else "driving_settings"
    if contains_any(title, {"二次确认", "关闭", "弹窗"}):
        return "close_confirm_modal"
    if contains_any(title, {"消息中心", "警报", "告警"}):
        return "alert_center"
    if contains_any(title, {"会话列表", "聊天历史"}):
        return "chat_list"
    if contains_any(title, {"个人会话", "聊天"}):
        return "chat_session"
    if contains_any(title, {"工作台"}):
        return "workspace"
    if contains_any(title, {"抽屉"}):
        return "drawer"
    if contains_any(title, {"个人中心", "我的"}):
        return "profile_settings"
    if contains_any(title, {"登录", "认证"}):
        return "login"
    if surface_kind == "overlay":
        return "modal"
    if surface_kind == "settings":
        return "settings"
    if surface_kind == "list":
        return "list"
    if surface_kind == "detail":
        return "detail"
    if surface_kind == "state":
        return "state"
    if scene_type in {"flow", "decision_branch", "state_matrix"}:
        return "rule_annotation"
    return "mobile_page"


def storyboard_brief_for_step(step: dict[str, object], design_hints: dict[str, object]) -> dict[str, object]:
    title = str(step.get("title") or "")
    surface_kind = str(step.get("surface_kind") or "page")
    scene_type = str(step.get("scene_type") or "mobile_wireframe")
    archetype = infer_surface_archetype(title, surface_kind, scene_type)
    evidence = product_text_candidates(
        [
            *(step.get("source_evidence", []) if isinstance(step.get("source_evidence"), list) else []),
            *(step.get("business_entities", []) if isinstance(step.get("business_entities"), list) else []),
            *(step.get("states_or_rules", []) if isinstance(step.get("states_or_rules"), list) else []),
            title,
        ],
        8,
    )
    visible_copy = product_text_candidates(evidence, 8)
    if not visible_copy:
        visible_copy = [title]
    component_inventory = component_baseline_for_step(step, design_hints)
    brief = {
        "screen_role": surface_kind,
        "surface_archetype": archetype,
        "layout_regions": step.get("primary_ui_regions", []),
        "component_inventory": component_inventory,
        "visible_copy": visible_copy,
        "data_examples": [item for item in visible_copy if re.search(r"\d|km/h|mph|分钟|公里|次", item)],
        "state_variants": product_text_candidates(step.get("states_or_rules", []) if isinstance(step.get("states_or_rules"), list) else [], 6),
        "interaction_jumps": [],
        "annotations": evidence,
        "design_refs": design_hints.get("reference_samples", []) if isinstance(design_hints, dict) else [],
        "must_not_draw": ["iframe", "TODO", "Axure", "裸链接", "section describes", "scene_type_reason"],
    }
    return brief


def apply_storyboard_brief(step: dict[str, object], brief: dict[str, object], design_hints: dict[str, object]) -> None:
    brief.setdefault("status", "auto_draft")
    step["storyboard_brief"] = brief
    step["storyboard_brief_status"] = str(brief.get("status") or "auto_draft")
    if brief.get("surface_kind"):
        step["surface_kind"] = brief["surface_kind"]
    if brief.get("scene_type"):
        step["scene_type"] = brief["scene_type"]
    if brief.get("visible_copy"):
        step["key_copy"] = product_text_candidates(list(brief.get("visible_copy", [])), 12)
    if brief.get("source_evidence"):
        step["source_evidence"] = product_text_candidates(list(brief.get("source_evidence", [])), 6)
    step["screen_role"] = brief.get("screen_role", step.get("surface_kind", "page"))
    step["surface_archetype"] = brief.get("surface_archetype", infer_surface_archetype(str(step.get("title", "")), str(step.get("surface_kind", "")), str(step.get("scene_type", ""))))
    step["component_baseline"] = product_text_candidates(list(brief.get("component_inventory", [])), 14) or component_baseline_for_step(step, design_hints)
    semantic = step.get("semantic_frame_spec") if isinstance(step.get("semantic_frame_spec"), dict) else {}
    semantic.update(
        {
            "surface_kind": step.get("surface_kind", ""),
            "key_copy": step.get("key_copy", []),
            "component_baseline": step.get("component_baseline", []),
            "storyboard_brief": brief,
        }
    )
    step["semantic_frame_spec"] = semantic


def make_plan_step(step_id: str, title: str, group_id: str, sections: list[str], section: dict[str, object], prd_title: str, design_hints: dict[str, object] | None = None) -> dict[str, object]:
    scene_type, scene_reason = infer_scene_type(section, prd_title)
    evidence = extract_source_evidence(section)
    entities = extract_business_entities(section)
    design_hints = design_hints or {}
    platform = infer_platform_for_step(title, section, scene_type, design_hints)
    screen_kind = infer_screen_kind(title, scene_type, design_hints)
    surface_kind = infer_surface_kind(title, scene_type, screen_kind)
    surface_id = stable_id("surface", " ".join(sections[-2:] or [title]), "surface")
    state_id = stable_id("state", title, "state") if surface_kind == "state" else ""
    step: dict[str, object] = {
        "id": step_id,
        "title": title,
        "group_id": group_id,
        "kind": "prototype_step",
        "platform": platform,
        "prd_sections": sections,
        "scene_type": scene_type,
        "scene_type_reason": scene_reason,
        "source_evidence": evidence,
        "business_entities": entities,
        "interaction_goal": f"把「{title}」表达成可讨论、可编辑的草图",
        "states_or_rules": extract_states_or_rules(section),
        "state": "planned",
        "rendered": False,
        "notes": "Prototype content lives in the Excalidraw scene.",
    }
    step["screen_kind"] = screen_kind
    step["surface_id"] = surface_id
    step["surface_kind"] = surface_kind
    step["state_id"] = state_id
    step["base_surface_id"] = ""
    step["frame_intent"] = f"呈现「{title}」这一真实产品界面/状态，便于围绕 PRD 证据讨论。"
    step["screen_purpose"] = str(step["interaction_goal"])
    step["primary_ui_regions"] = primary_regions_for(screen_kind, step)
    step["key_copy"] = key_copy_for(step)
    step["state_data"] = step.get("states_or_rules", [])
    step["linked_steps"] = []
    step["annotation_refs"] = []
    step["design_hints"] = {
        "platform_hint": design_hints.get("platform_hint", ""),
        "navigation_terms": design_hints.get("navigation_terms", []),
        "reference_count": design_hints.get("reference_count", 0),
        "component_baseline": design_hints.get("component_baseline", []),
    }
    step["component_baseline"] = component_baseline_for_step(step, design_hints)
    step["semantic_frame_spec"] = {
        "platform": platform,
        "surface_kind": surface_kind,
        "frame_intent": step["frame_intent"],
        "primary_ui_regions": step["primary_ui_regions"],
        "key_copy": step["key_copy"],
        "state_data": step["state_data"],
        "component_baseline": step["component_baseline"],
        "source_evidence": evidence,
        "design_hints": step["design_hints"],
    }
    apply_storyboard_brief(step, storyboard_brief_for_step(step, design_hints), design_hints)
    return step


def make_storyboard_steps_from_specs(prd_title: str, sections: list[dict[str, object]], specs: list[dict[str, object]], design_hints: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    storyboard_title = infer_feature_storyboard_title(prd_title, sections)
    group_order: list[str] = []
    group_by_id: dict[str, dict[str, object]] = {}
    steps: list[dict[str, object]] = []
    for order, spec in enumerate(specs, 1):
        title = str(spec.get("title") or f"Frame {order}")
        body = "\n".join(str(item) for item in spec.get("source_evidence", []) if item)
        group_title = storyboard_display_group_for_spec(spec)
        group_id = stable_id("group", f"{storyboard_title} {group_title}", "storyboard-group")
        if group_id not in group_by_id:
            group_by_id[group_id] = {"id": group_id, "title": group_title, "description": "Derived product storyboard frames", "step_ids": []}
            group_order.append(group_id)
        section = {"title": title, "path": [group_title, title], "body": body}
        step_id = stable_id("step", f"{storyboard_title} {group_title} {title}", f"frame-{order}")
        step = make_plan_step(step_id, title, group_id, [group_title, title], section, prd_title, design_hints)
        brief = {
            "screen_role": spec.get("screen_role", spec.get("surface_kind", "page")),
            "surface_archetype": spec.get("surface_archetype", infer_surface_archetype(title, str(spec.get("surface_kind", "")), str(spec.get("scene_type", "")))),
            "layout_regions": spec.get("layout_regions", step.get("primary_ui_regions", [])),
            "component_inventory": spec.get("component_inventory", step.get("component_baseline", [])),
            "visible_copy": spec.get("visible_copy", step.get("key_copy", [])),
            "data_examples": spec.get("data_examples", []),
            "state_variants": spec.get("state_variants", []),
            "interaction_jumps": spec.get("interaction_jumps", []),
            "annotations": spec.get("annotations", spec.get("source_evidence", [])),
            "design_refs": design_hints.get("reference_samples", []),
            "must_not_draw": spec.get("must_not_draw", ["iframe", "TODO", "Axure", "裸链接"]),
            "source_evidence": spec.get("source_evidence", []),
            "surface_kind": spec.get("surface_kind", step.get("surface_kind", "page")),
            "scene_type": spec.get("scene_type", step.get("scene_type", "mobile_wireframe")),
        }
        step["platform"] = "mobile"
        step["surface_kind"] = str(brief.get("surface_kind") or step.get("surface_kind") or "page")
        step["scene_type"] = str(brief.get("scene_type") or step.get("scene_type") or "mobile_wireframe")
        step["screen_kind"] = "modal" if step["surface_kind"] == "overlay" else "settings" if step["surface_kind"] == "settings" else "list" if step["surface_kind"] == "list" else "mobile"
        step["scene_type_reason"] = f"storyboard brief maps PRD/design evidence to a {brief.get('surface_archetype')} product frame"
        step["frame_intent"] = f"呈现「{title}」这一产品旅程画面，规则作为可见状态、数据或注释承载。"
        step["screen_purpose"] = step["frame_intent"]
        apply_storyboard_brief(step, brief, design_hints)
        group_by_id[group_id]["step_ids"].append(str(step["id"]))
        steps.append(step)
    groups = [group_by_id[group_id] for group_id in group_order if group_by_id[group_id].get("step_ids")]
    return groups, steps


def storyboard_display_group_for_spec(spec: dict[str, object]) -> str:
    title = str(spec.get("title") or "")
    surface_kind = str(spec.get("surface_kind") or "")
    screen_role = str(spec.get("screen_role") or "")
    archetype = str(spec.get("surface_archetype") or "")
    text = f"{title} {surface_kind} {screen_role} {archetype}"
    if contains_any(text, {"消息", "通知", "警报", "告警"}):
        return "消息与通知"
    if contains_any(text, {"设置", "关闭", "确认", "弹窗", "modal", "overlay"}):
        return "设置与关闭"
    if contains_any(text, {"报告", "行程", "trip", "dashboard", "数据", "过期", "订阅"}):
        return "报告与行程"
    if contains_any(text, {"入口", "启用", "开启", "引导", "entry", "onboarding"}):
        return "入口与启用"
    if surface_kind in {"settings", "overlay"}:
        return "设置与关闭"
    if surface_kind in {"list"}:
        return "消息与通知"
    if surface_kind in {"detail", "page", "state"}:
        return "报告与行程"
    return "核心界面"


def storyboard_boards_for_steps(steps: list[dict[str, object]], design_hints: dict[str, object]) -> list[dict[str, object]]:
    if not steps:
        return []
    by_top: dict[str, list[dict[str, object]]] = {}
    for step in steps:
        sections = step.get("prd_sections") if isinstance(step.get("prd_sections"), list) else []
        top = str(sections[-2] if len(sections) >= 2 else sections[0]) if sections else "Storyboard"
        by_top.setdefault(top, []).append(step)

    board_chunks: list[tuple[str, list[dict[str, object]]]] = []
    singleton_steps: list[dict[str, object]] = []
    for title, group_steps in by_top.items():
        if len(group_steps) == 1:
            singleton_steps.extend(group_steps)
            continue
        if len(group_steps) <= MAX_FRAMES_PER_BOARD:
            board_chunks.append((title, group_steps))
            continue
        for offset in range(0, len(group_steps), MAX_FRAMES_PER_BOARD):
            part = offset // MAX_FRAMES_PER_BOARD + 1
            chunk = group_steps[offset : offset + MAX_FRAMES_PER_BOARD]
            board_chunks.append((f"{title} Part {part}", chunk))
    if singleton_steps:
        singleton_title = "Storyboard" if not board_chunks else "Supporting states"
        for offset in range(0, len(singleton_steps), MAX_FRAMES_PER_BOARD):
            part = offset // MAX_FRAMES_PER_BOARD + 1
            chunk = singleton_steps[offset : offset + MAX_FRAMES_PER_BOARD]
            title = singleton_title if len(singleton_steps) <= MAX_FRAMES_PER_BOARD else f"{singleton_title} Part {part}"
            board_chunks.append((title, chunk))
    boards: list[dict[str, object]] = []
    for index, (title, board_steps) in enumerate(board_chunks, 1):
        board_id = stable_id("board", title, f"storyboard-{index}")
        board_file = f"{EXCAL_DIR}/{BOARDS_DIR}/{board_id}.excalidraw"
        for order, step in enumerate(board_steps, 1):
            frame_id = element_id(str(step["id"]), "frame")
            step["board_id"] = board_id
            step["board_file"] = board_file
            step["frame_id"] = frame_id
            step["frame_name"] = f"{order} · {clean_snippet(str(step.get('title') or step['id']), 34)}"
            step["frame_order"] = order
        boards.append(
            {
                "id": board_id,
                "title": title,
                "kind": "storyboard_board",
                "file": board_file,
                "board_strategy": "semantic_chunked",
                "max_frames_per_board": MAX_FRAMES_PER_BOARD,
                "frame_ids": [str(step["frame_id"]) for step in board_steps],
                "step_ids": [str(step["id"]) for step in board_steps],
                "frame_count": len(board_steps),
                "platforms": unique_preserve([str(step.get("platform") or "") for step in board_steps], 4),
                "surface_kinds": unique_preserve([str(step.get("surface_kind") or "") for step in board_steps], 8),
                "design_hints": {
                    "platform_hint": design_hints.get("platform_hint", ""),
                    "reference_count": design_hints.get("reference_count", 0),
                    "navigation_terms": design_hints.get("navigation_terms", []),
                    "component_baseline": design_hints.get("component_baseline", []),
                },
            }
        )
    return boards


def parse_prd_plan(prd: Path, demand: Path) -> dict[str, object]:
    text = read_text(prd)
    title = read_prd_title(prd)
    design_hints = collect_design_hints(demand, prd)
    sections = extract_markdown_sections(text)
    context_summary = make_context_summary(title, sections, design_hints)
    groups: list[dict[str, object]] = []
    group_by_id: dict[str, dict[str, object]] = {}
    steps: list[dict[str, object]] = []
    dispositions: list[dict[str, object]] = []

    if not sections:
        group_id = stable_id("group", title, "overview")
        step_id = stable_id("step", title, "overview")
        groups.append({"id": group_id, "title": title, "description": "", "step_ids": [step_id]})
        fallback_section = {"title": title, "path": [title], "body": text}
        steps.append(make_plan_step(step_id, title, group_id, [title], fallback_section, title, design_hints))
    else:
        for section in sections:
            if int(section.get("level") or 0) <= 2:
                dispositions.append(make_disposition_record(section, {"disposition": "prd_viewer", "reason": "top-level section acts as grouping context"}))
                continue
            classification = classify_prd_section(section, title)
            if classification["disposition"] != "prototype_step":
                dispositions.append(make_disposition_record(section, classification))
                continue
            path = [str(item) for item in section.get("path", []) if item]
            group_title = path[-2] if len(path) >= 2 else title
            group_id = stable_id("group", group_title, "group")
            group = group_by_id.get(group_id)
            if group is None:
                group = {"id": group_id, "title": group_title, "description": "", "step_ids": []}
                group_by_id[group_id] = group
                groups.append(group)
            step_title = str(section.get("title") or group_title)
            step_id = stable_id("step", " ".join(path[-2:] or [step_title]), "step")
            group["step_ids"].append(step_id)
            steps.append(make_plan_step(step_id, step_title, group_id, path, section, title, design_hints))

    derived_specs = derive_storyboard_surface_specs(title, sections)
    if len(derived_specs) >= 2:
        if steps:
            for old_step in steps:
                dispositions.append(
                    {
                        "prd_section": str(old_step.get("title") or ""),
                        "section_path": old_step.get("prd_sections", []),
                        "group_title": str(old_step.get("group_id") or ""),
                        "disposition": "annotation",
                        "reason": "folded into product storyboard frames as evidence, state, data, or annotation",
                        "decision_source": "auto_storyboard_brief_v1",
                    }
                )
        groups, steps = make_storyboard_steps_from_specs(title, sections, derived_specs, design_hints)
    if not steps:
        group_id = stable_id("group", title, "overview")
        step_id = stable_id("step", title, "overview")
        fallback_section = {"title": title, "path": [title], "body": text}
        groups = [{"id": group_id, "title": title, "description": "", "step_ids": [step_id]}]
        steps = [make_plan_step(step_id, title, group_id, [title], fallback_section, title, design_hints)]

    boards = storyboard_boards_for_steps(steps, design_hints)
    now = utc_now()
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "generation_mode": "excalidraw_storyboard_boards",
        "source": {
            "prd_path": browser_relative_path(prd, demand),
            "demand_dir": str(demand_root_for_prototype(demand)),
            "prototype_dir": str(demand),
            "design_context": design_hints,
        },
        "context_summary": context_summary,
        "groups": groups,
        "boards": boards,
        "frames": [
            {
                "step_id": step.get("id", ""),
                "board_id": step.get("board_id", ""),
                "frame_id": step.get("frame_id", ""),
                "surface_id": step.get("surface_id", ""),
                "surface_kind": step.get("surface_kind", ""),
                "platform": step.get("platform", ""),
                "frame_intent": step.get("frame_intent", ""),
                "source_evidence": step.get("source_evidence", []),
                "design_hints": step.get("design_hints", {}),
                "storyboard_brief": step.get("storyboard_brief", {}),
            }
            for step in steps
        ],
        "steps": steps,
        "coverage": {
            "all_prd_sections": [" / ".join(str(item) for item in section.get("path", []) if item) for section in sections],
            "planned_prd_sections": [section for step in steps for section in step["prd_sections"]],
            "covered_prd_sections": [],
            "disposition": dispositions,
            "omitted": [],
            "notes": "Scene coverage is validated by scene-check.",
        },
        "validation": {"last_scene_check_ok": None, "failures": [], "warnings": []},
        "revision_history": [],
    }


def ordered_steps(plan: dict[str, object]) -> list[dict[str, object]]:
    steps_by_id = {str(step["id"]): step for step in plan.get("steps", []) if isinstance(step, dict) and step.get("id")}
    result: list[dict[str, object]] = []
    for group in plan.get("groups", []):
        if not isinstance(group, dict):
            continue
        for step_id in group.get("step_ids", []):
            step = steps_by_id.get(str(step_id))
            if step:
                result.append(step)
    seen = {str(step["id"]) for step in result}
    result.extend(step for step in plan.get("steps", []) if isinstance(step, dict) and str(step.get("id")) not in seen)
    return result


def scene_element(
    element_id: str,
    element_type: str,
    x: int,
    y: int,
    width: int,
    height: int,
    text: str = "",
    custom: dict[str, object] | None = None,
    *,
    stroke: str = "#1f2937",
    fill: str = "#ffffff",
    roughness: int = 1,
    stroke_width: int = 2,
    points: list[list[int]] | None = None,
    frame_id: str | None = None,
) -> dict[str, object]:
    seed = int(hashlib.sha1(element_id.encode("utf-8")).hexdigest()[:7], 16)
    base: dict[str, object] = {
        "id": element_id,
        "type": element_type,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid" if fill != "transparent" else "hachure",
        "strokeWidth": stroke_width,
        "strokeStyle": "solid",
        "roughness": roughness,
        "opacity": 100,
        "groupIds": [],
        "frameId": frame_id,
        "roundness": {"type": 3} if element_type in {"rectangle", "diamond"} else None,
        "seed": seed,
        "version": 1,
        "versionNonce": seed + 17,
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "customData": custom or {},
    }
    if element_type == "text":
        base.update(
            {
                "text": text,
                "fontSize": 22,
                "fontFamily": EXCALIDRAW_TEXT_FONT_FAMILY,
                "textAlign": "left",
                "verticalAlign": "top",
                "containerId": None,
                "originalText": text,
                "lineHeight": 1.25,
                "baseline": max(height - 6, 18),
                "backgroundColor": "transparent",
                "strokeWidth": 1,
                "autoResize": True,
            }
        )
    if element_type in {"arrow", "line"}:
        base.update(
            {
                "points": points or [[0, 0], [width, height]],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": "arrow" if element_type == "arrow" else None,
            }
        )
    return {key: value for key, value in base.items() if value is not None}


def element_id(step_id: str, suffix: str) -> str:
    digest = hashlib.sha1(step_id.encode("utf-8")).hexdigest()[:8]
    return f"{digest}-{suffix}"


def base_custom(step: dict[str, object]) -> dict[str, object]:
    title = str(step.get("title") or step.get("id") or "step")
    entities = step.get("business_entities") if isinstance(step.get("business_entities"), list) else []
    return {
        "step_id": str(step.get("id") or ""),
        "group_id": str(step.get("group_id") or ""),
        "prd_section": str((step.get("prd_sections") or [title])[0]),
        "scene_type_reason": str(step.get("scene_type_reason") or ""),
        "source_evidence": step.get("source_evidence") if isinstance(step.get("source_evidence"), list) else [],
        "business_entity": " / ".join(str(item) for item in entities[:3]),
        "interaction_role": str(step.get("interaction_goal") or ""),
    }


def text_width(text: str, size: int) -> int:
    width = 0
    for char in text:
        width += size if "\u4e00" <= char <= "\u9fff" else max(7, int(size * 0.58))
    return max(160, width + 18)


def add_text(
    elements: list[dict[str, object]],
    step_id: str,
    suffix: str,
    x: int,
    y: int,
    text: str,
    custom: dict[str, object],
    size: int = 22,
    color: str = "#1f2937",
    frame_id: str | None = None,
) -> None:
    el = scene_element(element_id(step_id, suffix), "text", x, y, text_width(text, size), max(28, size + 10), text, custom, stroke=color, fill="transparent", frame_id=frame_id)
    el["fontSize"] = size
    elements.append(el)


def step_text_items(step: dict[str, object], limit: int = 5) -> list[str]:
    title = str(step.get("title") or "")
    evidence = [str(item) for item in step.get("source_evidence", []) if item] if isinstance(step.get("source_evidence"), list) else []
    entities = [str(item) for item in step.get("business_entities", []) if item] if isinstance(step.get("business_entities"), list) else []
    states = [str(item) for item in step.get("states_or_rules", []) if item] if isinstance(step.get("states_or_rules"), list) else []
    values = [title, *entities, *evidence, *states, str(step.get("interaction_goal") or "")]
    return unique_preserve(values, limit)


def compact_label(value: str, max_len: int = 24) -> str:
    value = clean_snippet(value, max_len=max_len)
    return value or "待确认"


def create_flow_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "Flow")
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    labels = step_text_items(step, 4)
    while len(labels) < 4:
        labels.append(f"{title} 节点 {len(labels) + 1}")
    for index, label in enumerate(labels[:4]):
        x = 70 + index * 220
        elements.append(scene_element(element_id(step_id, f"flow-box-{index}"), "rectangle", x, 120, 164, 112, "", custom, fill="#f8fafc"))
        add_text(elements, step_id, f"flow-text-{index}", x + 18, 148, compact_label(label), custom, 18)
        if index < 3:
            elements.append(scene_element(element_id(step_id, f"flow-arrow-{index}"), "arrow", x + 176, 176, 42, 0, custom=custom, points=[[0, 0], [42, 0]]))
    note = compact_label(str(step.get("scene_type_reason") or step.get("interaction_goal") or title), 58)
    elements.append(scene_element(element_id(step_id, "note-box"), "rectangle", 70, 304, 824, 92, "", custom, stroke="#64748b", fill="#eef6ff"))
    add_text(elements, step_id, "note", 96, 330, note, custom, 18, "#334155")
    return elements


def create_state_matrix_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "State Matrix")
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    cols = step_text_items(step, 4)
    while len(cols) < 4:
        cols.append(f"{title} 状态 {len(cols) + 1}")
    rows = ["界面表现", "系统响应", "用户可做"]
    for c, col in enumerate(cols):
        add_text(elements, step_id, f"col-{c}", 190 + c * 160, 94, compact_label(col, 16), custom, 17, "#475569")
    for r, row in enumerate(rows):
        add_text(elements, step_id, f"row-{r}", 54, 154 + r * 92, row, custom, 18, "#475569")
        for c, _col in enumerate(cols):
            fill = ["#f8fafc", "#fff7ed", "#ecfdf5", "#fef2f2"][c]
            elements.append(scene_element(element_id(step_id, f"cell-{r}-{c}"), "rectangle", 180 + c * 160, 140 + r * 92, 128, 58, "", custom, stroke="#94a3b8", fill=fill))
            if r == 1:
                add_text(elements, step_id, f"cell-label-{r}-{c}", 198 + c * 160, 158 + r * 92, compact_label(cols[c], 10), custom, 14, "#475569")
    return elements


def create_web_wireframe_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "Web Wireframe")
    labels = step_text_items(step, 6)
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    elements.append(scene_element(element_id(step_id, "page"), "rectangle", 70, 90, 820, 430, "", custom, fill="#ffffff"))
    elements.append(scene_element(element_id(step_id, "topbar"), "rectangle", 70, 90, 820, 58, "", custom, fill="#eff6ff"))
    add_text(elements, step_id, "topbar-label", 98, 108, compact_label(labels[0] if labels else title, 36), custom, 16, "#475569")
    elements.append(scene_element(element_id(step_id, "sidebar"), "rectangle", 70, 148, 180, 372, "", custom, fill="#f8fafc"))
    for i in range(4):
        elements.append(scene_element(element_id(step_id, f"nav-{i}"), "rectangle", 98, 182 + i * 52, 124, 22, "", custom, stroke="#cbd5e1", fill="#e2e8f0"))
    for i in range(3):
        elements.append(scene_element(element_id(step_id, f"card-{i}"), "rectangle", 284 + i * 188, 184, 150, 110, "", custom, stroke="#64748b", fill="#f8fafc"))
        add_text(elements, step_id, f"card-label-{i}", 300 + i * 188, 216, compact_label(labels[(i + 1) % len(labels)] if labels else title, 14), custom, 14, "#475569")
    elements.append(scene_element(element_id(step_id, "table"), "rectangle", 284, 338, 560, 126, "", custom, stroke="#64748b", fill="#ffffff"))
    for i in range(3):
        elements.append(scene_element(element_id(step_id, f"row-line-{i}"), "line", 284, 370 + i * 30, 560, 0, custom=custom, points=[[0, 0], [560, 0]], stroke="#cbd5e1"))
        if labels:
            add_text(elements, step_id, f"row-label-{i}", 306, 346 + i * 30, compact_label(labels[(i + 3) % len(labels)], 24), custom, 13, "#64748b")
    return elements


def create_overlay_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "Overlay")
    labels = step_text_items(step, 5)
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    elements.append(scene_element(element_id(step_id, "base"), "rectangle", 90, 90, 760, 420, "", custom, fill="#f8fafc"))
    elements.append(scene_element(element_id(step_id, "base-top"), "rectangle", 130, 124, 680, 44, "", custom, stroke="#cbd5e1", fill="#ffffff"))
    add_text(elements, step_id, "base-title", 154, 136, compact_label(labels[3] if len(labels) > 3 else title, 34), custom, 14, "#64748b")
    for i, label in enumerate(labels[:3]):
        elements.append(scene_element(element_id(step_id, f"base-row-{i}"), "rectangle", 154, 196 + i * 46, 260, 28, "", custom, stroke="#cbd5e1", fill="#ffffff"))
        add_text(elements, step_id, f"base-row-label-{i}", 170, 202 + i * 46, compact_label(label, 22), custom, 12, "#94a3b8")
    elements.append(scene_element(element_id(step_id, "dim"), "rectangle", 90, 90, 760, 420, "", custom, stroke="#64748b", fill="#e2e8f0"))
    elements[-1]["opacity"] = 62
    elements.append(scene_element(element_id(step_id, "modal"), "rectangle", 270, 174, 400, 230, "", custom, stroke="#1d4ed8", fill="#ffffff", stroke_width=3))
    add_text(elements, step_id, "modal-title", 312, 210, compact_label(labels[0] if labels else title, 28), custom, 20, "#1d4ed8")
    elements.append(scene_element(element_id(step_id, "field"), "rectangle", 312, 270, 316, 44, "", custom, stroke="#cbd5e1", fill="#f8fafc"))
    add_text(elements, step_id, "field-label", 330, 282, compact_label(labels[1] if len(labels) > 1 else str(step.get("scene_type_reason") or title), 26), custom, 15, "#64748b")
    elements.append(scene_element(element_id(step_id, "primary"), "rectangle", 492, 338, 120, 42, "", custom, stroke="#2563eb", fill="#dbeafe"))
    add_text(elements, step_id, "primary-label", 520, 348, compact_label(labels[2] if len(labels) > 2 else "继续", 8), custom, 15, "#1d4ed8")
    elements.append(scene_element(element_id(step_id, "secondary"), "rectangle", 350, 338, 112, 42, "", custom, stroke="#94a3b8", fill="#ffffff"))
    add_text(elements, step_id, "secondary-label", 382, 348, "返回", custom, 15, "#475569")
    return elements


def create_decision_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "Decision")
    labels = step_text_items(step, 5)
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    elements.append(scene_element(element_id(step_id, "start"), "ellipse", 80, 160, 150, 80, "", custom, fill="#ecfdf5"))
    add_text(elements, step_id, "start-text", 104, 186, compact_label(labels[0] if labels else title, 12), custom, 18)
    elements.append(scene_element(element_id(step_id, "decision"), "diamond", 350, 130, 170, 140, "", custom, fill="#fff7ed"))
    add_text(elements, step_id, "decision-text", 382, 178, compact_label(labels[1] if len(labels) > 1 else str(step.get("scene_type_reason") or title), 12), custom, 16)
    elements.append(scene_element(element_id(step_id, "yes"), "rectangle", 650, 96, 170, 86, "", custom, fill="#eff6ff"))
    add_text(elements, step_id, "yes-text", 672, 122, compact_label(labels[2] if len(labels) > 2 else title, 14), custom, 17)
    elements.append(scene_element(element_id(step_id, "no"), "rectangle", 650, 270, 170, 86, "", custom, fill="#fef2f2"))
    add_text(elements, step_id, "no-text", 672, 296, compact_label(labels[3] if len(labels) > 3 else "需处理分支", 14), custom, 17)
    elements.append(scene_element(element_id(step_id, "arrow-a"), "arrow", 238, 200, 96, 0, custom=custom, points=[[0, 0], [96, 0]]))
    elements.append(scene_element(element_id(step_id, "arrow-b"), "arrow", 522, 176, 112, -40, custom=custom, points=[[0, 0], [112, -40]]))
    elements.append(scene_element(element_id(step_id, "arrow-c"), "arrow", 522, 224, 112, 78, custom=custom, points=[[0, 0], [112, 78]]))
    add_text(elements, step_id, "label-yes", 570, 122, "Path A", custom, 16, "#16a34a")
    add_text(elements, step_id, "label-no", 570, 286, "Path B", custom, 16, "#dc2626")
    return elements


def create_list_table_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "List/Table")
    labels = step_text_items(step, 6)
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    elements.append(scene_element(element_id(step_id, "toolbar"), "rectangle", 70, 92, 820, 58, "", custom, fill="#f8fafc"))
    elements.append(scene_element(element_id(step_id, "search"), "rectangle", 94, 108, 240, 28, "", custom, stroke="#cbd5e1", fill="#ffffff"))
    add_text(elements, step_id, "search-label", 112, 113, compact_label(labels[0] if labels else title, 20), custom, 14, "#64748b")
    elements.append(scene_element(element_id(step_id, "button"), "rectangle", 740, 104, 110, 34, "", custom, stroke="#2563eb", fill="#dbeafe"))
    add_text(elements, step_id, "button-label", 760, 112, compact_label(labels[1] if len(labels) > 1 else "操作", 8), custom, 14, "#1d4ed8")
    elements.append(scene_element(element_id(step_id, "table"), "rectangle", 70, 174, 820, 288, "", custom, fill="#ffffff"))
    for i in range(1, 6):
        elements.append(scene_element(element_id(step_id, f"table-line-{i}"), "line", 70, 174 + i * 48, 820, 0, custom=custom, points=[[0, 0], [820, 0]], stroke="#cbd5e1"))
    for i, x in enumerate([220, 430, 620, 760]):
        elements.append(scene_element(element_id(step_id, f"col-line-{i}"), "line", x, 174, 0, 288, custom=custom, points=[[0, 0], [0, 288]], stroke="#e2e8f0"))
    for i in range(4):
        elements.append(scene_element(element_id(step_id, f"status-{i}"), "ellipse", 112, 244 + i * 48, 18, 18, "", custom, stroke="#16a34a", fill="#dcfce7"))
        elements.append(scene_element(element_id(step_id, f"action-{i}"), "rectangle", 790, 238 + i * 48, 52, 24, "", custom, stroke="#94a3b8", fill="#f8fafc"))
        add_text(elements, step_id, f"row-label-{i}", 150, 238 + i * 48, compact_label(labels[(i + 2) % len(labels)] if labels else title, 32), custom, 14, "#475569")
    return elements


def create_mobile_wireframe_scene(step: dict[str, object]) -> list[dict[str, object]]:
    step_id = str(step["id"])
    custom = base_custom(step)
    elements: list[dict[str, object]] = []
    title = str(step.get("title") or "Mobile Wireframe")
    labels = step_text_items(step, 6)
    add_text(elements, step_id, "title", 40, 24, title, custom, 28)
    elements.append(scene_element(element_id(step_id, "app-shell"), "rectangle", 96, 88, 312, 560, "", custom, stroke="#334155", fill="#ffffff", stroke_width=3))
    elements.append(scene_element(element_id(step_id, "statusbar"), "rectangle", 116, 112, 272, 36, "", custom, stroke="#cbd5e1", fill="#f8fafc"))
    add_text(elements, step_id, "screen-title", 142, 160, compact_label(labels[0] if labels else title, 18), custom, 20, "#1f2937")
    elements.append(scene_element(element_id(step_id, "search"), "rectangle", 132, 204, 240, 40, "", custom, stroke="#cbd5e1", fill="#f8fafc"))
    add_text(elements, step_id, "search-text", 152, 214, compact_label(labels[1] if len(labels) > 1 else "查找内容", 18), custom, 15, "#64748b")
    for index in range(4):
        y = 270 + index * 70
        elements.append(scene_element(element_id(step_id, f"list-item-{index}"), "rectangle", 132, y, 240, 52, "", custom, stroke="#cbd5e1", fill="#ffffff"))
        elements.append(scene_element(element_id(step_id, f"avatar-{index}"), "ellipse", 150, y + 14, 24, 24, "", custom, stroke="#94a3b8", fill="#e2e8f0"))
        add_text(elements, step_id, f"item-label-{index}", 188, y + 12, compact_label(labels[(index + 2) % len(labels)] if labels else title, 16), custom, 14, "#334155")
        elements.append(scene_element(element_id(step_id, f"sub-line-{index}"), "line", 188, y + 36, 82, 0, custom=custom, points=[[0, 0], [82, 0]], stroke="#cbd5e1", stroke_width=2))
    elements.append(scene_element(element_id(step_id, "bottom-tab"), "rectangle", 116, 590, 272, 42, "", custom, stroke="#cbd5e1", fill="#f8fafc"))
    tabs = unique_preserve(["首页", compact_label(labels[0] if labels else title, 4), "我的"], 3)
    for index, label in enumerate(tabs):
        add_text(elements, step_id, f"tab-{index}", 150 + index * 78, 602, label, custom, 14, "#475569")
    elements.append(scene_element(element_id(step_id, "note"), "rectangle", 470, 168, 350, 150, "", custom, stroke="#64748b", fill="#eef6ff"))
    add_text(elements, step_id, "note-text", 494, 196, compact_label(str(step.get("scene_type_reason") or step.get("interaction_goal") or title), 52), custom, 17, "#334155")
    elements.append(scene_element(element_id(step_id, "callout-arrow"), "arrow", 470, 300, -70, 150, custom=custom, points=[[0, 0], [-70, 150]], stroke="#64748b"))
    return elements


SCENE_BUILDERS = {
    "flow": create_flow_scene,
    "state_matrix": create_state_matrix_scene,
    "web_wireframe": create_web_wireframe_scene,
    "overlay": create_overlay_scene,
    "decision_branch": create_decision_scene,
    "list_table": create_list_table_scene,
    "mobile_wireframe": create_mobile_wireframe_scene,
}


def create_excalidraw_scene(step: dict[str, object], index: int = 0) -> dict[str, object]:
    scene_type = str(step.get("scene_type") or "flow")
    builder = SCENE_BUILDERS.get(scene_type, create_flow_scene)
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "Finn ProtoPilot Excalidraw",
        "elements": builder(step),
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None, "currentItemFontFamily": EXCALIDRAW_TEXT_FONT_FAMILY},
        "files": {},
    }


def storyboard_frame_element(frame_id: str, x: int, y: int, width: int, height: int, name: str, custom: dict[str, object], order: int) -> dict[str, object]:
    frame = scene_element(frame_id, "frame", x, y, width, height, "", custom, stroke="#ffffff", fill="transparent", roughness=0, stroke_width=1)
    frame["name"] = name
    frame["boundElements"] = []
    frame["opacity"] = 100
    return frame


def add_box(
    elements: list[dict[str, object]],
    step_id: str,
    suffix: str,
    x: int,
    y: int,
    width: int,
    height: int,
    custom: dict[str, object],
    *,
    frame_id: str,
    stroke: str = "#d8dee8",
    fill: str = "#ffffff",
    stroke_width: int = 1,
) -> None:
    elements.append(scene_element(element_id(step_id, suffix), "rectangle", x, y, width, height, "", custom, stroke=stroke, fill=fill, stroke_width=stroke_width, roughness=0, frame_id=frame_id))


def add_line_element(elements: list[dict[str, object]], step_id: str, suffix: str, x: int, y: int, width: int, height: int, custom: dict[str, object], *, frame_id: str, stroke: str = "#e5e7eb") -> None:
    elements.append(scene_element(element_id(step_id, suffix), "line", x, y, width, height, custom=custom, points=[[0, 0], [width, height]], stroke=stroke, stroke_width=1, roughness=0, frame_id=frame_id))


def mobile_frame_pattern(step: dict[str, object]) -> str:
    title = str(step.get("title") or "")
    kind = str(step.get("screen_kind") or "")
    title_lower = title.lower()
    if any(term in title_lower for term in ("modal", "popup", "upgrade", "offline")):
        return "modal"
    if any(term in title_lower for term in ("settings", "account", "profile", " me")):
        return "settings"
    if any(term in title_lower for term in ("message", "notification", "notice", "alert")):
        return "messages"
    if any(term in title_lower for term in ("detail", "history")):
        return "detail"
    if any(term in title_lower for term in ("home", "main", "overview", "dashboard")):
        return "dashboard"
    if any(term in title_lower for term in ("empty", "no data", "expired")):
        return "empty"
    if any(term in title_lower for term in ("login", "auth")):
        return "login"
    if any(term in title_lower for term in ("chat", "workspace")):
        return "chat"
    if kind == "modal" or contains_any(title, {"弹窗", "确认", "删除", "关闭"}):
        return "modal"
    if kind == "settings" or contains_any(title, {"设置", "配置", "通知设置"}):
        return "settings"
    if contains_any(title, {"消息", "通知", "警报"}):
        return "messages"
    if contains_any(title, {"详情", "行程"}):
        return "detail"
    if contains_any(title, {"主页", "报告", "有数据"}):
        return "dashboard"
    if contains_any(title, {"空", "无数据", "过期"}):
        return "empty"
    if contains_any(title, {"登录", "认证"}):
        return "login"
    if contains_any(title, {"会话", "聊天", "工作台"}):
        return "chat"
    return "list"


def brief_for_step(step: dict[str, object]) -> dict[str, object]:
    brief = step.get("storyboard_brief")
    if isinstance(brief, dict):
        return brief
    semantic = step.get("semantic_frame_spec")
    if isinstance(semantic, dict) and isinstance(semantic.get("storyboard_brief"), dict):
        return semantic["storyboard_brief"]
    return {}


def mobile_visible_copy(step: dict[str, object], limit: int = 16) -> list[str]:
    brief = brief_for_step(step)
    values: list[object] = []
    values.extend(brief.get("visible_copy", []) if isinstance(brief.get("visible_copy"), list) else [])
    values.extend(brief.get("data_examples", []) if isinstance(brief.get("data_examples"), list) else [])
    values.extend(step.get("key_copy", []) if isinstance(step.get("key_copy"), list) else [])
    values.extend(step.get("source_evidence", []) if isinstance(step.get("source_evidence"), list) else [])
    values.append(step.get("title", ""))
    return product_text_candidates(values, limit, max_len=84)


def add_mobile_shell(elements: list[dict[str, object]], step: dict[str, object], x: int, y: int, frame_id: str, order: int, title: str, *, right: str = "") -> dict[str, object]:
    step_id = str(step["id"])
    custom = base_custom(step)
    custom["board_id"] = str(step.get("board_id") or "")
    custom["frame_id"] = frame_id
    elements.append(storyboard_frame_element(frame_id, x, y, 300, 580, str(step.get("frame_name") or title), custom, order))
    add_box(elements, step_id, "phone", x + 10, y + 10, 280, 560, custom, frame_id=frame_id, stroke="#cbd5e1", fill="#ffffff", stroke_width=1)
    add_text(elements, step_id, "status", x + 28, y + 28, "12:30          5G ▮▮▮", custom, 12, "#94a3b8", frame_id=frame_id)
    add_line_element(elements, step_id, "top-line", x + 30, y + 64, 240, 0, custom, frame_id=frame_id)
    add_text(elements, step_id, "back", x + 28, y + 78, "←", custom, 18, "#64748b", frame_id=frame_id)
    add_text(elements, step_id, "nav-title", x + 95, y + 78, compact_label(title, 16), custom, 16, "#1f2937", frame_id=frame_id)
    if right:
        add_text(elements, step_id, "nav-right", x + 252, y + 80, compact_label(right, 4), custom, 15, "#64748b", frame_id=frame_id)
    return custom


def add_row(elements: list[dict[str, object]], step_id: str, suffix: str, x: int, y: int, label: str, custom: dict[str, object], *, frame_id: str, sub: str = "", value: str = "›") -> None:
    add_box(elements, step_id, suffix, x, y, 240, 48, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
    add_text(elements, step_id, f"{suffix}-label", x + 14, y + 12, compact_label(label, 20), custom, 12, "#334155", frame_id=frame_id)
    if sub:
        add_text(elements, step_id, f"{suffix}-sub", x + 14, y + 29, compact_label(sub, 24), custom, 10, "#94a3b8", frame_id=frame_id)
    if value:
        add_text(elements, step_id, f"{suffix}-value", x + 210, y + 15, compact_label(value, 8), custom, 12, "#2383ff", frame_id=frame_id)


def add_metric_card(elements: list[dict[str, object]], step_id: str, suffix: str, x: int, y: int, label: str, value: str, custom: dict[str, object], *, frame_id: str, fill: str = "#f8fafc") -> None:
    add_box(elements, step_id, suffix, x, y, 110, 52, custom, frame_id=frame_id, stroke="#e2e8f0", fill=fill)
    add_text(elements, step_id, f"{suffix}-label", x + 10, y + 10, compact_label(label, 9), custom, 11, "#64748b", frame_id=frame_id)
    add_text(elements, step_id, f"{suffix}-value", x + 10, y + 29, compact_label(value, 10), custom, 15, "#1f2937", frame_id=frame_id)


def draw_mobile_brief_frame(elements: list[dict[str, object]], step: dict[str, object], x: int, y: int, frame_id: str, order: int) -> None:
    brief = brief_for_step(step)
    archetype = str(brief.get("surface_archetype") or step.get("surface_archetype") or "")
    if not archetype or archetype in {"mobile_page", "list", "settings", "detail", "state", "modal", "rule_annotation"}:
        draw_mobile_story_frame(elements, step, x, y, frame_id, order, force_generic=True)
        return

    step_id = str(step["id"])
    copy = mobile_visible_copy(step, 18)
    title = str(step.get("title") or (copy[0] if copy else "界面"))
    nav_title = "驾驶侦测" if "驾驶" in title and "设置" not in title and "详情" not in title else title
    right = "⚙" if archetype in {"driving_dashboard_data", "driving_dashboard_empty", "subscription_expired", "alert_center"} else ""
    custom = add_mobile_shell(elements, step, x, y, frame_id, order, nav_title, right=right)

    if archetype == "device_safety_home":
        add_text(elements, step_id, "device-title", x + 105, y + 106, copy[0] if len(copy) > 0 else "孩子的设备", custom, 14, "#334155", frame_id=frame_id)
        add_text(elements, step_id, "section-label", x + 32, y + 148, copy[1] if len(copy) > 1 else "位置与安全", custom, 12, "#64748b", frame_id=frame_id)
        add_row(elements, step_id, "row-driving", x + 30, y + 176, copy[2] if len(copy) > 2 else "驾驶侦测", custom, frame_id=frame_id)
        add_row(elements, step_id, "row-location", x + 30, y + 232, copy[3] if len(copy) > 3 else "定位设置", custom, frame_id=frame_id)
        add_row(elements, step_id, "row-sos", x + 30, y + 288, copy[4] if len(copy) > 4 else "SOS 设置", custom, frame_id=frame_id)
        add_text(elements, step_id, "android-note", x + 36, y + 354, copy[5] if len(copy) > 5 else "（部分平台入口按规则隐藏）", custom, 10, "#64748b", frame_id=frame_id)
    elif archetype == "location_entry":
        add_box(elements, step_id, "map", x + 32, y + 122, 236, 300, custom, frame_id=frame_id, stroke="#bfdbfe", fill="#eaf5ff")
        add_text(elements, step_id, "map-label", x + 112, y + 254, "[ 地图区域 ]", custom, 13, "#64748b", frame_id=frame_id)
        add_box(elements, step_id, "entry-button", x + 32, y + 432, 236, 44, custom, frame_id=frame_id, stroke="#2383ff", fill="#ffffff", stroke_width=2)
        add_text(elements, step_id, "entry-label", x + 116, y + 446, "驾驶侦测 ›", custom, 13, "#2383ff", frame_id=frame_id)
    elif archetype == "onboarding":
        add_box(elements, step_id, "hero", x + 88, y + 130, 124, 108, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#f8fafc", stroke_width=2)
        add_text(elements, step_id, "headline", x + 70, y + 270, "记录驾驶行为，识别风险并提醒", custom, 13, "#334155", frame_id=frame_id)
        bullets = ["自动记录每一次出行轨迹与时长", "精准捕捉超速、急刹、急加速", "发现风险立即推送到你的手机"]
        for i, label in enumerate(bullets):
            add_text(elements, step_id, f"bullet-{i}", x + 50, y + 320 + i * 28, f"• {label}", custom, 11, "#64748b", frame_id=frame_id)
        add_box(elements, step_id, "enable-button", x + 64, y + 456, 172, 46, custom, frame_id=frame_id, stroke="#2383ff", fill="#2383ff")
        add_text(elements, step_id, "enable-label", x + 140, y + 471, "启用", custom, 14, "#ffffff", frame_id=frame_id)
    elif archetype in {"driving_dashboard_data", "driving_dashboard_empty", "subscription_expired"}:
        if archetype == "subscription_expired":
            add_box(elements, step_id, "expired-banner", x + 28, y + 116, 244, 40, custom, frame_id=frame_id, stroke="#f59e0b", fill="#fff7d6")
            add_text(elements, step_id, "expired-text", x + 42, y + 128, "此功能已暂停，订阅后可恢复运行 ›", custom, 10, "#92400e", frame_id=frame_id)
            start_y = y + 176
        else:
            add_box(elements, step_id, "period", x + 72, y + 116, 156, 28, custom, frame_id=frame_id, stroke="#d8dee8", fill="#f8fafc")
            add_text(elements, step_id, "period-label", x + 122, y + 122, "‹ 本周 ›", custom, 12, "#64748b", frame_id=frame_id)
            start_y = y + 162
        if archetype == "driving_dashboard_empty":
            add_box(elements, step_id, "empty-illu", x + 88, y + 230, 124, 96, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#f8fafc", stroke_width=2)
            add_text(elements, step_id, "empty-text", x + 126, y + 356, "暂无数据", custom, 15, "#94a3b8", frame_id=frame_id)
        else:
            add_text(elements, step_id, "summary", x + 72, start_y, "47 公里 · 最高时速 86 公里/小时", custom, 11, "#64748b", frame_id=frame_id)
            metrics = [("驾驶次数", "—"), ("超速", "—"), ("急加速", "—"), ("急刹车", "—")]
            for i, (label, value) in enumerate(metrics):
                add_metric_card(elements, step_id, f"metric-{i}", x + 30 + (i % 2) * 130, y + 190 + (i // 2) * 68, label, value, custom, frame_id=frame_id)
            add_box(elements, step_id, "chart", x + 42, y + 334, 216, 64, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
            for i, h in enumerate([20, 28, 42, 24, 34, 46, 26]):
                add_box(elements, step_id, f"bar-{i}", x + 62 + i * 26, y + 376 - h, 13, h, custom, frame_id=frame_id, stroke="#2383ff", fill="#2383ff")
            add_text(elements, step_id, "trips-title", x + 36, y + 420, "Trips", custom, 12, "#64748b", frame_id=frame_id)
            add_box(elements, step_id, "trip-card", x + 30, y + 442, 240, 84, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
            add_box(elements, step_id, "trip-map", x + 40, y + 452, 220, 26, custom, frame_id=frame_id, stroke="#bfdbfe", fill="#eaf5ff")
            add_text(elements, step_id, "trip-route", x + 44, y + 488, "○ 家 → ▽ 学校", custom, 10, "#64748b", frame_id=frame_id)
            add_text(elements, step_id, "trip-time", x + 44, y + 506, "08:30 - 09:15 · 12 公里", custom, 10, "#64748b", frame_id=frame_id)
            add_text(elements, step_id, "trip-speed", x + 44, y + 522, "96km/h", custom, 10, "#ef4444", frame_id=frame_id)
            add_text(elements, step_id, "trip-risk", x + 194, y + 522, "2 个风险事件 ›", custom, 10, "#ef4444", frame_id=frame_id)
    elif archetype == "trip_detail":
        add_box(elements, step_id, "map", x + 34, y + 116, 232, 156, custom, frame_id=frame_id, stroke="#bfdbfe", fill="#eaf5ff")
        add_text(elements, step_id, "map-label", x + 94, y + 184, "[ 轨迹 + 事件锚点 ]", custom, 12, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "kid", x + 44, y + 302, copy[2] if len(copy) > 2 else "⭐ 孩子", custom, 12, "#334155", frame_id=frame_id)
        add_text(elements, step_id, "start", x + 44, y + 328, "○ 家                                      08:30", custom, 10, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "end", x + 44, y + 350, "▽ 学校                                  09:15", custom, 10, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "duration", x + 44, y + 376, "08:30 - 09:15 · 12 公里", custom, 10, "#64748b", frame_id=frame_id)
        stats = [("最快速度", "96 km/h"), ("超速", "1 次"), ("急刹车", "0 次"), ("急加速", "1 次")]
        for i, (label, value) in enumerate(stats):
            add_metric_card(elements, step_id, f"detail-stat-{i}", x + 34 + (i % 2) * 118, y + 404 + (i // 2) * 58, label, value, custom, frame_id=frame_id)
    elif archetype in {"driving_settings", "notification_settings", "profile_settings"}:
        add_text(elements, step_id, "settings-group", x + 32, y + 122, "基础设置" if archetype == "driving_settings" else "通知设置", custom, 11, "#64748b", frame_id=frame_id)
        rows = [("启用驾驶侦测", "[ON]"), ("超速阈值", "80 km/h ›"), ("单位", "km/h ›")] if archetype == "driving_settings" else [("驾驶侦测", "[ON]")]
        for i, (label, value) in enumerate(rows):
            add_row(elements, step_id, f"setting-row-{i}", x + 30, y + 150 + i * 58, label, custom, frame_id=frame_id, value=value)
        note = "通知：消息中心 → 消息通知设置 → 驾驶侦测" if archetype == "driving_settings" else "统一控制超速实时 Push 与行程结束聚合 Push"
        add_text(elements, step_id, "setting-note", x + 34, y + 352, compact_label(note, 34), custom, 10, "#64748b", frame_id=frame_id)
    elif archetype in {"close_confirm_modal", "drawer"}:
        add_box(elements, step_id, "modal-page", x + 28, y + 116, 244, 394, custom, frame_id=frame_id, stroke="#eef2f7", fill="#f8fafc")
        add_box(elements, step_id, "modal", x + 58, y + 316, 184, 150, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff", stroke_width=2)
        add_text(elements, step_id, "modal-title", x + 96, y + 346, "关闭驾驶侦测", custom, 15, "#334155", frame_id=frame_id)
        add_text(elements, step_id, "modal-body", x + 70, y + 386, "关闭后将停止记录新的驾驶行为", custom, 10, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "modal-cancel", x + 88, y + 430, "取消", custom, 13, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "modal-ok", x + 184, y + 430, "确定", custom, 13, "#2383ff", frame_id=frame_id)
    elif archetype in {"alert_center", "chat_list"}:
        add_box(elements, step_id, "segmented", x + 32, y + 118, 236, 34, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
        tabs = ["提醒", "请求", "警报"] if archetype == "alert_center" else ["全部", "未读", "最近"]
        for i, tab in enumerate(tabs):
            add_text(elements, step_id, f"tab-{i}", x + 66 + i * 74, y + 128, tab, custom, 11, "#2383ff" if i == len(tabs) - 1 else "#94a3b8", frame_id=frame_id)
        if archetype == "alert_center":
            rows = [
                (copy[4] if len(copy) > 4 else "车速超过 80 km/h（当前 96 km/h）", "超速", f"{copy[5] if len(copy) > 5 else '请注意驾驶安全'} · {copy[6] if len(copy) > 6 else '今天 14:32'}", "未读", "查看行程 ›"),
                (copy[7] if len(copy) > 7 else "本次行程检测到急刹车 4 次", "急刹车", f"请关注驾驶安全 · {copy[8] if len(copy) > 8 else '昨天 18:05'}", "已读", "行程详情 ›"),
            ]
            for i, (label, badge, sub, state_label, jump) in enumerate(rows):
                row_y = y + 172 + i * 82
                add_box(elements, step_id, f"alert-card-{i}", x + 30, row_y, 240, 66, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
                add_box(elements, step_id, f"alert-badge-{i}", x + 42, row_y + 10, 50, 20, custom, frame_id=frame_id, stroke="#fca5a5", fill="#fff1f2")
                add_text(elements, step_id, f"alert-badge-label-{i}", x + 52, row_y + 14, compact_label(badge, 5), custom, 10, "#b91c1c", frame_id=frame_id)
                add_text(elements, step_id, f"alert-title-{i}", x + 100, row_y + 10, compact_label(label, 28), custom, 12, "#334155", frame_id=frame_id)
                add_text(elements, step_id, f"alert-sub-{i}", x + 42, row_y + 36, compact_label(sub, 26), custom, 10, "#64748b", frame_id=frame_id)
                add_text(elements, step_id, f"alert-state-{i}", x + 178, row_y + 36, state_label, custom, 10, "#94a3b8", frame_id=frame_id)
                add_text(elements, step_id, f"alert-jump-{i}", x + 210, row_y + 52, compact_label(jump, 8), custom, 10, "#64748b", frame_id=frame_id)
            add_line_element(elements, step_id, "bottom-line", x + 30, y + 538, 240, 0, custom, frame_id=frame_id)
            return
        else:
            add_box(elements, step_id, "search", x + 32, y + 166, 236, 34, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
            add_text(elements, step_id, "search-text", x + 52, y + 176, copy[1] if len(copy) > 1 else "搜索", custom, 11, "#94a3b8", frame_id=frame_id)
            rows = [
                (copy[0] if copy else "会话列表", "未读 · 最近会话"),
                (copy[2] if len(copy) > 2 else "最近会话", "今天 · 已同步"),
            ]
        for i, (label, sub) in enumerate(rows):
            row_y = 174 + i * 78 if archetype == "alert_center" else 220 + i * 78
            add_row(elements, step_id, f"alert-row-{i}", x + 30, y + row_y, label, custom, frame_id=frame_id, sub=sub, value="")
        if archetype == "chat_list":
            add_box(elements, step_id, "bottom-tab", x + 32, y + 504, 236, 36, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
            add_text(elements, step_id, "bottom-tab-text", x + 82, y + 515, copy[3] if len(copy) > 3 else "底部 Tab", custom, 11, "#2383ff", frame_id=frame_id)
    elif archetype in {"chat_session", "workspace", "login"}:
        draw_mobile_story_frame(elements, step, x, y, frame_id, order, force_generic=True)
        return
    else:
        draw_mobile_story_frame(elements, step, x, y, frame_id, order, force_generic=True)
        return

    add_line_element(elements, step_id, "bottom-line", x + 30, y + 538, 240, 0, custom, frame_id=frame_id)


def draw_mobile_story_frame(elements: list[dict[str, object]], step: dict[str, object], x: int, y: int, frame_id: str, order: int, *, force_generic: bool = False) -> None:
    if not force_generic and brief_for_step(step) and (not step.get("is_showcase_sample") or str(step.get("scene_type") or "") == "mobile_wireframe"):
        draw_mobile_brief_frame(elements, step, x, y, frame_id, order)
        return
    step_id = str(step["id"])
    custom = base_custom(step)
    custom["board_id"] = str(step.get("board_id") or "")
    custom["frame_id"] = frame_id
    title = clean_snippet(str(step.get("title") or "界面"), 34)
    labels = key_copy_for(step)
    while len(labels) < 6:
        labels.append(title)
    elements.append(storyboard_frame_element(frame_id, x, y, 300, 580, str(step.get("frame_name") or title), custom, order))
    add_box(elements, step_id, "phone", x + 10, y + 10, 280, 560, custom, frame_id=frame_id, stroke="#cbd5e1", fill="#ffffff", stroke_width=1)
    add_text(elements, step_id, "status", x + 28, y + 28, "12:30          5G ▮▮▮", custom, 12, "#94a3b8", frame_id=frame_id)
    add_line_element(elements, step_id, "top-line", x + 30, y + 64, 240, 0, custom, frame_id=frame_id)
    add_text(elements, step_id, "back", x + 28, y + 78, "←", custom, 18, "#64748b", frame_id=frame_id)
    add_text(elements, step_id, "nav-title", x + 88, y + 78, compact_label(labels[0], 18), custom, 17, "#1f2937", frame_id=frame_id)
    pattern = mobile_frame_pattern(step)
    if pattern == "dashboard":
        add_box(elements, step_id, "period", x + 66, y + 116, 168, 28, custom, frame_id=frame_id, stroke="#d8dee8", fill="#f8fafc")
        add_text(elements, step_id, "period-label", x + 118, y + 121, "‹ 本周 ›", custom, 12, "#64748b", frame_id=frame_id)
        for i, label in enumerate(labels[1:5]):
            cx = x + 30 + (i % 2) * 130
            cy = y + 166 + (i // 2) * 72
            add_box(elements, step_id, f"metric-{i}", cx, cy, 110, 52, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
            add_text(elements, step_id, f"metric-label-{i}", cx + 10, cy + 10, compact_label(label, 8), custom, 11, "#64748b", frame_id=frame_id)
            add_text(elements, step_id, f"metric-value-{i}", cx + 12, cy + 30, "—", custom, 18, "#1f2937", frame_id=frame_id)
        add_box(elements, step_id, "chart", x + 36, y + 318, 224, 70, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
        for i in range(7):
            add_box(elements, step_id, f"bar-{i}", x + 56 + i * 28, y + 362 - (i % 4) * 10, 14, 22 + (i % 4) * 10, custom, frame_id=frame_id, stroke="#2383ff", fill="#2383ff")
        add_box(elements, step_id, "trip-card", x + 30, y + 414, 240, 90, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
        add_text(elements, step_id, "trip-title", x + 44, y + 428, compact_label(labels[5], 22), custom, 12, "#334155", frame_id=frame_id)
        add_text(elements, step_id, "trip-risk", x + 196, y + 474, "›", custom, 18, "#2383ff", frame_id=frame_id)
    elif pattern == "detail":
        add_box(elements, step_id, "map", x + 34, y + 120, 232, 150, custom, frame_id=frame_id, stroke="#bfdbfe", fill="#eaf5ff")
        add_text(elements, step_id, "map-label", x + 96, y + 184, "[ 轨迹 / 事件锚点 ]", custom, 13, "#64748b", frame_id=frame_id)
        for i, label in enumerate(labels[1:4]):
            add_text(elements, step_id, f"detail-line-{i}", x + 42, y + 294 + i * 26, compact_label(label, 24), custom, 12, "#475569", frame_id=frame_id)
        for i, label in enumerate(labels[4:8]):
            cx = x + 34 + (i % 2) * 118
            cy = y + 392 + (i // 2) * 58
            add_box(elements, step_id, f"detail-stat-{i}", cx, cy, 104, 44, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
            add_text(elements, step_id, f"detail-stat-label-{i}", cx + 8, cy + 9, compact_label(label, 10), custom, 11, "#64748b", frame_id=frame_id)
    elif pattern == "settings":
        for i, label in enumerate(labels[:5]):
            yy = y + 132 + i * 62
            add_box(elements, step_id, f"setting-row-{i}", x + 28, yy, 244, 48, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
            add_text(elements, step_id, f"setting-label-{i}", x + 44, yy + 15, compact_label(label, 18), custom, 13, "#334155", frame_id=frame_id)
            add_text(elements, step_id, f"setting-value-{i}", x + 220, yy + 15, "[ON]" if i == 0 else "›", custom, 12, "#2383ff", frame_id=frame_id)
        add_text(elements, step_id, "setting-note", x + 32, y + 482, compact_label(labels[-1], 34), custom, 11, "#64748b", frame_id=frame_id)
    elif pattern == "modal":
        add_box(elements, step_id, "modal-page", x + 28, y + 118, 244, 360, custom, frame_id=frame_id, stroke="#eef2f7", fill="#f8fafc")
        add_box(elements, step_id, "modal", x + 58, y + 302, 184, 150, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff", stroke_width=2)
        add_text(elements, step_id, "modal-heading", x + 96, y + 330, compact_label(labels[0], 14), custom, 16, "#334155", frame_id=frame_id)
        add_text(elements, step_id, "modal-body", x + 72, y + 374, compact_label(labels[1], 28), custom, 11, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "modal-cancel", x + 86, y + 424, "取消", custom, 13, "#64748b", frame_id=frame_id)
        add_text(elements, step_id, "modal-ok", x + 184, y + 424, "确定", custom, 13, "#2383ff", frame_id=frame_id)
    elif pattern == "chat":
        add_box(elements, step_id, "chat-context", x + 32, y + 116, 236, 42, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
        add_text(elements, step_id, "chat-context-label", x + 48, y + 128, compact_label(labels[0], 22), custom, 12, "#64748b", frame_id=frame_id)
        for i, label in enumerate(labels[:4]):
            yy = y + 190 + i * 70
            is_user = i % 2 == 1
            bx = x + (84 if is_user else 34)
            fill = "#dbeafe" if is_user else "#ffffff"
            add_box(elements, step_id, f"bubble-{i}", bx, yy, 184, 46, custom, frame_id=frame_id, stroke="#d8dee8", fill=fill)
            add_text(elements, step_id, f"bubble-text-{i}", bx + 14, yy + 13, compact_label(label, 20), custom, 12, "#334155", frame_id=frame_id)
        add_box(elements, step_id, "composer", x + 34, y + 480, 232, 38, custom, frame_id=frame_id, stroke="#d8dee8", fill="#ffffff")
        add_text(elements, step_id, "composer-label", x + 52, y + 490, compact_label(labels[-1], 20), custom, 11, "#94a3b8", frame_id=frame_id)
    elif pattern in {"messages", "list", "login", "empty"}:
        if pattern == "empty":
            add_box(elements, step_id, "empty-illu", x + 88, y + 210, 124, 92, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#f8fafc")
            add_text(elements, step_id, "empty-text", x + 114, y + 334, compact_label(labels[0], 16), custom, 15, "#94a3b8", frame_id=frame_id)
        elif pattern == "login":
            for i, label in enumerate(labels[:3]):
                add_box(elements, step_id, f"login-field-{i}", x + 36, y + 146 + i * 60, 228, 42, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
                add_text(elements, step_id, f"login-label-{i}", x + 52, y + 158 + i * 60, compact_label(label, 20), custom, 12, "#64748b", frame_id=frame_id)
            add_box(elements, step_id, "login-btn", x + 36, y + 354, 228, 48, custom, frame_id=frame_id, stroke="#2383ff", fill="#2383ff")
            add_text(elements, step_id, "login-btn-label", x + 132, y + 368, "继续", custom, 14, "#ffffff", frame_id=frame_id)
        else:
            if pattern == "messages":
                add_box(elements, step_id, "segmented", x + 32, y + 120, 236, 34, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
                add_text(elements, step_id, "seg-a", x + 66, y + 129, "提醒", custom, 11, "#94a3b8", frame_id=frame_id)
                add_text(elements, step_id, "seg-b", x + 140, y + 129, "请求", custom, 11, "#94a3b8", frame_id=frame_id)
                add_text(elements, step_id, "seg-c", x + 212, y + 129, "警报", custom, 11, "#2383ff", frame_id=frame_id)
                start_y = y + 172
            else:
                start_y = y + 128
            for i, label in enumerate(labels[:5]):
                yy = start_y + i * 68
                add_box(elements, step_id, f"list-card-{i}", x + 30, yy, 240, 54, custom, frame_id=frame_id, stroke="#e5e7eb", fill="#ffffff")
                add_text(elements, step_id, f"list-title-{i}", x + 46, yy + 10, compact_label(label, 24), custom, 12, "#334155", frame_id=frame_id)
                add_text(elements, step_id, f"list-sub-{i}", x + 46, yy + 32, "—", custom, 11, "#94a3b8", frame_id=frame_id)
                add_text(elements, step_id, f"list-arrow-{i}", x + 246, yy + 18, "›", custom, 13, "#94a3b8", frame_id=frame_id)
    add_line_element(elements, step_id, "bottom-line", x + 30, y + 520, 240, 0, custom, frame_id=frame_id)
    add_text(elements, step_id, "trace", x + 36, y + 534, clean_snippet(" / ".join(str(item) for item in step.get("prd_sections", [])[-2:]), 32), custom, 10, "#94a3b8", frame_id=frame_id)


def draw_web_story_frame(elements: list[dict[str, object]], step: dict[str, object], x: int, y: int, frame_id: str, order: int) -> None:
    step_id = str(step["id"])
    custom = base_custom(step)
    custom["board_id"] = str(step.get("board_id") or "")
    custom["frame_id"] = frame_id
    title = clean_snippet(str(step.get("title") or "界面"), 34)
    labels = key_copy_for(step)
    while len(labels) < 6:
        labels.append(title)
    elements.append(storyboard_frame_element(frame_id, x, y, 560, 360, str(step.get("frame_name") or title), custom, order))
    add_box(elements, step_id, "web-shell", x + 10, y + 10, 540, 330, custom, frame_id=frame_id, stroke="#cbd5e1", fill="#ffffff", stroke_width=2)
    add_box(elements, step_id, "web-top", x + 10, y + 10, 540, 42, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
    add_text(elements, step_id, "web-title", x + 32, y + 22, compact_label(labels[0], 36), custom, 14, "#334155", frame_id=frame_id)
    add_box(elements, step_id, "web-side", x + 10, y + 52, 128, 288, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#f8fafc")
    for i, label in enumerate(labels[:5]):
        add_text(elements, step_id, f"web-nav-{i}", x + 28, y + 76 + i * 38, compact_label(label, 12), custom, 11, "#64748b", frame_id=frame_id)
    for i, label in enumerate(labels[1:4]):
        add_box(elements, step_id, f"web-card-{i}", x + 164 + i * 120, y + 82, 94, 74, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
        add_text(elements, step_id, f"web-card-label-{i}", x + 174 + i * 120, y + 106, compact_label(label, 10), custom, 11, "#334155", frame_id=frame_id)
    add_box(elements, step_id, "web-table", x + 164, y + 188, 340, 104, custom, frame_id=frame_id, stroke="#e2e8f0", fill="#ffffff")
    for i in range(3):
        add_line_element(elements, step_id, f"web-row-{i}", x + 164, y + 214 + i * 26, 340, 0, custom, frame_id=frame_id)


def element_bounds_for(elements: list[dict[str, object]]) -> dict[str, float]:
    boxes: list[tuple[float, float, float, float]] = []
    for element in elements:
        try:
            ex = float(element.get("x") or 0)
            ey = float(element.get("y") or 0)
            ew = float(element.get("width") or 0)
            eh = float(element.get("height") or 0)
        except (TypeError, ValueError):
            continue
        boxes.append((ex, ey, ex + max(ew, 1), ey + max(eh, 1)))
    if not boxes:
        return {"min_x": 0, "min_y": 0, "max_x": 1, "max_y": 1}
    return {
        "min_x": min(item[0] for item in boxes),
        "min_y": min(item[1] for item in boxes),
        "max_x": max(item[2] for item in boxes),
        "max_y": max(item[3] for item in boxes),
    }


def draw_diagram_story_frame(elements: list[dict[str, object]], step: dict[str, object], x: int, y: int, frame_id: str, order: int) -> None:
    step_id = str(step["id"])
    custom = base_custom(step)
    custom["board_id"] = str(step.get("board_id") or "")
    custom["frame_id"] = frame_id
    title = clean_snippet(str(step.get("title") or "Frame"), 42)
    elements.append(storyboard_frame_element(frame_id, x, y, 620, 430, str(step.get("frame_name") or title), custom, order))

    scene_type = str(step.get("scene_type") or "flow")
    builder = SCENE_BUILDERS.get(scene_type, create_flow_scene)
    local_elements = builder(step)
    bounds = element_bounds_for(local_elements)
    dx = x + 28 - bounds["min_x"]
    dy = y + 44 - bounds["min_y"]
    max_w = max(bounds["max_x"] - bounds["min_x"], 1)
    max_h = max(bounds["max_y"] - bounds["min_y"], 1)
    scale = min(560 / max_w, 330 / max_h, 1)
    for original in local_elements:
        element = json.loads(json.dumps(original))
        element["x"] = (float(element.get("x") or 0) - bounds["min_x"]) * scale + x + 28
        element["y"] = (float(element.get("y") or 0) - bounds["min_y"]) * scale + y + 44
        element["width"] = float(element.get("width") or 0) * scale
        element["height"] = float(element.get("height") or 0) * scale
        if isinstance(element.get("points"), list) and scale != 1:
            element["points"] = [[float(point[0]) * scale, float(point[1]) * scale] for point in element.get("points", []) if isinstance(point, list) and len(point) >= 2]
        element["frameId"] = frame_id
        custom_data = element.get("customData") if isinstance(element.get("customData"), dict) else {}
        custom_data.update({"board_id": custom["board_id"], "frame_id": frame_id})
        element["customData"] = custom_data
        elements.append(element)


def create_storyboard_board(board: dict[str, object], steps: list[dict[str, object]]) -> dict[str, object]:
    elements: list[dict[str, object]] = []
    board_id = str(board.get("id") or "board")
    title = str(board.get("title") or "Storyboard")
    board_custom = base_custom(steps[0]) if steps else {"step_id": board_id, "group_id": board_id, "prd_section": title}
    board_custom["board_id"] = board_id
    add_text(elements, board_id, "title", 30, 12, title, board_custom, 24, "#1f2937")
    mobile_like = sum(1 for step in steps if str(step.get("platform") or "") == "mobile")
    use_mobile_grid = mobile_like >= max(1, len(steps) - mobile_like)
    frame_w = 360 if use_mobile_grid else 680
    frame_h = 650 if mobile_like else 430
    columns = 4 if use_mobile_grid else 2
    for index, step in enumerate(steps):
        col = index % columns
        row = index // columns
        x = 30 + col * frame_w
        y = 70 + row * frame_h
        frame_id = str(step.get("frame_id") or element_id(str(step["id"]), "frame"))
        scene_type = str(step.get("scene_type") or "")
        showcase_diagram = bool(step.get("is_showcase_sample")) and scene_type in {"flow", "state_matrix", "overlay", "decision_branch", "list_table"}
        if showcase_diagram:
            draw_diagram_story_frame(elements, step, x, y, frame_id, index + 1)
        elif str(step.get("platform") or "") == "mobile":
            draw_mobile_story_frame(elements, step, x, y, frame_id, index + 1)
        else:
            draw_web_story_frame(elements, step, x, y, frame_id, index + 1)
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "Finn ProtoPilot Excalidraw Storyboard",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None, "currentItemFontFamily": EXCALIDRAW_TEXT_FONT_FAMILY},
        "files": {},
    }


def render_svg_element(el: dict[str, object]) -> str:
    element_type = str(el.get("type") or "rectangle")
    x = float(el.get("x") or 0)
    y = float(el.get("y") or 0)
    width = max(float(el.get("width") or 0), 1)
    height = max(float(el.get("height") or 0), 1)
    stroke = html_escape(el.get("strokeColor") or "#1f2937")
    fill_value = str(el.get("backgroundColor") or "transparent")
    fill = html_escape(fill_value) if fill_value != "transparent" else "none"
    sw = float(el.get("strokeWidth") or 1.5)
    opacity = float(el.get("opacity") or 100) / 100
    opacity_attr = f' opacity="{opacity:.2f}"' if opacity < 1 else ""
    if element_type == "text":
        font_size = float(el.get("fontSize") or 20)
        lines = str(el.get("text") or "").split("\n")
        tspans = "".join(
            f'<tspan x="{x:g}" dy="{0 if index == 0 else font_size * 1.25:g}">{html_escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        return f'<text x="{x:g}" y="{y + font_size:g}" fill="{stroke}" font-family="Segoe UI, PingFang SC, Microsoft YaHei, sans-serif" font-size="{font_size:g}"{opacity_attr}>{tspans}</text>'
    if element_type == "ellipse":
        return f'<ellipse cx="{x + width / 2:g}" cy="{y + height / 2:g}" rx="{width / 2:g}" ry="{height / 2:g}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:g}"{opacity_attr}/>'
    if element_type == "diamond":
        points = f"{x + width / 2:g},{y:g} {x + width:g},{y + height / 2:g} {x + width / 2:g},{y + height:g} {x:g},{y + height / 2:g}"
        return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:g}"{opacity_attr}/>'
    if element_type in {"arrow", "line"}:
        points = el.get("points") if isinstance(el.get("points"), list) else [[0, 0], [width, height]]
        d = " ".join(
            f"{'M' if index == 0 else 'L'} {x + float(point[0] or 0):g} {y + float(point[1] or 0):g}"
            for index, point in enumerate(points)
            if isinstance(point, list) and len(point) >= 2
        )
        marker = ' marker-end="url(#proto-arrow)"' if element_type == "arrow" else ""
        return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw:g}" stroke-linecap="round" stroke-linejoin="round"{marker}{opacity_attr}/>'
    rx = min(14, max(4, min(width, height) / 8))
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{rx:g}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:g}"{opacity_attr}/>'


def scene_elements_for_frame(scene: dict[str, object], frame_id: str | None = None) -> list[dict[str, object]]:
    elements = [item for item in scene.get("elements", []) if isinstance(item, dict) and not item.get("isDeleted")]
    if not frame_id:
        return elements
    frame = next((item for item in elements if item.get("id") == frame_id and item.get("type") == "frame"), None)
    if not frame:
        return []
    fx = float(frame.get("x") or 0)
    fy = float(frame.get("y") or 0)
    fw = float(frame.get("width") or 0)
    fh = float(frame.get("height") or 0)
    result = [frame]
    for item in elements:
        if item is frame:
            continue
        if item.get("frameId") == frame_id:
            result.append(item)
            continue
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("width") or 0)
        h = float(item.get("height") or 0)
        if fx <= x <= fx + fw and fy <= y <= fy + fh and x + w <= fx + fw + 4 and y + h <= fy + fh + 4:
            result.append(item)
    return result


def is_preview_aux_element(element: dict[str, object]) -> bool:
    element_id_value = str(element.get("id") or "")
    if element.get("type") == "text" and element_id_value.endswith("-trace"):
        return True
    return False


def frame_ids_in_scene(scene: dict[str, object]) -> set[str]:
    return {
        str(element.get("id"))
        for element in scene.get("elements", [])
        if isinstance(element, dict) and element.get("type") == "frame" and element.get("id")
    }


def elements_for_frame_ids(scene: dict[str, object], frame_ids: set[str]) -> list[dict[str, object]]:
    elements = [item for item in scene.get("elements", []) if isinstance(item, dict) and not item.get("isDeleted")]
    return [
        element
        for element in elements
        if str(element.get("id") or "") in frame_ids or str(element.get("frameId") or "") in frame_ids
    ]


def append_missing_board_frames(existing_scene: dict[str, object], generated_scene: dict[str, object], missing_frame_ids: set[str]) -> dict[str, object]:
    merged = json.loads(json.dumps(existing_scene))
    if not isinstance(merged.get("elements"), list):
        merged["elements"] = []
    existing_ids = {str(element.get("id")) for element in merged["elements"] if isinstance(element, dict) and element.get("id")}
    additions: list[dict[str, object]] = []
    for element in elements_for_frame_ids(generated_scene, missing_frame_ids):
        element_id_value = str(element.get("id") or "")
        if element_id_value and element_id_value not in existing_ids:
            additions.append(json.loads(json.dumps(element)))
            existing_ids.add(element_id_value)
    merged["type"] = "excalidraw"
    merged["version"] = max(int(merged.get("version") or 2), 2)
    merged["source"] = merged.get("source") or "Finn ProtoPilot Excalidraw Storyboard"
    merged["elements"].extend(additions)
    if not isinstance(merged.get("appState"), dict):
        merged["appState"] = generated_scene.get("appState", {})
    if not isinstance(merged.get("files"), dict):
        merged["files"] = generated_scene.get("files", {})
    return merged


def render_scene_svg(scene: dict[str, object], frame_id: str | None = None) -> str:
    elements = scene_elements_for_frame(scene, frame_id)
    if not elements:
        return '<div class="proto-excalidraw-placeholder">这个 scene 还没有内容</div>'
    render_elements = [element for element in elements if not is_preview_aux_element(element)]
    frame = next((element for element in elements if frame_id and element.get("type") == "frame" and element.get("id") == frame_id), None)
    bounds = {"min_x": float("inf"), "min_y": float("inf"), "max_x": float("-inf"), "max_y": float("-inf")}
    if frame:
        bounds = {
            "min_x": float(frame.get("x") or 0),
            "min_y": float(frame.get("y") or 0),
            "max_x": float(frame.get("x") or 0) + max(float(frame.get("width") or 0), 1),
            "max_y": float(frame.get("y") or 0) + max(float(frame.get("height") or 0), 1),
        }
    for el in ([] if frame else render_elements):
        x = float(el.get("x") or 0)
        y = float(el.get("y") or 0)
        width = max(float(el.get("width") or 0), 1)
        height = max(float(el.get("height") or 0), 1)
        bounds["min_x"] = min(bounds["min_x"], x)
        bounds["min_y"] = min(bounds["min_y"], y)
        bounds["max_x"] = max(bounds["max_x"], x + width)
        bounds["max_y"] = max(bounds["max_y"], y + height)
    pad = 18 if frame else 32
    view_x = bounds["min_x"] - pad
    view_y = bounds["min_y"] - pad
    view_w = max(bounds["max_x"] - bounds["min_x"] + pad * 2, 1)
    view_h = max(bounds["max_y"] - bounds["min_y"] + pad * 2, 1)
    defs = '<defs><marker id="proto-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#1f2937"/></marker></defs>'
    body = "".join(render_svg_element(el) for el in render_elements)
    return f'<svg viewBox="{view_x:g} {view_y:g} {view_w:g} {view_h:g}" role="img" aria-label="Excalidraw scene preview">{defs}{body}</svg>'


def init_scenes(demand: Path) -> dict[str, object]:
    p = paths(demand)
    if not p["plan"].is_file():
        fail(f"Missing prototype-plan.json: {p['plan']}")
    plan = load_json(p["plan"])
    existing = load_json(p["manifest"]) if p["manifest"].is_file() else {}
    p["scenes"].mkdir(parents=True, exist_ok=True)
    p["boards"].mkdir(parents=True, exist_ok=True)
    p["snapshots"].mkdir(parents=True, exist_ok=True)
    scenes: list[dict[str, object]] = []
    boards_manifest: list[dict[str, object]] = []
    created: list[str] = []
    preserved: list[str] = []
    steps_by_id = {str(step["id"]): step for step in ordered_steps(plan)}
    plan_boards = [board for board in plan.get("boards", []) if isinstance(board, dict)]
    if plan_boards:
        for board in plan_boards:
            board_id = str(board.get("id") or stable_id("board", str(board.get("title") or "board"), "board"))
            rel = str(board.get("file") or f"{EXCAL_DIR}/{BOARDS_DIR}/{board_id}.excalidraw")
            board_path = demand / rel
            board_steps = [steps_by_id[str(step_id)] for step_id in board.get("step_ids", []) if str(step_id) in steps_by_id]
            required_frames = {str(step.get("frame_id") or "") for step in board_steps if step.get("frame_id")}
            missing_frames: set[str] = set()
            invalid_existing_board = False
            if board_path.exists() and required_frames:
                try:
                    existing_scene = load_json(board_path)
                    existing_frames = frame_ids_in_scene(existing_scene)
                    missing_frames = required_frames - existing_frames
                except Exception:
                    invalid_existing_board = True
            if not board_path.exists() or invalid_existing_board:
                write_json(board_path, create_storyboard_board(board, board_steps))
                created.append(board_id)
            elif missing_frames:
                generated_scene = create_storyboard_board(board, board_steps)
                write_json(board_path, append_missing_board_frames(load_json(board_path), generated_scene, missing_frames))
                preserved.append(board_id)
                created.extend(sorted(missing_frames))
            else:
                preserved.append(board_id)
            board_hash = file_hash(board_path)
            boards_manifest.append(
                {
                    "board_id": board_id,
                    "title": board.get("title", board_id),
                    "file": rel,
                    "frame_count": len(board_steps),
                    "hash": board_hash,
                    "updated_at": utc_now(),
                }
            )
            for step in board_steps:
                step_id = str(step["id"])
                scenes.append(
                    {
                        "step_id": step_id,
                        "group_id": step.get("group_id", ""),
                        "title": step.get("title", step_id),
                        "scene_type": step.get("scene_type") or "mobile_wireframe",
                        "scene_type_reason": step.get("scene_type_reason", ""),
                        "source_evidence": step.get("source_evidence", []),
                        "prd_sections": step.get("prd_sections", []),
                        "file": rel,
                        "board_id": board_id,
                        "frame_id": step.get("frame_id", ""),
                        "frame_name": step.get("frame_name", step.get("title", step_id)),
                        "frame_order": step.get("frame_order", 0),
                        "screen_kind": step.get("screen_kind", ""),
                        "surface_kind": step.get("surface_kind", ""),
                        "platform": step.get("platform", ""),
                        "storyboard_brief": step.get("storyboard_brief", {}),
                        "status": "ready",
                        "hash": board_hash,
                        "updated_at": utc_now(),
                    }
                )
    else:
        for index, step in enumerate(ordered_steps(plan)):
            step_id = str(step["id"])
            rel = f"{EXCAL_DIR}/{SCENES_DIR}/{step_id}.excalidraw"
            scene_path = demand / rel
            if not scene_path.exists():
                write_json(scene_path, create_excalidraw_scene(step, index))
                created.append(step_id)
            else:
                preserved.append(step_id)
            scenes.append(
                {
                    "step_id": step_id,
                    "group_id": step.get("group_id", ""),
                    "title": step.get("title", step_id),
                    "scene_type": step.get("scene_type") or "flow",
                    "scene_type_reason": step.get("scene_type_reason", ""),
                    "source_evidence": step.get("source_evidence", []),
                    "prd_sections": step.get("prd_sections", []),
                    "surface_kind": step.get("surface_kind", ""),
                    "platform": step.get("platform", ""),
                    "storyboard_brief": step.get("storyboard_brief", {}),
                    "file": rel,
                    "status": "ready",
                    "hash": file_hash(scene_path),
                    "updated_at": utc_now(),
                }
            )
    manifest = {
        "schema_version": 2 if plan_boards else 1,
        "kind": "finn-protopilot-sketch-manifest",
        "created_at": (existing.get("created_at") if isinstance(existing, dict) else None) or utc_now(),
        "updated_at": utc_now(),
        "source": plan.get("source", {}) if isinstance(plan, dict) else {},
        "boards": boards_manifest,
        "scenes": scenes,
    }
    write_json(p["manifest"], manifest)
    return {"ok": True, "manifest": str(p["manifest"]), "created": created, "preserved": preserved}


def render_generated_area(demand: Path, manifest: dict[str, object], plan: dict[str, object]) -> str:
    scene_by_step = {str(item["step_id"]): item for item in manifest.get("scenes", []) if isinstance(item, dict) and item.get("step_id")}
    step_by_id = {str(step["id"]): step for step in plan.get("steps", []) if isinstance(step, dict) and step.get("id")}
    parts: list[str] = [
        '<div class="proto-area-label"><span class="proto-generated-note">Generated area - Excalidraw render</span></div>',
    ]
    display_sections: list[dict[str, object]] = []
    mounted_steps: set[str] = set()
    for group in plan.get("groups", []):
        if not isinstance(group, dict):
            continue
        step_ids = [str(step_id) for step_id in group.get("step_ids", []) if str(step_id) in scene_by_step]
        step_ids = [step_id for step_id in step_ids if step_id not in mounted_steps]
        if step_ids:
            mounted_steps.update(step_ids)
            display_sections.append({"id": str(group.get("id") or ""), "title": str(group.get("title") or "Scenes"), "step_ids": step_ids})
    remaining_steps = [
        str(step.get("id"))
        for step in plan.get("steps", [])
        if isinstance(step, dict) and step.get("id") and str(step.get("id")) in scene_by_step and str(step.get("id")) not in mounted_steps
    ]
    if remaining_steps:
        display_sections.append({"id": "group-ungrouped-scenes", "title": "Scenes", "step_ids": remaining_steps})
    if not display_sections:
        for board in plan.get("boards", []) if isinstance(plan.get("boards"), list) else []:
            if not isinstance(board, dict):
                continue
            step_ids = [str(step_id) for step_id in board.get("step_ids", []) if str(step_id) in scene_by_step]
            if not step_ids:
                continue
            title = str(board.get("title") or board.get("id") or "Storyboard")
            display_sections.append({"id": str(board.get("id") or title), "title": title, "step_ids": step_ids})
    display_index = 0
    for section in display_sections:
        step_ids = [str(step_id) for step_id in section.get("step_ids", [])]
        parts.append(f'<div class="section-divider" data-proto-id="{html_escape(section.get("id", ""))}">{html_escape(str(section.get("title", "Scenes")))}</div>')
        parts.append('<section class="journey-row">')
        for step_id in step_ids:
            display_index += 1
            scene_item = scene_by_step.get(step_id)
            step = step_by_id.get(step_id, {"title": step_id})
            if not scene_item:
                continue
            scene_src = str(scene_item.get("file"))
            scene_type = str(scene_item.get("scene_type") or step.get("scene_type") or "wireframe")
            title = str(step.get("title") or scene_item.get("title") or step_id)
            frame_id = str(scene_item.get("frame_id") or "")
            board_id = str(scene_item.get("board_id") or "")
            platform = str(step.get("platform") or scene_item.get("platform") or "")
            preview_kind = "mobile" if platform == "mobile" else "web" if platform == "web" else "diagram"
            scene_path, scene_src_normalized = resolve_excalidraw_ref(demand, scene_src)
            scene_src = scene_src_normalized
            preview = render_scene_svg(load_json(scene_path), frame_id=frame_id or None) if scene_path and scene_path.is_file() else '<div class="proto-excalidraw-placeholder">Scene 文件缺失</div>'
            if not (scene_path and scene_path.is_file()):
                preview = '<div class="proto-excalidraw-placeholder">Scene 文件缺失</div>'
            parts.append(
                f'''  <article class="journey-step" id="{html_escape(step_id)}" data-proto-id="{html_escape(step_id)}" data-proto-label="{html_escape(title)}">
    <div class="step-header"><span class="step-number">{display_index}</span><span class="step-title">{html_escape(title)}</span></div>
    <div class="proto-excalidraw-card" data-scene-src="{html_escape(scene_src)}" data-step-id="{html_escape(step_id)}" data-scene-title="{html_escape(title)}" data-scene-type="{html_escape(scene_type)}" data-board-id="{html_escape(board_id)}" data-frame-id="{html_escape(frame_id)}" data-platform="{html_escape(platform)}" data-preview-kind="{html_escape(preview_kind)}">
      <div class="proto-excalidraw-preview" data-render-state="fallback">{preview}</div>
    </div>
  </article>'''
            )
        parts.append("</section>")
    return "\n".join(parts)


def inject_generated_area(index_path: Path, fragment_text: str) -> None:
    html = index_path.read_text(encoding="utf-8")
    if START_MARKER not in html or END_MARKER not in html:
        fail(f"Generated-area markers missing in {index_path}")
    updated = re.sub(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        START_MARKER + "\n" + fragment_text.strip() + "\n" + END_MARKER,
        html,
        flags=re.S,
    )
    index_path.write_text(updated, encoding="utf-8")


def frame_mapping_from_steps(steps: list[object]) -> dict[str, tuple[str, str, str]]:
    mapping: dict[str, tuple[str, str, str]] = {}
    for step in steps:
        if not isinstance(step, dict) or not step.get("id"):
            continue
        mapping[str(step.get("id"))] = (
            str(step.get("board_id") or ""),
            str(step.get("frame_id") or ""),
            str(step.get("board_file") or step.get("file") or ""),
        )
    return mapping


def frame_mapping_from_manifest(scenes: list[object]) -> dict[str, tuple[str, str, str]]:
    mapping: dict[str, tuple[str, str, str]] = {}
    for item in scenes:
        if not isinstance(item, dict) or not item.get("step_id"):
            continue
        mapping[str(item.get("step_id"))] = (
            str(item.get("board_id") or ""),
            str(item.get("frame_id") or ""),
            str(item.get("file") or ""),
        )
    return mapping


def build_scenes(demand: Path) -> dict[str, object]:
    p = paths(demand)
    if not p["plan"].is_file():
        fail(f"Missing prototype-plan.json: {p['plan']}")
    plan = load_json(p["plan"])
    if not p["manifest"].is_file():
        init_scenes(demand)
    manifest = load_json(p["manifest"])
    plan_step_ids = {str(step.get("id")) for step in plan.get("steps", []) if isinstance(step, dict) and step.get("id")}
    manifest_step_ids = {str(item.get("step_id")) for item in manifest.get("scenes", []) if isinstance(item, dict) and item.get("step_id")}
    plan_frame_map = frame_mapping_from_steps(plan.get("steps", []) if isinstance(plan.get("steps"), list) else [])
    manifest_frame_map = frame_mapping_from_manifest(manifest.get("scenes", []) if isinstance(manifest.get("scenes"), list) else [])
    plan_uses_boards = bool(plan.get("boards")) or str(plan.get("generation_mode") or "") == "excalidraw_storyboard_boards"
    manifest_has_frames = any(str(item.get("frame_id") or "") for item in manifest.get("scenes", []) if isinstance(item, dict))
    if plan_step_ids != manifest_step_ids or (plan_uses_boards and (int(manifest.get("schema_version") or 1) < 2 or not manifest_has_frames or plan_frame_map != manifest_frame_map)):
        init_scenes(demand)
        manifest = load_json(p["manifest"])
    fragment = render_generated_area(demand, manifest, plan)
    p["fragment"].write_text(fragment + "\n", encoding="utf-8")
    if p["index"].is_file():
        prd = find_prd(demand)
        copy_shell_assets(demand)
        render_shell(demand, prd, read_prd_title(prd), fragment)
    return {"ok": True, "fragment": str(p["fragment"]), "index_injected": p["index"].is_file()}


def copy_shell_assets(demand: Path) -> None:
    root = skill_root()
    for name in SHELL_ASSETS:
        shutil.copy2(root / name, demand / name)


def render_shell(demand: Path, prd: Path, title: str, generated_area: str = "") -> None:
    template = (skill_root() / "templates" / "sketch" / "prototype-shell.html").read_text(encoding="utf-8")
    prd_src = browser_relative_path(prd, demand)
    html = (
        template.replace("{{title}}", html_escape(title))
        .replace("{{lang}}", "zh-CN")
        .replace("{{prd_viewer_src}}", html_escape(prd_src))
        .replace("{{design_context}}", "")
        .replace("{{generated_area}}", generated_area)
    )
    (demand / "index.html").write_text(html, encoding="utf-8")


def has_suspicious_text(text: str) -> bool:
    if not text:
        return False
    mojibake_terms = {"\ufffd", "??", "Ã", "锛", "鈥", "鐨", "鏄", "绛", "涓", "忚", "", "€"}
    return any(term in text for term in mojibake_terms)


def scene_check(demand: Path) -> dict[str, object]:
    p = paths(demand)
    failures: list[str] = []
    warnings: list[str] = []
    if not p["manifest"].is_file():
        return {"ok": False, "failures": [f"Missing manifest: {p['manifest']}"], "warnings": []}
    manifest = load_json(p["manifest"])
    plan = load_json(p["plan"]) if p["plan"].is_file() else {"steps": []}
    plan_ids = {str(step.get("id")) for step in plan.get("steps", []) if isinstance(step, dict)}
    scene_ids: set[str] = set()
    for item in manifest.get("scenes", []):
        if not isinstance(item, dict):
            failures.append("Manifest scene entry is not an object.")
            continue
        step_id = str(item.get("step_id") or "")
        scene_ids.add(step_id)
        scene_type = str(item.get("scene_type") or "")
        if scene_type and scene_type not in EXCALIDRAW_SCENE_TYPES:
            failures.append(f"{step_id}: unknown scene_type {scene_type}.")
        rel = str(item.get("file") or "")
        scene_path, normalized_rel = resolve_excalidraw_ref(demand, rel)
        valid_prefix = normalized_rel.startswith(f"{EXCAL_DIR}/{SCENES_DIR}/") or normalized_rel.startswith(f"{EXCAL_DIR}/{BOARDS_DIR}/")
        if not valid_prefix or not normalized_rel.endswith(".excalidraw") or scene_path is None:
            failures.append(f"{step_id}: scene file must be under {EXCAL_DIR}/{SCENES_DIR}/ or {EXCAL_DIR}/{BOARDS_DIR}/ and end with .excalidraw.")
            continue
        if not scene_path.is_file():
            failures.append(f"{step_id}: missing scene file {normalized_rel}.")
            continue
        try:
            scene = load_json(scene_path)
        except Exception as error:
            failures.append(f"{step_id}: invalid scene JSON: {error}")
            continue
        if not isinstance(scene, dict) or scene.get("type") != "excalidraw":
            failures.append(f"{step_id}: scene type must be excalidraw.")
        elements = scene.get("elements")
        if not isinstance(elements, list):
            failures.append(f"{step_id}: scene elements must be an array.")
            elements = []
        frame_id = str(item.get("frame_id") or "")
        checked_elements = scene_elements_for_frame(scene, frame_id) if frame_id else elements
        if not checked_elements:
            failures.append(f"{step_id}: scene must contain at least one element.")
        if frame_id:
            if not any(isinstance(element, dict) and element.get("type") == "frame" and element.get("id") == frame_id for element in elements):
                failures.append(f"{step_id}: frame_id {frame_id} is missing from board.")
            elif len(checked_elements) < 8:
                failures.append(f"{step_id}: frame {frame_id} is too sparse.")
        for element in checked_elements:
            if not isinstance(element, dict):
                continue
            custom = element.get("customData")
            if not isinstance(custom, dict) or not custom.get("step_id") or not custom.get("group_id") or not custom.get("prd_section"):
                warnings.append(f"{step_id}: element {element.get('id', '<unknown>')} lacks traceable customData.")
                break
            if frame_id and (not custom.get("board_id") or not custom.get("frame_id")):
                warnings.append(f"{step_id}: element {element.get('id', '<unknown>')} lacks board/frame customData.")
                break
        for element in checked_elements:
            if isinstance(element, dict) and element.get("type") == "text" and has_suspicious_text(str(element.get("text") or "")):
                warnings.append(f"{step_id}: suspicious text encoding in element {element.get('id', '<unknown>')}.")
                break
        declared_hash = item.get("hash")
        actual_hash = file_hash(scene_path)
        if declared_hash != actual_hash:
            warnings.append(f"{step_id}: manifest hash is stale; run init-scenes.")
    missing = sorted(plan_ids - scene_ids)
    extra = sorted(scene_ids - plan_ids)
    if missing:
        failures.append("Plan steps missing scenes: " + ", ".join(missing[:12]))
    if extra:
        warnings.append("Manifest contains scene ids not in plan: " + ", ".join(extra[:12]))
    if str(plan.get("generation_mode") or "") == "excalidraw_storyboard_boards":
        plan_frame_map = frame_mapping_from_steps(plan.get("steps", []) if isinstance(plan.get("steps"), list) else [])
        manifest_frame_map = frame_mapping_from_manifest(manifest.get("scenes", []) if isinstance(manifest.get("scenes"), list) else [])
        drift = sorted(step_id for step_id, expected in plan_frame_map.items() if manifest_frame_map.get(step_id) != expected)
        if drift:
            failures.append("Manifest board/frame mapping differs from plan: " + ", ".join(drift[:12]))
    has_board_manifest = any(isinstance(item, dict) and str(item.get("frame_id") or "") for item in manifest.get("scenes", []))
    if p["scenes"].is_dir():
        referenced_files = {str(item.get("file") or "") for item in manifest.get("scenes", []) if isinstance(item, dict)}
        orphan_files = sorted(
            relative_to(path, demand)
            for path in p["scenes"].glob("*.excalidraw")
            if relative_to(path, demand) not in referenced_files
        )
        if orphan_files:
            prefix = "Legacy scene files remain in board/frame output: " if has_board_manifest else "Scene files not referenced by manifest: "
            warnings.append(prefix + ", ".join(orphan_files[:12]))
    if p["boards"].is_dir():
        referenced_files = {str(item.get("file") or "") for item in manifest.get("scenes", []) if isinstance(item, dict)}
        orphan_files = sorted(
            relative_to(path, demand)
            for path in p["boards"].glob("*.excalidraw")
            if relative_to(path, demand) not in referenced_files
        )
        if orphan_files:
            warnings.append("Board files not referenced by manifest: " + ", ".join(orphan_files[:12]))
    return {"ok": not failures, "failures": failures, "warnings": warnings, "manifest": str(p["manifest"])}


def scene_texts(scene: dict[str, object], frame_id: str | None = None) -> list[str]:
    return [
        str(element.get("text") or "")
        for element in scene_elements_for_frame(scene, frame_id)
        if isinstance(element, dict) and element.get("type") == "text" and not element.get("isDeleted")
    ]


def text_matches_evidence(texts: list[str], step: dict[str, object]) -> int:
    haystack = " ".join(texts)
    evidence = [str(item) for item in step.get("source_evidence", []) if item] if isinstance(step.get("source_evidence"), list) else []
    entities = [str(item) for item in step.get("business_entities", []) if item] if isinstance(step.get("business_entities"), list) else []
    brief = brief_for_step(step)
    brief_copy = [str(item) for item in brief.get("visible_copy", []) if item] if isinstance(brief.get("visible_copy"), list) else []
    brief_data = [str(item) for item in brief.get("data_examples", []) if item] if isinstance(brief.get("data_examples"), list) else []
    title = clean_snippet(str(step.get("title") or ""), 64)
    group_title = clean_snippet(str(step.get("group_title") or ""), 64)
    values = unique_preserve([*evidence, *entities, *brief_copy, *brief_data], 16)
    matches = 0
    for value in values:
        label = clean_snippet(value, 32)
        if label in {title, group_title}:
            continue
        if len(label) >= 2 and label in haystack:
            matches += 1
    return matches


def evidence_match_detail(texts: list[str], step: dict[str, object]) -> dict[str, int]:
    haystack = " ".join(texts)
    title = clean_snippet(str(step.get("title") or ""), 64)
    evidence = [str(item) for item in step.get("source_evidence", []) if item] if isinstance(step.get("source_evidence"), list) else []
    entities = [str(item) for item in step.get("business_entities", []) if item] if isinstance(step.get("business_entities"), list) else []
    states = [str(item) for item in step.get("states_or_rules", []) if item] if isinstance(step.get("states_or_rules"), list) else []
    brief = brief_for_step(step)
    brief_values = [str(item) for item in brief.get("visible_copy", []) if item] if isinstance(brief.get("visible_copy"), list) else []
    body_hits = 0
    entity_hits = 0
    state_hits = 0
    for value in evidence:
        label = clean_snippet(value, 32)
        if len(label) >= 2 and label != title and label in haystack:
            body_hits += 1
    for value in brief_values:
        label = clean_snippet(value, 32)
        if len(label) >= 2 and label != title and label in haystack:
            body_hits += 1
    for value in entities:
        label = clean_snippet(value, 24)
        if len(label) >= 2 and label in haystack:
            entity_hits += 1
    for value in states:
        label = clean_snippet(value, 28)
        if len(label) >= 2 and label in haystack:
            state_hits += 1
    return {"body": body_hits, "entity": entity_hits, "state": state_hits}


def layout_signature(elements: list[dict[str, object]]) -> str:
    raw_boxes: list[tuple[str, float, float, float, float]] = []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") in {"text", "frame"}:
            continue
        try:
            raw_boxes.append(
                (
                    str(element.get("type") or ""),
                    float(element.get("x") or 0),
                    float(element.get("y") or 0),
                    float(element.get("width") or 0),
                    float(element.get("height") or 0),
                )
            )
        except (TypeError, ValueError):
            continue
    if not raw_boxes:
        return ""
    min_x = min(item[1] for item in raw_boxes)
    min_y = min(item[2] for item in raw_boxes)
    boxes: list[str] = []
    for element_type, x, y, w, h in raw_boxes:
        x_key = round((x - min_x) / 24)
        y_key = round((y - min_y) / 24)
        w_key = round(w / 24)
        h_key = round(h / 24)
        boxes.append(f"{element_type}:{x_key}:{y_key}:{w_key}:{h_key}")
    return "|".join(boxes[:28])


def normalized_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


def is_template_text(value: str) -> bool:
    normalized = normalized_text(value)
    if not normalized:
        return False
    if normalized in NORMALIZED_TEMPLATE_TEXT_TERMS:
        return True
    return any(term and term in normalized for term in NORMALIZED_TEMPLATE_TEXT_TERMS if len(term) >= 6)


def story_brief_failures(step_id: str, step: dict[str, object]) -> list[str]:
    failures: list[str] = []
    brief = brief_for_step(step)
    if not isinstance(brief, dict) or not brief:
        return [f"{step_id}: missing storyboard_brief; real project frames need an authoring brief."]
    required = ["screen_role", "surface_archetype", "component_inventory", "visible_copy", "must_not_draw"]
    for field in required:
        if not brief.get(field):
            failures.append(f"{step_id}: storyboard_brief missing {field}.")
    visible = product_text_candidates(list(brief.get("visible_copy", [])) if isinstance(brief.get("visible_copy"), list) else [], 4)
    title = clean_snippet(str(step.get("title") or ""), 72)
    if len(visible) < 2 or all(clean_snippet(item, 72) == title for item in visible):
        failures.append(f"{step_id}: storyboard_brief visible_copy is too thin or only repeats the frame title.")
    bad_values = [
        str(item)
        for field in ["visible_copy", "source_evidence", "annotations"]
        for item in (brief.get(field, []) if isinstance(brief.get(field), list) else [])
        if is_non_product_text(str(item))
    ]
    if bad_values:
        failures.append(f"{step_id}: storyboard_brief contains non-product source text: {clean_snippet(bad_values[0], 48)}")
    return failures


def placeholder_text_ratio(texts: list[str]) -> float:
    if not texts:
        return 0
    ignored = {"12:30          5G ▮▮▮", "←"}
    visible = [text.strip() for text in texts if text.strip() and text.strip() not in ignored]
    if not visible:
        return 0
    placeholders = [text for text in visible if text in PLACEHOLDER_TEXT_TERMS - {"›"} or text == "—" or "<iframe" in text.lower()]
    return len(placeholders) / len(visible)


def element_type_count(elements: list[dict[str, object]], element_type: str) -> int:
    return sum(1 for element in elements if isinstance(element, dict) and element.get("type") == element_type and not element.get("isDeleted"))


def brief_implementation_failures(step_id: str, step: dict[str, object], elements: list[dict[str, object]], texts: list[str]) -> list[str]:
    failures: list[str] = []
    brief = brief_for_step(step)
    if not brief:
        return failures
    haystack = " ".join(texts)
    visible = product_text_candidates(list(brief.get("visible_copy", [])) if isinstance(brief.get("visible_copy"), list) else [], 8)
    visible_hits = 0
    for value in visible:
        label = clean_snippet(str(value), 32)
        if len(label) >= 2 and label in haystack:
            visible_hits += 1
    if len(visible) >= 3 and visible_hits < 2:
        failures.append(f"{step_id}: board frame does not implement enough storyboard_brief visible_copy.")
    inventory = {normalized_text(str(item)) for item in (brief.get("component_inventory", []) if isinstance(brief.get("component_inventory"), list) else [])}
    rects = element_type_count(elements, "rectangle")
    lines = element_type_count(elements, "line") + element_type_count(elements, "arrow")
    if "phoneshell" in inventory and rects < 2:
        failures.append(f"{step_id}: storyboard_brief requests phone_shell but frame lacks phone-like structure.")
    if any(item in inventory for item in {"modalcard", "primaryaction", "secondaryaction"}) and rects < 3:
        failures.append(f"{step_id}: storyboard_brief requests modal/action components but frame lacks modal structure.")
    if any(item in inventory for item in {"settingsrows", "settingsrow", "listrows", "alertcards", "conversationrows"}) and rects < 2:
        failures.append(f"{step_id}: storyboard_brief requests row/list components but frame lacks repeated rows.")
    if "barchart" in inventory and rects < 8:
        failures.append(f"{step_id}: storyboard_brief requests a bar_chart but frame lacks chart structure.")
    if any(item in inventory for item in {"maparea", "addresstimeline"}) and rects < 2 and lines < 2:
        failures.append(f"{step_id}: storyboard_brief requests map/timeline content but frame lacks spatial structure.")
    return failures


def visual_grammar_failures(step_id: str, step: dict[str, object], elements: list[dict[str, object]], texts: list[str]) -> list[str]:
    failures: list[str] = []
    scene_type = str(step.get("scene_type") or "")
    surface_kind = str(step.get("surface_kind") or "")
    archetype = str(step.get("surface_archetype") or brief_for_step(step).get("surface_archetype") or "")
    has_product_archetype = archetype not in {"", "rule_annotation", "mobile_page", "state", "list", "settings", "detail", "modal"}
    if has_product_archetype:
        return failures
    arrows = element_type_count(elements, "arrow")
    diamonds = element_type_count(elements, "diamond")
    rects = element_type_count(elements, "rectangle")
    if scene_type == "decision_branch" and diamonds < 1 and arrows < 2:
        failures.append(f"{step_id}: decision_branch lacks visible branch grammar or a concrete UI surface.")
    if scene_type == "state_matrix" and rects < 6 and not any(text in " ".join(texts) for text in ["IDLE", "DRIVING", "ENDED", "空", "过期", "失败", "成功"]):
        failures.append(f"{step_id}: state_matrix lacks state comparison or state-transition content.")
    if scene_type == "flow" and arrows < 2 and surface_kind not in {"entry_or_flow", "page", "detail", "settings", "list", "overlay"}:
        failures.append(f"{step_id}: flow lacks enough path nodes/arrows or a concrete UI surface.")
    return failures


def quality_check(demand: Path, strict: bool = False) -> dict[str, object]:
    p = paths(demand)
    failures: list[str] = []
    warnings: list[str] = []
    if not p["plan"].is_file():
        return {"ok": False, "failures": [f"Missing plan: {p['plan']}"], "warnings": warnings}
    if not p["manifest"].is_file():
        return {"ok": False, "failures": [f"Missing manifest: {p['manifest']}"], "warnings": warnings}
    plan = load_json(p["plan"])
    manifest = load_json(p["manifest"])
    steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]
    scenes = [item for item in manifest.get("scenes", []) if isinstance(item, dict)]
    step_by_id = {str(step.get("id")): step for step in steps if step.get("id")}
    source = plan.get("source", {}) if isinstance(plan.get("source"), dict) else {}
    design_context = source.get("design_context", {}) if isinstance(source.get("design_context"), dict) else {}
    design_summary = str(design_context.get("summary") or "")
    if design_summary and has_suspicious_text(design_summary):
        warnings.append("Design context summary contains suspicious encoding; verify the design source was read correctly.")
    auto_draft_steps = []
    for step in steps:
        brief = step.get("storyboard_brief") if isinstance(step.get("storyboard_brief"), dict) else {}
        if str(step.get("storyboard_brief_status") or brief.get("status") or "") == "auto_draft":
            auto_draft_steps.append(step)
    if steps and len(auto_draft_steps) / len(steps) > 0.5:
        warnings.append("Most storyboard briefs are still auto_draft; review important frames before treating the sketch as final.")
    schema_version = int(plan.get("schema_version") or 1)
    if schema_version < 2:
        failures.append("prototype-plan.json is schema_version < 2; regenerate plan to use semantic section disposition.")
    has_frame_entries = any(str(item.get("frame_id") or "") for item in scenes)
    if strict and schema_version < PLAN_SCHEMA_VERSION:
        failures.append(f"prototype-plan.json is schema_version < {PLAN_SCHEMA_VERSION}; regenerate to use storyboard semantic specs and frame-level previews.")
    if strict and str(plan.get("generation_mode") or "") != "excalidraw_storyboard_boards":
        failures.append("prototype-plan.json generation_mode must be excalidraw_storyboard_boards.")
    if strict and not isinstance(plan.get("context_summary"), dict):
        failures.append("prototype-plan.json missing context_summary; PRD/design context was not summarized before storyboard authoring.")
    if strict and int(manifest.get("schema_version") or 1) < 2:
        failures.append("manifest.json schema_version must be >= 2 for board/frame output.")
    if strict and not manifest.get("boards"):
        failures.append("manifest.json has no storyboard boards.")
    if strict and scenes and not has_frame_entries:
        failures.append("Generated prototype has no Excalidraw frames; storyboard output should use board/frame entries, not one sparse scene per step.")
    if strict:
        for item in scenes:
            if not str(item.get("board_id") or "") or not str(item.get("frame_id") or ""):
                failures.append(f"{item.get('step_id')}: manifest scene entry must include board_id and frame_id.")
    if strict and len({str(item.get("file") or "") for item in scenes}) == len(scenes) and len(scenes) > 1:
        failures.append("Each step uses a separate scene file; real projects should group related frames into storyboard boards.")
    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    disposition = coverage.get("disposition", []) if isinstance(coverage.get("disposition"), list) else []
    if len(steps) >= 8 and not disposition:
        failures.append("Long PRD plan has no coverage.disposition; explanatory sections are probably being turned into scenes.")
    for step in steps:
        step_id = str(step.get("id") or "<unknown>")
        if str(step.get("kind") or "") != "prototype_step":
            failures.append(f"{step_id}: plan steps must be prototype_step only; non-prototype sections belong in coverage.disposition.")
        if not step.get("scene_type_reason"):
            failures.append(f"{step_id}: missing scene_type_reason.")
        evidence = step.get("source_evidence") if isinstance(step.get("source_evidence"), list) else []
        if len([item for item in evidence if str(item).strip()]) < 2:
            failures.append(f"{step_id}: source_evidence must contain at least two PRD-derived snippets.")
        if strict:
            if not step.get("platform") or str(step.get("platform")) not in {"mobile", "web"}:
                failures.append(f"{step_id}: missing concrete platform decision.")
            if not step.get("surface_id") or not step.get("surface_kind"):
                failures.append(f"{step_id}: missing surface_id/surface_kind.")
            if not step.get("frame_intent"):
                failures.append(f"{step_id}: missing frame_intent.")
            if not isinstance(step.get("semantic_frame_spec"), dict):
                failures.append(f"{step_id}: missing semantic_frame_spec.")
            if not step.get("component_baseline"):
                failures.append(f"{step_id}: missing component_baseline.")
            failures.extend(story_brief_failures(step_id, step))
    bad_title_terms = {
        "文档目的",
        "修订历史",
        "项目背景",
        "项目目标",
        "UI图连接",
        "UI 图连接",
        "术语定义",
        "核心概念定义",
        "功能概览",
        "概述与目标",
        "界面元素与功能规格",
        "模块详细规格",
        "功能规格详解",
        "核心规则",
        "业务逻辑与规则",
        "版本记录",
    }
    for item in scenes:
        title = str(item.get("title") or "")
        if contains_any(title, bad_title_terms):
            failures.append(f"{item.get('step_id')}: documentation-only section was generated as a scene: {title}")
    for step in steps:
        step_id = str(step.get("id") or "<unknown>")
        prd_sections = " ".join(str(item) for item in step.get("prd_sections", []) if item)
        if contains_any(prd_sections, {"核心概念定义", "概念定义", "术语定义"}):
            failures.append(f"{step_id}: concept/terminology section was generated as a scene.")
    scene_types = [str(item.get("scene_type") or "") for item in scenes]
    if len(scene_types) >= len(EXCALIDRAW_SCENE_TYPES) * 2:
        cycle = [EXCALIDRAW_SCENE_TYPES[index % len(EXCALIDRAW_SCENE_TYPES)] for index in range(len(scene_types))]
        matches = sum(1 for actual, expected in zip(scene_types, cycle) if actual == expected)
        if matches / max(len(scene_types), 1) >= 0.8:
            failures.append("scene_type sequence looks mechanically cycled through showcase scene types.")
    all_texts: list[str] = []
    scene_signatures: list[str] = []
    layout_signatures: list[str] = []
    for item in scenes:
        step_id = str(item.get("step_id") or "")
        rel = str(item.get("file") or "")
        scene_path, _normalized_rel = resolve_excalidraw_ref(demand, rel)
        if not scene_path or not scene_path.is_file():
            continue
        try:
            scene = load_json(scene_path)
        except Exception:
            continue
        frame_id = str(item.get("frame_id") or "")
        frame_elements = scene_elements_for_frame(scene, frame_id or None)
        texts = scene_texts(scene, frame_id or None)
        all_texts.extend(texts)
        layout_signatures.append(layout_signature(frame_elements))
        normalized = ["<template>" if is_template_text(text) else clean_snippet(text, 24) for text in texts[1:8]]
        scene_signatures.append("|".join(normalized))
        step = step_by_id.get(step_id, {})
        if strict and frame_id:
            if len(frame_elements) < 10:
                failures.append(f"{step_id}: storyboard frame is visually too sparse.")
            if len(texts) < 6:
                failures.append(f"{step_id}: storyboard frame has too little visible product copy.")
        if strict and any("section describes" in text.lower() or text in {"Yes", "No"} for text in texts):
            failures.append(f"{step_id}: internal generation labels leaked into the drawing.")
        if strict:
            bad_visible = [text for text in texts if is_non_product_text(text) and any(term.lower() in text.lower() for term in NON_PRODUCT_TEXT_TERMS)]
            if bad_visible:
                failures.append(f"{step_id}: non-product source text leaked into the drawing: {clean_snippet(bad_visible[0], 56)}")
            if placeholder_text_ratio(texts) > 0.25:
                failures.append(f"{step_id}: visible text is dominated by placeholders; frame needs real product copy.")
            failures.extend(brief_implementation_failures(step_id, step, frame_elements, texts))
            failures.extend(visual_grammar_failures(step_id, step, frame_elements, texts))
        if any((("…" in text or "..." in text) and re.search(r"\d|km/h|当前|速度|阈值", text)) for text in texts):
            warnings.append(f"{step_id}: key product copy appears truncated with ellipsis; verify important values are readable.")
        heavy_phone_border = any(
            isinstance(element, dict)
            and element.get("type") == "rectangle"
            and str(element.get("strokeColor") or "").lower() == "#2383ff"
            and float(element.get("strokeWidth") or 0) >= 3
            and float(element.get("width") or 0) >= 250
            and float(element.get("height") or 0) >= 520
            for element in frame_elements
        )
        if heavy_phone_border:
            warnings.append(f"{step_id}: phone inner boundary is visually heavy; prefer a weak boundary and let product content carry emphasis.")
        match_detail = evidence_match_detail(texts, step)
        if text_matches_evidence(texts, step) < 2 or (strict and match_detail["body"] < 1 and (match_detail["entity"] + match_detail["state"]) < 1):
            failures.append(f"{step_id}: scene text does not carry enough PRD-specific evidence.")
        template_hits = sum(1 for text in texts if is_template_text(text))
        if texts and template_hits / len(texts) > 0.45:
            failures.append(f"{step_id}: scene text is dominated by generic showcase template labels.")
    if all_texts:
        template_total = sum(1 for text in all_texts if is_template_text(text))
        if template_total / len(all_texts) > 0.25:
            failures.append("Generated scenes contain too many repeated showcase template labels.")
    if scene_signatures:
        counts: dict[str, int] = {}
        for signature in scene_signatures:
            counts[signature] = counts.get(signature, 0) + 1
        repeated = max(counts.values())
        if len(scene_signatures) >= 6 and repeated / len(scene_signatures) > 0.2:
            failures.append("Multiple scenes share the same text/structure signature; generation is likely templated.")
    if strict and layout_signatures:
        counts: dict[str, int] = {}
        for signature in layout_signatures:
            if signature:
                counts[signature] = counts.get(signature, 0) + 1
        repeated = max(counts.values()) if counts else 0
        if len(layout_signatures) >= 8 and repeated / len(layout_signatures) > 0.45:
            failures.append("Storyboard frames repeat the same layout signature too often; generation is likely templated.")
        sorted_counts = sorted(counts.values(), reverse=True)
        top2 = sum(sorted_counts[:2]) if sorted_counts else 0
        if len(layout_signatures) >= 8 and top2 / len(layout_signatures) > 0.60:
            failures.append("Top storyboard layout families cover too many frames; product surfaces are still too templated.")
    if strict and p["index"].is_file():
        index_html = p["index"].read_text(encoding="utf-8")
        preview_states = re.findall(r'class="[^"]*\bproto-excalidraw-preview\b[^"]*"[^>]*\bdata-render-state="([^"]+)"', index_html)
        if preview_states and all(state == "fallback" for state in preview_states):
            warnings.append("All Excalidraw previews are static fallback snapshots; open preview in a browser to confirm official render and editing.")
        cards = extract_excalidraw_cards(index_html)
        card_keys = {
            (
                str(card.get("data-step-id") or ""),
                str(card.get("data-board-id") or ""),
                str(card.get("data-frame-id") or ""),
            )
            for card in cards
        }
        manifest_keys = {
            (
                str(item.get("step_id") or ""),
                str(item.get("board_id") or ""),
                str(item.get("frame_id") or ""),
            )
            for item in scenes
        }
        if card_keys != manifest_keys:
            failures.append("HTML Excalidraw card mounts do not match manifest board/frame entries.")
    base_scene = scene_check(demand)
    if strict:
        failures.extend(f"scene-check: {item}" for item in base_scene.get("failures", []))
        failures.extend(f"scene-check warning: {item}" for item in base_scene.get("warnings", []))
    else:
        warnings.extend(f"scene-check: {item}" for item in base_scene.get("warnings", []))
    return {"ok": not failures, "failures": failures, "warnings": warnings, "plan": str(p["plan"])}


def parse_html_attrs(tag: str) -> dict[str, str]:
    return {match.group(1): html_lib.unescape(match.group(2)) for match in re.finditer(r'([A-Za-z_:][-A-Za-z0-9_:.]*)="([^"]*)"', tag)}


def extract_excalidraw_cards(html_text: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for match in re.finditer(r"<div\b[^>]*>", html_text):
        tag = match.group(0)
        attrs = parse_html_attrs(tag)
        classes = set(str(attrs.get("class") or "").split())
        if "proto-excalidraw-card" in classes:
            cards.append(attrs)
    return cards


def validate_target(target: Path) -> dict[str, object]:
    demand = demand_dir_for_target(target)
    index = demand / "index.html" if target.is_dir() else target
    failures: list[str] = []
    warnings: list[str] = []
    if not index.is_file():
        return {"ok": False, "failures": [f"Missing index.html: {index}"], "warnings": warnings}
    html = index.read_text(encoding="utf-8")
    required = [
        START_MARKER,
        END_MARKER,
        'id="proto-generated-area"',
        'id="prd-drawer"',
        'class="proto-prd-viewer"',
        'id="proto-nav-dock"',
        'id="proto-step-spotlight"',
        'id="excalidraw-editor-modal"',
        'id="excalidraw-editor-root"',
        "prototype-shell.js",
        "prototype-base.css",
        "prototype-excalidraw.js",
        "prototype-excalidraw.css",
    ]
    for marker in required:
        if marker not in html:
            failures.append(f"Missing shell marker: {marker}")
    prd_src_match = re.search(r"\bdata-prd-src=[\"']([^\"']+)[\"']", html)
    prd_src_value = prd_src_match.group(1) if prd_src_match else ""
    if not prd_src_match:
        failures.append("Missing PRD Viewer source: data-prd-src.")
    elif re.match(r"^[A-Za-z]:[\\/]", prd_src_value) or prd_src_value.startswith("file://") or "\\" in prd_src_value:
        failures.append("PRD Viewer source must be a browser-relative URL such as ../PRD.md, not a local filesystem path.")
    if prd_src_match and not failures:
        prd_file, prd_error = browser_local_path(index.parent, prd_src_value)
        if prd_error:
            failures.append(f"PRD Viewer source is not a local browser-relative path: {prd_src_value}")
        elif not prd_file or not prd_file.is_file():
            failures.append(f"PRD Viewer source file not found from index.html: {prd_src_value}")
        else:
            demand_root = demand_root_for_prototype(demand)
            try:
                prd_file.relative_to(demand_root)
            except ValueError:
                failures.append(f"PRD Viewer source must stay inside the demand folder: {prd_src_value}")
            plan_src = plan_prd_source_for_prototype(demand)
            if plan_src:
                plan_file, plan_error = resolve_plan_prd_source(demand, plan_src)
                if plan_error:
                    failures.append(f"prototype-plan.json source.prd_path is not a local path: {plan_src}")
                elif not plan_file or not plan_file.is_file():
                    failures.append(f"prototype-plan.json source.prd_path file not found: {plan_src}")
                else:
                    try:
                        plan_file.relative_to(demand_root)
                    except ValueError:
                        failures.append(f"prototype-plan.json source.prd_path must stay inside the demand folder: {plan_src}")
                    if plan_file != prd_file:
                        failures.append(f"PRD Viewer source does not match prototype-plan.json source: index={prd_src_value}, plan={plan_src}")
    forbidden = [
        "prototype-content/",
        "content.css",
        "apply-edit-patch",
        "init-content",
        "build-content",
        "proto-excalidraw-export-btn",
        "proto-excalidraw-actions",
        "proto-scene-path",
        "annotation-toggle",
        "toggleEditMode",
        "toggleRevisionMode",
        "copyFullHtmlCode",
        "copyContentPatch",
    ]
    for marker in forbidden:
        if marker in html:
            failures.append(f"HTML content-package marker is not allowed in Excalidraw skill: {marker}")
    cards = extract_excalidraw_cards(html)
    scene_refs = [card.get("data-scene-src", "") for card in cards if card.get("data-scene-src")]
    if not scene_refs:
        failures.append("No Excalidraw scene mounts found in generated area.")
    for ref in sorted(set(scene_refs)):
        if ref.startswith(("http://", "https://", "file:")) or re.match(r"^[A-Za-z]:", ref):
            failures.append(f"Scene reference must be relative: {ref}")
        elif not (demand / ref).is_file():
            failures.append(f"Scene reference missing on disk: {ref}")
    manifest_path = demand / EXCAL_DIR / MANIFEST_FILENAME
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        expected_cards = {
            (
                str(item.get("step_id") or ""),
                str(item.get("file") or ""),
                str(item.get("board_id") or ""),
                str(item.get("frame_id") or ""),
            )
            for item in manifest.get("scenes", [])
            if isinstance(item, dict)
        }
        actual_cards = {
            (
                str(card.get("data-step-id") or ""),
                str(card.get("data-scene-src") or ""),
                str(card.get("data-board-id") or ""),
                str(card.get("data-frame-id") or ""),
            )
            for card in cards
        }
        if actual_cards != expected_cards:
            missing = sorted(expected_cards - actual_cards)
            extra = sorted(actual_cards - expected_cards)
            if missing:
                failures.append("HTML is missing manifest step/frame mounts: " + ", ".join("/".join(item[:1] + item[2:]) for item in missing[:8]))
            if extra:
                failures.append("HTML contains step/frame mounts not in manifest: " + ", ".join("/".join(item[:1] + item[2:]) for item in extra[:8]))
        plan_path = demand / PLAN_FILENAME
        if plan_path.is_file():
            plan = load_json(plan_path)
            groups = [group for group in plan.get("groups", []) if isinstance(group, dict)]
            if groups:
                mounted_step_ids_all = {str(card.get("data-step-id") or "") for card in cards}
                for group in groups:
                    group_id = str(group.get("id") or "")
                    group_title = str(group.get("title") or group_id or "Scenes")
                    group_step_ids = {str(step_id) for step_id in group.get("step_ids", []) if step_id}
                    expected_mounted = group_step_ids.intersection({str(item.get("step_id") or "") for item in manifest.get("scenes", []) if isinstance(item, dict)})
                    if expected_mounted and group_id and f'data-proto-id="{html_escape(group_id)}"' not in html:
                        failures.append(f"Generated area is missing PRD group section: {group_title}")
                    if expected_mounted and not expected_mounted.issubset(mounted_step_ids_all):
                        missing_group_steps = sorted(expected_mounted - mounted_step_ids_all)
                        failures.append(f"Generated area PRD group is missing steps: {group_title} -> {', '.join(missing_group_steps[:8])}")
        for card in cards:
            if not card.get("data-board-id") or not card.get("data-frame-id") or not card.get("data-scene-src"):
                failures.append(f"Excalidraw card is missing board/frame/source attributes for step: {card.get('data-step-id', '<unknown>')}")
    scene_result = scene_check(demand) if (demand / EXCAL_DIR / MANIFEST_FILENAME).is_file() else {"ok": False, "failures": ["Missing Excalidraw manifest."], "warnings": []}
    failures.extend(f"scene-check: {item}" for item in scene_result.get("failures", []))
    warnings.extend(f"scene-check: {item}" for item in scene_result.get("warnings", []))
    for asset in SHELL_ASSETS:
        if not (demand / asset).is_file():
            failures.append(f"Missing shell asset beside index.html: {asset}")
    return {"ok": not failures, "failures": failures, "warnings": warnings, "index": str(index)}


def shell_baseline_dir() -> Path:
    return skill_root() / "templates" / "sketch" / "_shell-baseline"


def normalized_shell_value(text: str, filename: str) -> str:
    if filename == "prototype-base.css":
        text = re.sub(
            r"\n\.proto-generated-area \.proto-content-screen \{\n"
            r"  background: transparent !important;\n"
            r"  border: 0 !important;\n"
            r"  box-shadow: none !important;\n"
            r"  padding: 0 !important;\n"
            r"\}\n",
            "",
            text,
        )
    return text


def normalized_shell_text(path: Path, filename: str) -> str:
    return normalized_shell_value(path.read_text(encoding="utf-8"), filename)


def shell_diff_check() -> dict[str, object]:
    root = skill_root()
    baseline_dir = shell_baseline_dir()
    failures: list[str] = []
    warnings: list[str] = []
    baseline_label = str(baseline_dir)
    if not baseline_dir.is_dir():
        return {"ok": False, "failures": [f"Missing internal shell baseline: {baseline_dir}"], "warnings": []}
    exact_files = ["prototype-base.css", "prototype-shell.js"]
    for filename in exact_files:
        current = root / filename
        base = baseline_dir / filename
        base_text = read_text(base) if base.is_file() else None
        if not current.is_file() or base_text is None:
            failures.append(f"Missing shell file for comparison: {filename}")
            continue
        if normalized_shell_text(current, filename) != normalized_shell_value(base_text, filename):
            failures.append(f"{filename} differs from the internal shell baseline; Excalidraw changes must live in adapter files.")
    for filename in ["prototype-excalidraw.css", "prototype-excalidraw.js"]:
        if not (root / filename).is_file():
            failures.append(f"Missing adapter file: {filename}")
    template = root / "templates" / "sketch" / "prototype-shell.html"
    baseline_template = baseline_dir / "prototype-shell.html"
    baseline_text = read_text(baseline_template) if baseline_template.is_file() else None
    if not template.is_file() or baseline_text is None:
        failures.append("Missing template for shell comparison.")
    else:
        text = template.read_text(encoding="utf-8")
        required_template_hooks = [
            'data-prototype-kind="excalidraw"',
            "prototype-excalidraw.css",
            "prototype-excalidraw.js",
            "EXCALIDRAW_ASSET_PATH",
            "proto-excalidraw-edit-btn",
            "excalidraw-editor-modal",
            "proto-generated-area",
            "proto-step-spotlight",
            "proto-prd-viewer",
        ]
        for hook in required_template_hooks:
            if hook not in text:
                failures.append(f"Template missing allowed Excalidraw/shell hook: {hook}")
        forbidden_template_markers = [
            "proto-excalidraw-export-btn",
            "proto-excalidraw-actions",
            "proto-scene-path",
            "annotation-toggle",
            "revision-panel",
            "edit-panel",
            "revision-popover",
            "copyContentPatch",
            "copyFullHtmlCode",
            "toggleEditMode",
            "toggleRevisionMode",
            "小改",
            "大改",
        ]
        for old_visible in forbidden_template_markers:
            if old_visible in text:
                failures.append(f"Template still exposes HTML edit workflow: {old_visible}")
        allowed_missing_ids = {
            "annotation-toggle",
            "annotation-toggle-prd",
            "annotation-toggle-spotlight",
            "edit-panel",
            "float-edit-btn",
            "float-revision-btn",
            "revision-panel",
            "revision-popover",
            "revision-list",
            "revision-note",
            "revision-target",
        }
        baseline_ids = set(re.findall(r'id="([^"]+)"', baseline_text))
        current_ids = set(re.findall(r'id="([^"]+)"', text))
        missing_protected_ids = sorted(baseline_ids - current_ids - allowed_missing_ids)
        if missing_protected_ids:
            failures.append("Template removed protected shell ids: " + ", ".join(missing_protected_ids[:12]))
    return {"ok": not failures, "baseline": baseline_label, "failures": failures, "warnings": warnings}


def skill_hygiene_check() -> dict[str, object]:
    root = skill_root()
    failures: list[str] = []
    warnings: list[str] = []
    forbidden_file_names = {
        PREVIEW_STATE_FILENAME,
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    }
    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        rel_text = rel.as_posix()
        if ".git/" in rel_text:
            continue
        if path.is_dir():
            if path.name in {"__pycache__", "node_modules", ".pytest_cache", ".cache"}:
                failures.append(f"Runtime/cache directory must not stay in the skill: {rel_text}")
            continue
        if path.name in forbidden_file_names:
            failures.append(f"Runtime/package file must not stay in the skill: {rel_text}")
        if path.suffix in {".pyc", ".pyo", ".log"}:
            failures.append(f"Runtime/cache file must not stay in the skill: {rel_text}")
    if shutil.which("python") is None and shutil.which("py") is None:
        warnings.append(f"`python` is not on PATH; use the current interpreter instead: {sys.executable}")
    return {"ok": not failures, "failures": failures, "warnings": warnings, "python_executable": sys.executable}


def refresh_manifest_hash(demand: Path, scene_rel: str) -> None:
    p = paths(demand)
    if not p["manifest"].is_file():
        return
    manifest = load_json(p["manifest"])
    for item in manifest.get("scenes", []):
        if isinstance(item, dict) and item.get("file") == scene_rel:
            item["hash"] = file_hash(demand / scene_rel)
            item["updated_at"] = utc_now()
    for item in manifest.get("boards", []):
        if isinstance(item, dict) and item.get("file") == scene_rel:
            item["hash"] = file_hash(demand / scene_rel)
            item["updated_at"] = utc_now()
    manifest["updated_at"] = utc_now()
    write_json(p["manifest"], manifest)


def command_preflight(args: argparse.Namespace) -> int:
    target = Path(args.target)
    prd = find_prd(target)
    if target.expanduser().resolve().is_dir():
        demand = demand_dir_for_target(target)
        demand_root = demand_root_for_prototype(demand)
    else:
        demand_root = demand_dir_for_prd(prd)
        demand = prototype_dir_for_demand(demand_root)
    design_hints = collect_design_hints(demand_root, prd)
    result = {
        "ok": True,
        "prd_path": str(prd),
        "demand_dir": str(demand_root),
        "prototype_dir": str(demand),
        "source_policy": "prd_first_design_context_required_when_present",
        "optional_design_context": {
            "available": design_hints.get("available", False),
            "design_md": design_hints.get("design_md", ""),
            "reference_count": design_hints.get("reference_count", 0),
            "platform_hint": design_hints.get("platform_hint", ""),
        },
        "recommended_action": "scaffold" if not (demand / "index.html").is_file() else "plan",
        "prototype_source": f"{EXCAL_DIR}/{BOARDS_DIR}/*.excalidraw",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def place_prd_in_demand(source_prd: Path, demand: Path) -> tuple[Path, str]:
    target_prd = demand / f"{source_prd.stem}.md"
    if source_prd.resolve() == target_prd.resolve():
        return target_prd, "already_inside"
    if target_prd.exists():
        if source_prd.read_bytes() == target_prd.read_bytes():
            source_prd.unlink()
            return target_prd, "removed_duplicate"
        return target_prd, "kept_existing_target"
    shutil.move(str(source_prd), str(target_prd))
    return target_prd, "moved"


def command_scaffold(args: argparse.Namespace) -> int:
    source_prd = find_prd(Path(args.prd))
    demand_root = demand_dir_for_prd(source_prd)
    demand_root.mkdir(parents=True, exist_ok=True)
    target_prd, prd_action = place_prd_in_demand(source_prd, demand_root)
    prototype = prototype_dir_for_demand(demand_root)
    prototype.mkdir(parents=True, exist_ok=True)
    copy_shell_assets(prototype)
    render_shell(prototype, target_prd, args.title or read_prd_title(target_prd))
    write_json(prototype / PLAN_FILENAME, parse_prd_plan(target_prd, prototype))
    init_scenes(prototype)
    build_scenes(prototype)
    print(
        json.dumps(
            {
                "ok": True,
                "demand_dir": str(demand_root),
                "prototype_dir": str(prototype),
                "prd": str(target_prd),
                "prd_action": prd_action,
                "index": str(prototype / "index.html"),
                "storyboard_authoring_required": True,
                "next_action": "Review prototype-plan.json semantic_frame_spec, edit .excalidraw boards, then run quality-check --strict.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def merge_existing_plan(new_plan: dict[str, object], old_plan: dict[str, object] | None) -> dict[str, object]:
    if not old_plan:
        return new_plan
    old_steps = [step for step in old_plan.get("steps", []) if isinstance(step, dict)]
    by_id = {str(step.get("id")): step for step in old_steps if step.get("id")}
    by_title = {str(step.get("title")): step for step in old_steps if step.get("title")}
    preserved_fields = ("state", "rendered", "notes", "manual_notes", "source_notes", "updated_by")
    for step in new_plan.get("steps", []):
        if not isinstance(step, dict):
            continue
        old = by_id.get(str(step.get("id"))) or by_title.get(str(step.get("title")))
        if not old:
            continue
        for field in preserved_fields:
            if field in old:
                step[field] = old[field]
    new_plan["created_at"] = old_plan.get("created_at") or new_plan.get("created_at")
    new_plan["revision_history"] = old_plan.get("revision_history", [])
    return new_plan


def command_plan(args: argparse.Namespace) -> int:
    demand = demand_dir_for_target(Path(args.demand_dir))
    prd = find_prd(demand)
    old_plan = load_json(demand / PLAN_FILENAME) if (demand / PLAN_FILENAME).is_file() and not args.reset else None
    plan = merge_existing_plan(parse_prd_plan(prd, demand), old_plan if isinstance(old_plan, dict) else None)
    write_json(demand / PLAN_FILENAME, plan)
    disposition = plan.get("coverage", {}).get("disposition", []) if isinstance(plan.get("coverage"), dict) else []
    print(
        json.dumps(
            {
                "ok": True,
                "plan": str(demand / PLAN_FILENAME),
                "schema_version": plan.get("schema_version"),
                "steps": len(plan["steps"]),
                "boards": len(plan.get("boards", [])),
                "disposition": len(disposition),
                "storyboard_authoring_required": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_init_scenes(args: argparse.Namespace) -> int:
    result = init_scenes(demand_dir_for_target(Path(args.demand_dir)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_build_scenes(args: argparse.Namespace) -> int:
    result = build_scenes(demand_dir_for_target(Path(args.demand_dir)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_scene_check(args: argparse.Namespace) -> int:
    result = scene_check(demand_dir_for_target(Path(args.demand_dir)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_quality_check(args: argparse.Namespace) -> int:
    result = quality_check(demand_dir_for_target(Path(args.demand_dir)), strict=bool(args.strict))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_validate(args: argparse.Namespace) -> int:
    result = validate_target(Path(args.target))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_shell_diff_check(args: argparse.Namespace) -> int:
    result = shell_diff_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_doctor(args: argparse.Namespace) -> int:
    demand = demand_dir_for_target(Path(args.demand_dir))
    demand_root = demand_root_for_prototype(demand)
    prd = find_prd(demand)
    p = paths(demand)
    actions: list[str] = []
    if not p["index"].is_file():
        actions.append("Run scaffold <prd-path>.")
    elif not p["plan"].is_file():
        actions.append("Run plan <demand-dir>.")
    elif not p["manifest"].is_file():
        actions.append("Run init-scenes <demand-dir>.")
    elif not p["fragment"].is_file():
        actions.append("Run build-scenes <demand-dir>.")
    else:
        check = validate_target(demand)
        quality = quality_check(demand, strict=True)
        if not check["ok"]:
            actions.append("Fix validate failures.")
        elif not quality["ok"]:
            actions.append("Fix quality-check --strict generation-quality failures.")
        else:
            state = load_preview_state(demand)
            health = active_preview_health(state, demand) if state else None
            if state and health and not preview_state_expired(state):
                actions.append(f"Open local preview: {state.get('url')}. Stop with: python scripts/protopilot.py stop-preview \"{demand_root}\"")
            else:
                actions.append(f"Prototype looks ready. Run preview to view and edit locally: python scripts/protopilot.py preview \"{demand_root}\"")
    print(
        json.dumps(
            {
                "ok": True,
                "prd_path": str(prd) if prd else "",
                "demand_dir": str(demand_root),
                "prototype_dir": str(demand),
                "python_executable": sys.executable,
                "next_actions": actions,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


class EditHandler(SimpleHTTPRequestHandler):
    demand_dir: Path = Path.cwd()
    prototype_dir: Path = Path.cwd()
    token: str = ""
    port: int = 0

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        rel = unquote(parsed.path).lstrip("/")
        target = (self.demand_dir / rel).resolve()
        try:
            target.relative_to(self.demand_dir.resolve())
        except ValueError:
            return str((self.demand_dir / "__forbidden__").resolve())
        return str(target)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/__protopilot_excalidraw/save":
            self.send_error(404)
            return
        if self.headers.get("X-ProtoPilot-Preview-Token") != self.token:
            self.send_error(403, "Invalid preview save token.")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            scene_rel = str(payload.get("scene_path") or "")
            scene = payload.get("scene")
            target = (self.prototype_dir / scene_rel).resolve()
            scenes_allowed = (self.prototype_dir / EXCAL_DIR / SCENES_DIR).resolve()
            boards_allowed = (self.prototype_dir / EXCAL_DIR / BOARDS_DIR).resolve()
            try:
                target.relative_to(scenes_allowed)
            except ValueError:
                target.relative_to(boards_allowed)
            if target.suffix != ".excalidraw" or not isinstance(scene, dict):
                raise ValueError("Invalid scene payload.")
            write_json(target, scene)
            refresh_manifest_hash(self.prototype_dir, scene_rel)
            build_scenes(self.prototype_dir)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "scene_path": scene_rel}, ensure_ascii=False).encode("utf-8"))
        except Exception as error:
            self.send_error(400, str(error))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == PREVIEW_HEALTH_PATH:
            body = json.dumps(
                {
                    "ok": True,
                    "schema_version": PREVIEW_SCHEMA_VERSION,
                    "token": self.token,
                    "demand_dir": str(self.demand_dir.resolve()),
                    "prototype_dir": str(self.prototype_dir.resolve()),
                    "pid": os.getpid(),
                    "port": self.port,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == PREVIEW_STOP_PATH:
            token = ""
            for part in parsed.query.split("&"):
                key, _, value = part.partition("=")
                if key == "token":
                    token = unquote(value)
            if not self.token or token != self.token:
                self.send_error(403)
                return
            body = json.dumps({"ok": True, "status": "stopping"}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path: str) -> str:
        if path.endswith(".excalidraw"):
            return "application/json"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def log_message(self, _format: str, *args: object) -> None:
        return


def preview_state_path(demand: Path) -> Path:
    return demand / PREVIEW_STATE_FILENAME


def preview_url(port: int) -> str:
    return f"http://{PREVIEW_HOST}:{port}/{PROTOTYPE_DIRNAME}/index.html"


def preview_health_url(port: int) -> str:
    return f"http://{PREVIEW_HOST}:{port}{PREVIEW_HEALTH_PATH}"


def preview_stop_url(port: int, token: str) -> str:
    return f"http://{PREVIEW_HOST}:{port}{PREVIEW_STOP_PATH}?token={token}"


def preview_expires_at(ttl_minutes: int) -> str | None:
    if ttl_minutes <= 0:
        return None
    expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    return expires.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def preview_state_expired(state: dict[str, object]) -> bool:
    raw = state.get("expires_at")
    if not raw:
        return False
    try:
        expires = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return True
    return expires <= datetime.now(timezone.utc)


def load_preview_state(demand: Path) -> dict[str, object] | None:
    state_file = preview_state_path(demand)
    if not state_file.is_file():
        return None
    try:
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict) or loaded.get("schema_version") != PREVIEW_SCHEMA_VERSION:
        return None
    return loaded


def clear_preview_state(demand: Path) -> None:
    try:
        preview_state_path(demand).unlink()
    except FileNotFoundError:
        return


def fetch_preview_health(port: int, timeout: float = 0.5) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(preview_health_url(port), timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        loaded = json.loads(raw)
    except Exception:
        return None
    return loaded if isinstance(loaded, dict) else None


def request_preview_stop(port: int, token: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(preview_stop_url(port, token), timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        loaded = json.loads(raw)
    except Exception:
        return False
    return isinstance(loaded, dict) and bool(loaded.get("ok"))


def active_preview_health(state: dict[str, object] | None, demand: Path) -> dict[str, object] | None:
    if not state:
        return None
    try:
        port = int(state.get("port"))
    except (TypeError, ValueError):
        return None
    token = str(state.get("token") or "")
    if not token:
        return None
    if str(state.get("url") or "") != preview_url(port):
        return None
    health = fetch_preview_health(port)
    if not health or str(health.get("token") or "") != token:
        return None
    try:
        health_prototype = Path(str(health.get("prototype_dir") or health.get("demand_dir") or "")).resolve()
    except (OSError, RuntimeError):
        return None
    if health_prototype != demand.resolve():
        return None
    return health


def port_is_available(port: int) -> bool:
    if port < 1 or port > 65535:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        if probe.connect_ex((PREVIEW_HOST, port)) == 0:
            return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((PREVIEW_HOST, port))
        except OSError:
            return False
    return True


def choose_preview_port(requested_port: int | None = None) -> tuple[int | None, str | None]:
    if requested_port is not None:
        if requested_port < 1 or requested_port > 65535:
            return None, f"Preview port is out of range: {requested_port}"
        if not port_is_available(requested_port):
            return None, f"Preview port is already in use: {requested_port}"
        return requested_port, None
    for port in range(PREVIEW_PORT_START, PREVIEW_PORT_END + 1):
        if port_is_available(port):
            return port, None
    return None, f"No available preview port in {PREVIEW_PORT_START}-{PREVIEW_PORT_END}."


def terminate_preview_pid(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def start_windows_preview_process(command: list[str], cwd: Path) -> int | None:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return None
    args = ",".join(powershell_single_quote(item) for item in command[1:])
    script = (
        "$ErrorActionPreference='Stop'; "
        "$envs=[System.Environment]::GetEnvironmentVariables('Process'); "
        "if ($envs.Contains('PATH') -and $envs.Contains('Path')) { "
        "[System.Environment]::SetEnvironmentVariable('PATH',$null,'Process') "
        "}; "
        f"$p=Start-Process -FilePath {powershell_single_quote(command[0])} "
        f"-ArgumentList @({args}) "
        f"-WorkingDirectory {powershell_single_quote(str(cwd))} "
        "-WindowStyle Hidden -PassThru; "
        "$p.Id"
    )
    try:
        output = subprocess.check_output(
            [powershell, "-NoProfile", "-Command", script],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except Exception:
        return None
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.isdigit():
            return int(line)
    return None


def spawn_preview_process(command: list[str], demand: Path, popen_kwargs: dict[str, object]) -> tuple[int, subprocess.Popen[bytes] | None]:
    spawn_kwargs = dict(popen_kwargs)
    breakaway_flag = int(spawn_kwargs.pop("_breakaway_flag", 0) or 0)
    try:
        process = subprocess.Popen(command, **spawn_kwargs)
    except OSError:
        if os.name != "nt" or not breakaway_flag or "creationflags" not in spawn_kwargs:
            raise
        fallback_kwargs = dict(spawn_kwargs)
        fallback_kwargs["creationflags"] = int(fallback_kwargs["creationflags"]) & ~breakaway_flag
        process = subprocess.Popen(command, **fallback_kwargs)
    return int(process.pid), process


def wait_preview_stopped(state: dict[str, object], demand: Path, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not active_preview_health(state, demand):
            return True
        time.sleep(0.1)
    return not active_preview_health(state, demand)


def preview_result_from_state(state: dict[str, object], demand: Path, status: str, reused: bool = False) -> dict[str, object]:
    demand_root = demand_root_for_prototype(demand)
    return {
        "ok": True,
        "status": status,
        "reused": reused,
        "url": state.get("url"),
        "host": state.get("host", PREVIEW_HOST),
        "port": state.get("port"),
        "pid": state.get("pid"),
        "demand_dir": str(demand_root),
        "prototype_dir": str(demand),
        "ttl_minutes": state.get("ttl_minutes"),
        "started_at": state.get("started_at"),
        "expires_at": state.get("expires_at"),
        "stop_command": f'python scripts/protopilot.py stop-preview "{demand_root}"',
    }


def start_preview(demand_dir: Path, requested_port: int | None = None, ttl_minutes: int = PREVIEW_DEFAULT_TTL_MINUTES) -> dict[str, object]:
    prototype = demand_dir_for_target(demand_dir)
    demand = demand_root_for_prototype(prototype)
    if ttl_minutes < 0:
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "failures": ["--ttl-minutes must be 0 or greater."]}
    if not demand.is_dir():
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "failures": [f"Demand folder not found: {demand}"]}
    if not (prototype / "index.html").is_file():
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "prototype_dir": str(prototype), "failures": [f"index.html not found in prototype folder: {prototype}"]}

    existing_state = load_preview_state(prototype)
    existing_health = active_preview_health(existing_state, prototype) if existing_state else None
    if existing_state and existing_health and not preview_state_expired(existing_state):
        return preview_result_from_state(existing_state, prototype, "running", reused=True)
    if existing_state and existing_health:
        existing_port = int(existing_state.get("port") or 0)
        existing_token = str(existing_state.get("token") or "")
        if not request_preview_stop(existing_port, existing_token):
            terminate_preview_pid(int(existing_health.get("pid") or existing_state.get("pid") or 0))
        wait_preview_stopped(existing_state, prototype)
    if existing_state:
        clear_preview_state(prototype)

    port, port_error = choose_preview_port(requested_port)
    if port is None:
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "failures": [str(port_error)]}

    token = uuid.uuid4().hex
    state = {
        "schema_version": PREVIEW_SCHEMA_VERSION,
        "host": PREVIEW_HOST,
        "port": port,
        "pid": None,
        "token": token,
        "demand_dir": str(demand),
        "prototype_dir": str(prototype),
        "url": preview_url(port),
        "ttl_minutes": ttl_minutes,
        "started_at": utc_now(),
        "expires_at": preview_expires_at(ttl_minutes),
    }
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "preview-server",
        str(demand),
        "--prototype-dir",
        str(prototype),
        "--port",
        str(port),
        "--token",
        token,
        "--ttl-minutes",
        str(ttl_minutes),
    ]
    popen_kwargs: dict[str, object] = {
        "cwd": str(demand),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    breakaway_flag = 0
    if os.name == "nt":
        breakaway_flag = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | breakaway_flag
        )
        if creationflags:
            popen_kwargs["creationflags"] = creationflags
            popen_kwargs["_breakaway_flag"] = breakaway_flag
    else:
        popen_kwargs["start_new_session"] = True
    process_pid, process = spawn_preview_process(command, demand, popen_kwargs)
    state["pid"] = process_pid

    deadline = time.time() + PREVIEW_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        health = fetch_preview_health(port, timeout=0.25)
        if health and health.get("token") == token and Path(str(health.get("prototype_dir") or health.get("demand_dir"))).resolve() == prototype:
            write_json(preview_state_path(prototype), state)
            return preview_result_from_state(state, prototype, "started")
        if process is not None and process.poll() is not None:
            break
        time.sleep(0.1)

    if process is None or process.poll() is None:
        terminate_preview_pid(process_pid)
    return {
        "ok": False,
        "status": "failed",
        "demand_dir": str(demand),
        "prototype_dir": str(prototype),
        "port": port,
        "pid": process_pid,
        "failures": ["Preview server did not become ready in time."],
    }


def stop_preview(demand_dir: Path) -> dict[str, object]:
    prototype = demand_dir_for_target(demand_dir)
    demand = demand_root_for_prototype(prototype)
    state = load_preview_state(prototype)
    if not state:
        return {"ok": True, "status": "not_running", "demand_dir": str(demand), "prototype_dir": str(prototype), "warnings": ["No ProtoPilot Sketch preview state found."]}
    health = active_preview_health(state, prototype)
    if not health:
        clear_preview_state(prototype)
        return {"ok": True, "status": "stale_cleared", "demand_dir": str(demand), "prototype_dir": str(prototype), "warnings": ["Stale preview state was removed; no matching live preview server was found."]}
    pid = int(health.get("pid") or state.get("pid") or 0)
    try:
        port = int(state.get("port") or 0)
    except (TypeError, ValueError):
        port = 0
    token = str(state.get("token") or "")
    if not request_preview_stop(port, token):
        terminate_preview_pid(pid)
    stopped = wait_preview_stopped(state, prototype)
    if not stopped:
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "prototype_dir": str(prototype), "failures": [f"Preview process did not stop: {pid}"]}
    clear_preview_state(prototype)
    return {"ok": True, "status": "stopped", "demand_dir": str(demand), "prototype_dir": str(prototype), "port": state.get("port"), "pid": pid}


def run_preview_server(demand_dir: Path, port: int, token: str, ttl_minutes: int, prototype_dir: Path | None = None) -> int:
    demand = demand_dir.expanduser().resolve()
    prototype = prototype_dir.expanduser().resolve() if prototype_dir else prototype_dir_for_demand(demand)
    if not demand.is_dir():
        print(json.dumps({"ok": False, "failure": f"Demand folder not found: {demand}"}, ensure_ascii=False), file=sys.stderr)
        return 3
    EditHandler.demand_dir = demand
    EditHandler.prototype_dir = prototype
    EditHandler.token = token
    EditHandler.port = int(port)
    try:
        server = ThreadingHTTPServer((PREVIEW_HOST, int(port)), EditHandler)
        timer: threading.Timer | None = None
        if ttl_minutes > 0:
            timer = threading.Timer(ttl_minutes * 60, server.shutdown)
            timer.daemon = True
            timer.start()
        print(json.dumps({"ok": True, "url": preview_url(int(port)), "pid": os.getpid()}, ensure_ascii=False), flush=True)
        try:
            server.serve_forever(poll_interval=0.5)
        finally:
            if timer:
                timer.cancel()
            server.server_close()
    except OSError as error:
        print(json.dumps({"ok": False, "failure": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 3
    return 0


def command_preview(args: argparse.Namespace) -> int:
    result = start_preview(
        demand_dir_for_target(Path(args.demand_dir)),
        requested_port=int(args.port) if args.port is not None else None,
        ttl_minutes=int(args.ttl_minutes),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_stop_preview(args: argparse.Namespace) -> int:
    result = stop_preview(demand_dir_for_target(Path(args.demand_dir)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_preview_server(args: argparse.Namespace) -> int:
    return run_preview_server(
        Path(args.demand_dir),
        int(args.port),
        str(args.token),
        int(args.ttl_minutes),
        prototype_dir=Path(args.prototype_dir) if getattr(args, "prototype_dir", None) else None,
    )


def command_serve_edit(args: argparse.Namespace) -> int:
    result = start_preview(
        demand_dir_for_target(Path(args.demand_dir)),
        requested_port=int(args.port) if args.port is not None else None,
        ttl_minutes=int(getattr(args, "ttl_minutes", PREVIEW_DEFAULT_TTL_MINUTES)),
    )
    result["compatibility_note"] = "serve-edit is kept as a compatibility alias; prefer preview for local viewing and editing."
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_selfcheck(args: argparse.Namespace) -> int:
    def make_negative_fixture(root: Path) -> Path:
        demand_root = root / "bad"
        demand_root.mkdir()
        demand = prototype_dir_for_demand(demand_root)
        demand.mkdir(parents=True)
        prd = demand_root / "bad.md"
        prd.write_text("# Bad PRD\n\n## 1. 文档说明\n\n### 1.1. 文档目的\n\n说明用途。\n", encoding="utf-8")
        copy_shell_assets(demand)
        render_shell(demand, prd, "Bad")
        group_id = "group-bad"
        step_id = "step-bad-doc"
        bad_plan = {
            "schema_version": 2,
            "generation_mode": "excalidraw_scenes",
            "source": {"prd_path": browser_relative_path(prd, demand), "demand_dir": str(demand_root), "prototype_dir": str(demand)},
            "groups": [{"id": group_id, "title": "文档说明", "step_ids": [step_id]}],
            "steps": [
                {
                    "id": step_id,
                    "title": "文档目的",
                    "group_id": group_id,
                    "kind": "prototype_step",
                    "scene_type": "flow",
                    "scene_type_reason": "section describes a generic flow",
                    "source_evidence": ["文档目的"],
                    "business_entities": ["文档"],
                    "prd_sections": ["文档说明", "文档目的"],
                }
            ],
            "coverage": {"disposition": []},
        }
        write_json(demand / PLAN_FILENAME, bad_plan)
        p = paths(demand)
        p["scenes"].mkdir(parents=True, exist_ok=True)
        scene_rel = f"{EXCAL_DIR}/{SCENES_DIR}/{step_id}.excalidraw"
        write_json(demand / scene_rel, create_excalidraw_scene(bad_plan["steps"][0]))
        write_json(
            p["manifest"],
            {
                "schema_version": 1,
                "kind": "finn-protopilot-sketch-manifest",
                "source": bad_plan["source"],
                "boards": [],
                "scenes": [
                    {
                        "step_id": step_id,
                        "group_id": group_id,
                        "title": "文档目的",
                        "scene_type": "flow",
                        "file": scene_rel,
                        "hash": file_hash(demand / scene_rel),
                    }
                ],
            },
        )
        build_scenes(demand)
        return demand

    with tempfile.TemporaryDirectory(prefix="finn-excalidraw-selfcheck-") as tmp:
        root = Path(tmp)
        prd = root / "demo.md"
        prd.write_text(
            "# Demo Mobile PRD\n\n"
            "## 1. 文档说明\n\n"
            "### 1.1. 文档目的\n\n"
            "说明本文档用途，不需要生成草图。\n\n"
            "## 2. 功能模块\n\n"
            "### 2.1. 登录与认证\n\n"
            "用户输入账号后进入权限判断，失败时展示错误提示，成功时进入首页。\n\n"
            "### 2.2. 会话列表页\n\n"
            "移动端展示会话列表、搜索入口、未读状态和底部 Tab。\n",
            encoding="utf-8",
        )
        demand = root / "demo"
        demand.mkdir()
        shutil.copy2(prd, demand / "demo.md")
        prototype = prototype_dir_for_demand(demand)
        prototype.mkdir(parents=True)
        copy_shell_assets(prototype)
        render_shell(prototype, demand / "demo.md", "Demo")
        write_json(prototype / PLAN_FILENAME, parse_prd_plan(demand / "demo.md", prototype))
        init_scenes(prototype)
        build_scenes(prototype)
        validation = validate_target(demand)
        scene = scene_check(prototype)
        quality = quality_check(prototype, strict=True)
        shell = shell_diff_check()
        preview = start_preview(demand, ttl_minutes=1)
        preview_reuse = start_preview(demand, ttl_minutes=1) if preview["ok"] else {"ok": False, "failures": ["preview did not start"]}
        preview_stop = stop_preview(demand) if preview["ok"] else {"ok": False, "failures": ["preview did not start"]}
        preview_clean = not preview_state_path(prototype).exists()
        pycache = skill_root() / "scripts" / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache, ignore_errors=True)
        hygiene = skill_hygiene_check()
        bad_demand = make_negative_fixture(root)
        negative_quality = quality_check(bad_demand, strict=True)
        result = {
            "ok": (
                validation["ok"]
                and scene["ok"]
                and quality["ok"]
                and shell["ok"]
                and preview["ok"]
                and preview_reuse["ok"]
                and bool(preview_reuse.get("reused"))
                and preview_stop["ok"]
                and preview_clean
                and hygiene["ok"]
                and not negative_quality["ok"]
            ),
            "validate": validation,
            "scene_check": scene,
            "quality_check": quality,
            "preview_check": {
                "start": preview,
                "reuse": preview_reuse,
                "stop": preview_stop,
                "state_cleaned": preview_clean,
            },
            "hygiene_check": hygiene,
            "negative_quality_check": negative_quality,
            "shell_diff_check": shell,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 3


def showcase_plan(showcase: Path, prd: Path) -> dict[str, object]:
    specs = [
        {
            "group": "Flow board",
            "title": "User acquisition flow",
            "scene_type": "flow",
            "reason": "showcase capability sample for end-to-end flow sketches",
            "evidence": ["User acquisition flow", "Trigger, qualify, act, and reach a result", "Use flow arrows for path discussion"],
            "entities": ["Acquisition", "Trigger", "Result"],
        },
        {
            "group": "State board",
            "title": "State matrix",
            "scene_type": "state_matrix",
            "reason": "showcase capability sample for comparing UI states",
            "evidence": ["State matrix", "Default, loading, success, and failure states", "Use cells for state differences"],
            "entities": ["Default", "Loading", "Failure"],
        },
        {
            "group": "Web wireframe",
            "title": "Admin workspace layout",
            "scene_type": "web_wireframe",
            "reason": "showcase capability sample for web page wireframes",
            "evidence": ["Admin workspace layout", "Navigation, toolbar, content, and side panel", "Use low fidelity web surface blocks"],
            "entities": ["Admin", "Workspace", "Panel"],
        },
        {
            "group": "Overlay board",
            "title": "Confirmation modal",
            "scene_type": "overlay",
            "reason": "showcase capability sample for modal and overlay sketches",
            "evidence": ["Confirmation modal", "Dialog over a dimmed page", "Primary and secondary actions"],
            "entities": ["Dialog", "Confirm", "Cancel"],
        },
        {
            "group": "Decision board",
            "title": "Rule branch",
            "scene_type": "decision_branch",
            "reason": "showcase capability sample for permission or rule branches",
            "evidence": ["Rule branch", "Decision splits into pass and blocked paths", "Make branching logic visible"],
            "entities": ["Rule", "Pass", "Blocked"],
        },
        {
            "group": "Table board",
            "title": "List operations",
            "scene_type": "list_table",
            "reason": "showcase capability sample for dense list and table operations",
            "evidence": ["List operations", "Filter, select, batch action, and result", "Represent dense data as editable rows"],
            "entities": ["List", "Filter", "Batch action"],
        },
        {
            "group": "Mobile board",
            "title": "Mobile task surface",
            "scene_type": "mobile_wireframe",
            "reason": "showcase capability sample for mobile-contextual wireframes",
            "evidence": ["Mobile task surface", "App-like list, detail, bottom tab, and form", "Use mobile framing only for mobile context"],
            "entities": ["Mobile", "Task", "Bottom tab"],
        },
    ]
    group_by_id: dict[str, dict[str, object]] = {}
    group_order: list[str] = []
    steps: list[dict[str, object]] = []
    for spec in specs:
        group_title = str(spec["group"])
        title = str(spec["title"])
        group_id = stable_id("group", group_title, "showcase")
        if group_id not in group_by_id:
            group_by_id[group_id] = {"id": group_id, "title": group_title, "description": "", "step_ids": []}
            group_order.append(group_id)
        step_id = stable_id("step", f"{group_title} {title}", "showcase")
        section = {"title": title, "path": [group_title, title], "body": "\n".join(str(item) for item in spec["evidence"])}
        step = make_plan_step(step_id, title, group_id, [group_title, title], section, "Excalidraw ProtoPilot Showcase")
        step["scene_type"] = spec["scene_type"]
        step["scene_type_reason"] = spec["reason"]
        step["source_evidence"] = spec["evidence"]
        step["business_entities"] = spec["entities"]
        step["interaction_goal"] = f"Demonstrate {title} as an editable Excalidraw-native showcase frame."
        step["is_showcase_sample"] = True
        brief = storyboard_brief_for_step(step, {})
        if spec["scene_type"] == "mobile_wireframe":
            brief.update(
                {
                    "screen_role": "list",
                    "surface_archetype": "chat_list",
                    "component_inventory": ["phone_shell", "search", "segmented_tabs", "conversation_rows", "bottom_tab"],
                    "visible_copy": ["Mobile task surface", "Search tasks", "Unread", "Recent task", "Bottom tab"],
                    "data_examples": ["2 unread", "Today"],
                    "state_variants": ["Unread", "Synced"],
                    "annotations": spec["evidence"],
                    "must_not_draw": ["placeholder", "section describes"],
                }
            )
            step["platform"] = "mobile"
            step["surface_kind"] = "list"
        apply_storyboard_brief(step, brief, {})
        group_by_id[group_id]["step_ids"].append(step_id)
        steps.append(step)
    design_hints = {"platform_hint": "mixed", "reference_count": 0, "navigation_terms": []}
    boards = storyboard_boards_for_steps(steps, design_hints)
    now = utc_now()
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "generation_mode": "excalidraw_storyboard_boards",
        "source": {
            "prd_path": browser_relative_path(prd, showcase),
            "demand_dir": str(demand_root_for_prototype(showcase)),
            "prototype_dir": str(showcase),
            "design_context": design_hints,
        },
        "context_summary": {
            "prd_title": "Excalidraw ProtoPilot Showcase",
            "prd_section_count": len(specs),
            "design_context_status": "showcase_fixture",
            "platform_hint": "mixed",
            "reference_count": 0,
            "component_baseline": [],
        },
        "groups": [group_by_id[group_id] for group_id in group_order],
        "boards": boards,
        "frames": [
            {
                "step_id": step.get("id", ""),
                "board_id": step.get("board_id", ""),
                "frame_id": step.get("frame_id", ""),
                "surface_id": step.get("surface_id", ""),
                "surface_kind": step.get("surface_kind", ""),
                "platform": step.get("platform", ""),
                "frame_intent": step.get("frame_intent", ""),
                "source_evidence": step.get("source_evidence", []),
            }
            for step in steps
        ],
        "steps": steps,
        "coverage": {
            "all_prd_sections": [section for spec in specs for section in [str(spec["group"]), str(spec["title"])]],
            "planned_prd_sections": [section for step in steps for section in step["prd_sections"]],
            "covered_prd_sections": [],
            "disposition": [
                {
                    "prd_section": section,
                    "disposition": "prd_viewer",
                    "reason": "Showcase group headings and explanatory material stay in the PRD Viewer; frames cover the explicit 16 showcase pages.",
                    "decision_source": "showcase_fixture",
                }
                for section in ["0. 设计原则", "0.1 页面结构规则", "0.2 Skill 原生能力约束", "5. 推荐页面清单", "6. 生成注意事项"]
            ],
            "omitted": [],
            "notes": "Showcase plan is explicit so real-project semantic filtering does not collapse capability samples.",
        },
        "validation": {"last_scene_check_ok": None, "failures": [], "warnings": []},
        "revision_history": [],
    }


def command_build_showcase(args: argparse.Namespace) -> int:
    showcase_root = skill_root() / "examples" / "showcase-sketch"
    showcase = showcase_root / PROTOTYPE_DIRNAME
    showcase.mkdir(parents=True, exist_ok=True)
    showcase_excal = (showcase / EXCAL_DIR).resolve()
    if showcase_excal.is_dir() and skill_root().resolve() in showcase_excal.parents:
        shutil.rmtree(showcase_excal)
    prd = showcase_root / "proto-pilot-manual.md"
    prd.write_text(
        "# Excalidraw ProtoPilot Showcase\n\n"
        "## Flow board\n\n"
        "### User acquisition flow\n\n"
        "A simple end-to-end path from trigger to result.\n\n"
        "## State board\n\n"
        "### State matrix\n\n"
        "Compare default, loading, success, and failure states.\n\n"
        "## Web wireframe\n\n"
        "### Admin workspace layout\n\n"
        "Sketch a web surface without turning it into production HTML.\n\n"
        "## Overlay board\n\n"
        "### Confirmation modal\n\n"
        "Show how a dialog sits over a dimmed page.\n\n"
        "## Decision board\n\n"
        "### Rule branch\n\n"
        "Make PRD branching logic visible for review.\n\n"
        "## Table board\n\n"
        "### List operations\n\n"
        "Represent dense list and table workflows as editable wireframes.\n\n"
        "## Mobile board\n\n"
        "### Mobile task surface\n\n"
        "Show an app-like list/detail surface only when mobile context matters.\n",
        encoding="utf-8",
    )
    copy_shell_assets(showcase)
    render_shell(showcase, prd, "Excalidraw ProtoPilot Showcase")
    write_json(showcase / PLAN_FILENAME, showcase_plan(showcase, prd))
    init_scenes(showcase)
    build_scenes(showcase)
    result = validate_target(showcase)
    scene_result = scene_check(showcase)
    quality_result = quality_check(showcase, strict=True)
    print(json.dumps({"ok": result["ok"] and scene_result["ok"] and quality_result["ok"], "showcase": str(showcase_root), "prototype_dir": str(showcase), "validate": result, "scene_check": scene_result, "quality_check": quality_result}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] and scene_result["ok"] and quality_result["ok"] else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finn ProtoPilot Sketch tools")
    public_commands = (
        "preflight,scaffold,plan,init-scenes,build-scenes,scene-check,quality-check,"
        "preview,stop-preview,serve-edit,validate,shell-diff-check,doctor,selfcheck,build-showcase"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="{" + public_commands + "}")

    preflight = sub.add_parser("preflight")
    preflight.add_argument("target")
    preflight.set_defaults(func=command_preflight)

    scaffold = sub.add_parser("scaffold")
    scaffold.add_argument("prd")
    scaffold.add_argument("--title")
    scaffold.set_defaults(func=command_scaffold)

    plan = sub.add_parser("plan")
    plan.add_argument("demand_dir")
    plan.add_argument("--reset", action="store_true")
    plan.set_defaults(func=command_plan)

    init = sub.add_parser("init-scenes")
    init.add_argument("demand_dir")
    init.set_defaults(func=command_init_scenes)

    build = sub.add_parser("build-scenes")
    build.add_argument("demand_dir")
    build.set_defaults(func=command_build_scenes)

    check = sub.add_parser("scene-check")
    check.add_argument("demand_dir")
    check.set_defaults(func=command_scene_check)

    quality = sub.add_parser("quality-check")
    quality.add_argument("demand_dir")
    quality.add_argument("--strict", action="store_true")
    quality.set_defaults(func=command_quality_check)

    preview = sub.add_parser("preview")
    preview.add_argument("demand_dir")
    preview.add_argument("--port", type=int)
    preview.add_argument("--ttl-minutes", type=int, default=PREVIEW_DEFAULT_TTL_MINUTES)
    preview.set_defaults(func=command_preview)

    stop_preview_parser = sub.add_parser("stop-preview")
    stop_preview_parser.add_argument("demand_dir")
    stop_preview_parser.set_defaults(func=command_stop_preview)

    serve = sub.add_parser("serve-edit")
    serve.add_argument("demand_dir")
    serve.add_argument("--port", type=int, default=4317)
    serve.add_argument("--ttl-minutes", type=int, default=PREVIEW_DEFAULT_TTL_MINUTES)
    serve.set_defaults(func=command_serve_edit)

    validate = sub.add_parser("validate")
    validate.add_argument("target")
    validate.add_argument("--strict", action="store_true", help="Accepted for the shared command surface; path checks are always enforced.")
    validate.set_defaults(func=command_validate)

    shell = sub.add_parser("shell-diff-check")
    shell.set_defaults(func=command_shell_diff_check)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("demand_dir")
    doctor.set_defaults(func=command_doctor)

    selfcheck = sub.add_parser("selfcheck")
    selfcheck.set_defaults(func=command_selfcheck)

    showcase = sub.add_parser("build-showcase")
    showcase.set_defaults(func=command_build_showcase)

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "preview-server":
        preview_server = argparse.ArgumentParser(description="Internal ProtoPilot Sketch preview server")
        preview_server.add_argument("demand_dir")
        preview_server.add_argument("--prototype-dir")
        preview_server.add_argument("--port", type=int, required=True)
        preview_server.add_argument("--token", required=True)
        preview_server.add_argument("--ttl-minutes", type=int, default=PREVIEW_DEFAULT_TTL_MINUTES)
        args = preview_server.parse_args(argv[1:])
        return command_preview_server(args)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
