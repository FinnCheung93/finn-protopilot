#!/usr/bin/env python3
"""Finn ProtoPilot HTML deterministic scaffolding tools."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import html
import json
import os
import re
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".avif",
    ".bmp",
}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
SHELL_ASSETS = ("prototype-base.css", "prototype-shell.js")
START_MARKER = "<!-- PROTO_GENERATED_AREA_START -->"
END_MARKER = "<!-- PROTO_GENERATED_AREA_END -->"
STATE_CODE_RE = re.compile(r"(?<![A-Za-z0-9])S\d+(?:-[A-Za-z0-9]+)?(?![A-Za-z0-9])", re.I)
BARE_ICON_TEXT = {">", "›", "→", "...", "···", "⋯"}
PLAN_FILENAME = "prototype-plan.json"
PLAN_SCHEMA_VERSION = 1
DESIGN_CONTEXT_FILENAMES = ("design.md", "README.md", "tokens.md", "design-tokens.md")
CONTENT_DIRNAME = "prototype-content"
PROTOTYPE_DIRNAME = "prototype"
CONTENT_MANIFEST_FILENAME = "manifest.json"
CONTENT_CSS_FILENAME = "content.css"
CONTENT_SCREENS_DIRNAME = "screens"
CONTENT_SCHEMA_VERSION = 1
PREVIEW_STATE_FILENAME = ".protopilot-preview.json"
PREVIEW_SCHEMA_VERSION = 1
PREVIEW_HOST = "127.0.0.1"
PREVIEW_PORT_START = 4310
PREVIEW_PORT_END = 4399
PREVIEW_DEFAULT_TTL_MINUTES = 240
PREVIEW_START_TIMEOUT_SECONDS = 5.0
PREVIEW_HEALTH_PATH = "/.protopilot-preview-health"
PREVIEW_SAVE_TEXT_PATCH_PATH = "/__protopilot_html/save-text-patch"
LIGHT_INTERACTION_ACTIONS = {
    "toggle",
    "show",
    "hide",
    "toggle-class",
    "add-class",
    "remove-class",
    "activate",
    "toast",
}
CONTENT_SCREEN_FORBIDDEN_PATTERNS = (
    (r"<\s*/?\s*html\b", "screen files must not contain <html>."),
    (r"<\s*/?\s*head\b", "screen files must not contain <head>."),
    (r"<\s*/?\s*body\b", "screen files must not contain <body>."),
    (r"<\s*script\b", "screen files must not contain <script>; content scripts need a dedicated runtime contract."),
    (r"<\s*style\b", "screen files must not contain <style>; put scoped styles in prototype-content/content.css."),
    (r"<\s*link\b[^>]*\brel=[\"']?stylesheet\b", "screen files must not load stylesheets; put scoped styles in prototype-content/content.css."),
    (r"\son[a-z]+\s*=", "screen files must not contain inline event handlers."),
    (r"javascript\s*:", "screen files must not contain javascript: URLs."),
    (r"\bproto-generated-area\b", "screen files must not contain the shell generated-area container."),
    (r"\bproto-nav-dock\b", "screen files must not contain shell navigation DOM."),
    (r"\bjourney-row\b", "screen files must not contain journey-row; build-content wraps rows."),
    (r"\bjourney-step\b", "screen files must not contain journey-step; build-content wraps steps."),
    (r"\bstep-header\b", "screen files must not contain step-header; build-content creates headers."),
    (r"\bsection-divider\b", "screen files must not contain section-divider; build-content creates group dividers."),
)
CONTENT_CSS_FORBIDDEN_PATTERNS = (
    (r"(^|[,{]\s*)body\b", "content.css must not style body."),
    (r"(^|[,{]\s*)html\b", "content.css must not style html."),
    (r"(^|[,{]\s*):root\b", "content.css must not style :root."),
    (r"(^|[,{]\s*)\*", "content.css must not use global * selectors."),
    (r"\.proto-", "content.css must not override .proto-* shell classes."),
    (r"\.journey-", "content.css must not override .journey-* shell classes."),
    (r"\.step-", "content.css must not override .step-* shell classes."),
    (r"#proto-", "content.css must not target #proto-* shell ids."),
)
RESERVED_CONTENT_NAMESPACE_PREFIXES = ("proto", "journey", "step")
PLAN_GENERATION_MODES = {"content_package", "legacy_fragment", "showcase"}
PLAN_DISPOSITIONS = {"screen", "annotation", "prd_viewer", "delivery_note", "omitted"}
DOCUMENT_SECTION_TERMS = {
    "背景",
    "目标",
    "概述",
    "概览",
    "简介",
    "说明",
    "规则",
    "规格",
    "字段",
    "验收",
    "SOP",
    "风险",
    "来源",
    "审计",
    "配置",
    "机制",
    "原则",
    "范围",
    "口径",
    "数据结构",
    "接口",
    "埋点",
    "权限矩阵",
    "requirement",
    "requirements",
    "rule",
    "rules",
    "spec",
    "specification",
    "field",
    "fields",
    "acceptance",
    "background",
    "goal",
    "overview",
    "risk",
    "source",
    "audit",
    "sop",
}
ANNOTATION_SECTION_TERMS = {"限制", "异常", "差异", "提示", "注意", "风险", "说明", "note", "notes", "edge case"}
DELIVERY_NOTE_SECTION_TERMS = {"交付", "发布", "参考图", "原界面", "设计上下文", "素材", "source", "reference", "delivery", "publish"}
STRONG_SCREEN_SECTION_TERMS = {
    "页面",
    "界面",
    "主页",
    "首页",
    "列表页",
    "详情页",
    "弹窗",
    "浮层",
    "底部弹层",
    "Toast",
    "toast",
    "Sheet",
    "sheet",
    "抽屉",
    "通知",
    "空态",
    "加载",
    "错误态",
    "登录",
    "入口",
    "个人中心",
    "会话",
    "消息",
    "列表",
    "详情",
    "状态",
    "state",
    "screen",
    "page",
    "modal",
    "dialog",
    "drawer",
    "empty",
    "loading",
    "error",
}
STATIC_REF_ATTR_RE = re.compile(r"\b(?:src|href|data-prd-src)=([\"'])([^\"']+)\1", re.I)
CSS_URL_RE = re.compile(r"url\(\s*([\"']?)([^\"')]+)\1\s*\)", re.I)
QUALITY_EXPLANATION_TERMS = {
    "说明",
    "规则",
    "字段",
    "验收",
    "来源",
    "背景",
    "备注",
    "风险",
    "解释",
    "审计",
    "spec",
    "explain",
    "explanation",
    "requirement",
    "requirements",
    "rule",
    "rules",
    "note",
    "notes",
    "audit",
    "source",
    "acceptance",
    "field",
    "fields",
}
QUALITY_EXPLANATION_CLASS_RE = re.compile(
    r"(?:^|[-_\s])(?:spec|explain|explanation|requirement|requirements|rule|rules|note|notes|audit|source|acceptance|field|fields)(?:$|[-_\s])",
    re.I,
)
QUALITY_DANGEROUS_CSS_PATTERNS = (
    (r"position\s*:\s*fixed\b", "generated content uses position: fixed; keep overlays inside the product surface."),
    (r"\bwidth\s*:\s*100vw\b", "generated content uses width: 100vw; this often breaks phone/web surface bounds."),
    (r"\bheight\s*:\s*100vh\b", "generated content uses height: 100vh; this often breaks the presentation canvas."),
    (r"\bmargin(?:-[a-z]+)?\s*:\s*-\d{2,}", "generated content uses a large negative margin; this can cause overlaps."),
    (r"\btransform\s*:[^;]*(?:translate|scale)\([^;]*(?:-\d{2,}|\d{3,}|scale\(\s*[2-9])", "generated content uses a large transform; verify it does not move content out of bounds."),
)
QUALITY_CSS_WARNING_PATTERNS = (
    (r"\bmargin(?:-[a-z]+)?\s*:\s*-\d", "generated content uses a negative margin; small values are allowed but verify there is no overlap."),
)
EDIT_PATCH_SCHEMA_VERSION = 1


def state_codes_from_text(text: str) -> set[str]:
    return {match.group(0).upper() for match in STATE_CODE_RE.finditer(text or "")}


def class_name_suggests_state_switch(classes: set[str], attrs: dict[str, str]) -> bool:
    class_text = " ".join(classes).lower()
    role = attrs.get("role", "").lower()
    aria = attrs.get("aria-label", "").lower()
    return (
        role == "tablist"
        or "segment" in class_text
        or "seg" in class_text
        or "tabs" in class_text
        or "tablist" in class_text
        or "状态" in aria
    )


def style_has_fixed_height_or_large_radius(style: str) -> bool:
    if not style:
        return False
    lowered = style.lower()
    has_fixed_height = bool(re.search(r"\b(?:height|max-height)\s*:\s*(?:\d+px|\d+rem|calc\()", lowered))
    has_large_radius = bool(re.search(r"border-radius\s*:\s*(?:[2-9]\d|1[8-9])px", lowered))
    return has_fixed_height or has_large_radius


def style_has_top_only_radius(style: str) -> bool:
    if not style:
        return False
    lowered = style.lower()
    return bool(
        re.search(r"border-radius\s*:\s*[^;]*(?:\b0\b\s+\b0\b|\b0px\b\s+\b0px\b|\b0rem\b\s+\b0rem\b)", lowered)
        or re.search(r"border-(?:bottom-left|bottom-right)-radius\s*:\s*0", lowered)
    )


class GeneratedAreaInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, object]] = []
        self.step_count = 0
        self.section_divider_count = 0
        self.row_step_counts: list[int] = []
        self.row_extended_counts: list[int] = []
        self.dialogs_outside_surface = 0
        self.key_elements_missing_proto_id = 0
        self.annotation_counts_by_step: list[int] = []
        self.phone_frame_extended_count = 0
        self.phone_frame_count = 0
        self.phone_frame_stretched_count = 0
        self.phone_frame_missing_home_indicator_count = 0
        self.status_bar_count = 0
        self.status_bar_empty_right_count = 0
        self.status_bar_values: list[str] = []
        self.nav_bar_count = 0
        self.nav_bar_missing_title_count = 0
        self.bare_icon_text_count = 0
        self.multi_state_step_count = 0
        self.state_switcher_count = 0
        self.suspicious_half_screen_count = 0
        self.annotation_flow_count = 0
        self.generic_business_button_count = 0
        self.multi_surface_step_count = 0
        self.top_only_radius_count = 0
        self.generated_note_outside_label_count = 0
        self.step_stack: list[dict[str, object]] = []

    @staticmethod
    def classes_from_attrs(attrs: list[tuple[str, str | None]]) -> set[str]:
        raw = ""
        for key, value in attrs:
            if key.lower() == "class" and value:
                raw = value
                break
        return {item for item in raw.split() if item}

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): value or "" for key, value in attrs}

    def has_surface_ancestor(self) -> bool:
        surface_classes = {"app-screen", "phone-screen", "web-surface"}
        return any(surface_classes.intersection(node["classes"]) for node in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self.classes_from_attrs(attrs)
        attr_map = self.attrs_dict(attrs)
        node = {
            "tag": tag.lower(),
            "classes": classes,
            "attrs": attr_map,
            "row_steps": 0,
            "annotations": 0,
            "has_app_screen": False,
            "has_home_indicator": False,
            "status_parts": [],
            "nav_title_found": False,
            "step_info": None,
        }
        style = attr_map.get("style", "")

        if "section-divider" in classes:
            self.section_divider_count += 1

        if "phone-frame" in classes and "is-extended" in classes:
            self.phone_frame_extended_count += 1
        if "phone-frame" in classes:
            self.phone_frame_count += 1
            if "is-extended" in classes:
                for ancestor in reversed(self.stack):
                    if "journey-row" in ancestor["classes"]:
                        ancestor["extended_phones"] = int(ancestor.get("extended_phones", 0)) + 1
                        break
            if {"is-stretched", "is-long", "phone-tall"}.intersection(classes) or re.search(
                r"\b(min-)?height\s*:", style, re.I
            ):
                self.phone_frame_stretched_count += 1

        if "phone-status-bar" in classes:
            self.status_bar_count += 1
            node["is_status_bar"] = True

        if tag.lower() == "span" and any(node.get("is_status_bar") for node in self.stack):
            node["is_status_span"] = True
            node["status_text"] = ""

        if "nav-bar" in classes:
            self.nav_bar_count += 1
            node["is_nav_bar"] = True

        if "nav-title" in classes:
            for ancestor in reversed(self.stack):
                if ancestor.get("is_nav_bar"):
                    ancestor["nav_title_found"] = True
                    break

        if "journey-step" in classes:
            self.step_count += 1
            label = attr_map.get("data-proto-label", "")
            step_info = {
                "label": label,
                "title": "",
                "state_codes": set(state_codes_from_text(label)),
                "state_switch_codes": set(),
                "generic_buttons": 0,
                "surface_count": 0,
            }
            node["step_info"] = step_info
            self.step_stack.append(step_info)
            for ancestor in reversed(self.stack):
                if "journey-row" in ancestor["classes"]:
                    ancestor["row_steps"] = int(ancestor["row_steps"]) + 1
                    break

        if "app-screen" in classes:
            for ancestor in reversed(self.stack):
                if "phone-frame" in ancestor["classes"]:
                    ancestor["has_app_screen"] = True
                    break

        if {"phone-frame", "web-surface"}.intersection(classes) and self.step_stack:
            self.step_stack[-1]["surface_count"] = int(self.step_stack[-1]["surface_count"]) + 1

        if "phone-home-indicator" in classes:
            for ancestor in reversed(self.stack):
                if "phone-frame" in ancestor["classes"]:
                    ancestor["has_home_indicator"] = True
                    break

        if class_name_suggests_state_switch(classes, attr_map) and self.has_surface_ancestor():
            node["is_state_switcher"] = True
            if self.step_stack:
                self.step_stack[-1]["state_switch_codes"].update(state_codes_from_text(attr_map.get("aria-label", "")))

        if "app-content" in classes and self.has_surface_ancestor():
            if style_has_fixed_height_or_large_radius(style):
                self.suspicious_half_screen_count += 1

        if self.has_surface_ancestor() and style_has_top_only_radius(style):
            self.top_only_radius_count += 1

        if "proto-generated-note" in classes and not any("proto-area-label" in node["classes"] for node in self.stack):
            self.generated_note_outside_label_count += 1

        key_classes = {
            "card",
            "list-row",
            "primary-btn",
            "secondary-btn",
            "dialog",
            "dialog-backdrop",
            "annotation",
            "toast",
            "switch",
            "segment-btn",
            "kp-card",
            "empty-illus",
            "error-callout",
            "web-surface",
            "phone-frame",
            "app-screen",
        }
        if classes.intersection(key_classes) and "data-proto-id" not in attr_map:
            self.key_elements_missing_proto_id += 1

        if "annotation" in classes:
            if re.search(r"\bposition\s*:\s*relative\b", style, re.I):
                self.annotation_flow_count += 1
            if any({"app-screen", "phone-screen", "phone-frame", "app-content"}.intersection(node["classes"]) for node in self.stack):
                self.annotation_flow_count += 1
            for ancestor in reversed(self.stack):
                if "journey-step" in ancestor["classes"]:
                    ancestor["annotations"] = int(ancestor["annotations"]) + 1
                    break

        if tag.lower() == "button" and {"primary-btn", "secondary-btn"}.intersection(classes):
            self.generic_business_button_count += 1
            if self.step_stack:
                self.step_stack[-1]["generic_buttons"] = int(self.step_stack[-1]["generic_buttons"]) + 1

        if "dialog-backdrop" in classes and not self.has_surface_ancestor():
            self.dialogs_outside_surface += 1

        self.stack.append(node)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if any(node.get("is_status_span") for node in self.stack):
            for node in reversed(self.stack):
                if node.get("is_status_span"):
                    node["status_text"] = str(node.get("status_text", "")) + data
                    break
        if self.has_surface_ancestor() and data.strip() in BARE_ICON_TEXT:
            self.bare_icon_text_count += 1
        if not self.step_stack:
            return
        current_step = self.step_stack[-1]
        if any("step-title" in node["classes"] for node in self.stack):
            current_step["title"] = str(current_step["title"]) + data
            current_step["state_codes"].update(state_codes_from_text(data))
        if any(node.get("is_state_switcher") for node in self.stack):
            current_step["state_switch_codes"].update(state_codes_from_text(data))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        while self.stack:
            node = self.stack.pop()
            if "journey-row" in node["classes"]:
                self.row_step_counts.append(int(node["row_steps"]))
                self.row_extended_counts.append(int(node.get("extended_phones", 0)))
            if "journey-step" in node["classes"]:
                self.annotation_counts_by_step.append(int(node["annotations"]))
                step_info = node.get("step_info")
                if step_info:
                    if len(step_info["state_codes"]) >= 2:
                        self.multi_state_step_count += 1
                    if len(step_info["state_switch_codes"]) >= 2:
                        self.state_switcher_count += 1
                    if int(step_info["surface_count"]) > 1:
                        self.multi_surface_step_count += 1
                    if self.step_stack and self.step_stack[-1] is step_info:
                        self.step_stack.pop()
            if "phone-frame" in node["classes"]:
                if node["has_app_screen"] and not node["has_home_indicator"]:
                    self.phone_frame_missing_home_indicator_count += 1
            if node.get("is_status_span"):
                for ancestor in reversed(self.stack):
                    if ancestor.get("is_status_bar"):
                        ancestor["status_parts"].append(str(node.get("status_text", "")).strip())
                        break
            if node.get("is_status_bar"):
                parts = [part for part in node.get("status_parts", [])]
                right = parts[-1].strip() if parts else ""
                if not right:
                    self.status_bar_empty_right_count += 1
                else:
                    self.status_bar_values.append(right)
            if node.get("is_nav_bar") and not node.get("nav_title_found"):
                self.nav_bar_missing_title_count += 1
            if node["tag"] == tag:
                break


def inspect_generated_area(text: str) -> dict[str, object]:
    if START_MARKER in text and END_MARKER in text:
        text = text.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0]

    inspector = GeneratedAreaInspector()
    inspector.feed(text)
    warnings: list[str] = []

    if inspector.step_count >= 6 and inspector.section_divider_count == 0:
        warnings.append("业务步骤达到 6 个以上但没有 section-divider 分组，目录会显得平铺。")

    wide_rows = [count for count in inspector.row_step_counts if count > 4]
    if wide_rows:
        warnings.append("单个 journey-row 内超过 4 个界面；画布会自动换行，但该生成块较大，建议按 PRD 结构拆分以降低上下文负担。")

    if inspector.dialogs_outside_surface:
        warnings.append("发现 dialog-backdrop 不在 app-screen / phone-screen / web-surface 内，弹窗可能覆盖整个画布。")

    if inspector.key_elements_missing_proto_id:
        warnings.append("发现关键业务元素缺少 data-proto-id，可能导致改文字/大改无法选中。")

    crowded_annotation_steps = [count for count in inspector.annotation_counts_by_step if count > 2]
    if crowded_annotation_steps:
        warnings.append("发现单个界面内超过 2 个标注，容易重叠或遮挡界面。")

    if inspector.phone_frame_stretched_count:
        warnings.append("发现手机外框疑似被拉长；长内容应使用固定手机壳 + 内容向下延展。")

    status_values = {value for value in inspector.status_bar_values if value}
    if len(status_values) > 1:
        warnings.append("发现同一份原型内状态栏网络/电量文字混用；默认应统一，例如 12:30 + 5G，除非 PRD 或参考图明确区分平台。")

    if inspector.status_bar_empty_right_count:
        warnings.append("发现手机状态栏右侧为空；应统一补齐网络/电量文字，避免同一份原型状态栏不一致。")

    if inspector.nav_bar_missing_title_count:
        warnings.append("发现手机导航栏缺少 .nav-title；标题栏可能在画布或全屏模式下看不见。")

    if inspector.phone_frame_count >= 3 and inspector.phone_frame_extended_count == inspector.phone_frame_count:
        warnings.append("发现全部手机都使用 is-extended；短页面不应默认使用长页模式，只有内容确实超过一屏时才启用。")

    if any(count > 1 for count in inspector.row_extended_counts):
        warnings.append("发现同一 journey-row 内有多个长页手机；请确认长页布局已为延展内容占位，否则下一行原型可能压到上一行。")

    if inspector.bare_icon_text_count:
        warnings.append("发现手机界面内有裸 > / ... / → 等文字代替图标；正式操作 icon 应使用 Lucide。")

    if inspector.multi_state_step_count:
        warnings.append("发现单个 journey-step 标题或 label 中包含多个状态码，疑似把多个 PRD 状态折叠进单屏；S1/S2/S3/S4 等状态默认应拆成独立界面。")

    if inspector.state_switcher_count:
        warnings.append("发现手机界面内使用状态切换控件承载多个 PRD 状态；除非真实产品本来如此，否则应拆成多个 journey-step。")

    if inspector.suspicious_half_screen_count or inspector.phone_frame_missing_home_indicator_count:
        warnings.append("发现手机界面疑似没有完整填满屏幕，或缺少底部 home indicator；不要用大圆角半截容器承载整页。")

    if inspector.annotation_flow_count:
        warnings.append("发现标注使用相对定位或进入手机/主内容流，可能挤压、遮挡界面；标注应优先放在手机外侧留白。")

    if inspector.generic_business_button_count >= 3:
        warnings.append("业务生成区大量使用通用 primary-btn/secondary-btn，按钮可能套用了宣讲台默认风格；应优先复刻产品/参考图按钮样式。")

    if inspector.multi_surface_step_count:
        warnings.append("发现单个 journey-step 内包含多个手机/页面界面；目录和全屏放大只能对应一个标题，默认应拆成多个 journey-step。")

    if inspector.top_only_radius_count:
        warnings.append("发现手机界面内有疑似只圆上角、不圆下角的贴底模块；除非是明确半截浮层，否则应保持完整圆角链路。")

    if inspector.generated_note_outside_label_count:
        warnings.append("发现 proto-generated-note 出现在生成区标签之外；来源/背景说明不要横跨画布挤占宣讲区，应放在交付说明或标注中。")

    return {
        "step_count": inspector.step_count,
        "section_divider_count": inspector.section_divider_count,
        "max_steps_per_row": max(inspector.row_step_counts) if inspector.row_step_counts else 0,
        "max_extended_phones_per_row": max(inspector.row_extended_counts) if inspector.row_extended_counts else 0,
        "dialogs_outside_surface": inspector.dialogs_outside_surface,
        "key_elements_missing_proto_id": inspector.key_elements_missing_proto_id,
        "max_annotations_per_step": max(inspector.annotation_counts_by_step) if inspector.annotation_counts_by_step else 0,
        "phone_frame_count": inspector.phone_frame_count,
        "phone_frame_extended_count": inspector.phone_frame_extended_count,
        "phone_frame_stretched_count": inspector.phone_frame_stretched_count,
        "phone_frame_missing_home_indicator_count": inspector.phone_frame_missing_home_indicator_count,
        "status_bar_count": inspector.status_bar_count,
        "status_bar_values": sorted(status_values),
        "status_bar_empty_right_count": inspector.status_bar_empty_right_count,
        "nav_bar_count": inspector.nav_bar_count,
        "nav_bar_missing_title_count": inspector.nav_bar_missing_title_count,
        "bare_icon_text_count": inspector.bare_icon_text_count,
        "multi_state_step_count": inspector.multi_state_step_count,
        "state_switcher_count": inspector.state_switcher_count,
        "suspicious_half_screen_count": inspector.suspicious_half_screen_count,
        "annotation_flow_count": inspector.annotation_flow_count,
        "generic_business_button_count": inspector.generic_business_button_count,
        "multi_surface_step_count": inspector.multi_surface_step_count,
        "top_only_radius_count": inspector.top_only_radius_count,
        "generated_note_outside_label_count": inspector.generated_note_outside_label_count,
        "strict_failures": build_strict_failures(inspector),
        "warnings": warnings,
    }


def build_strict_failures(inspector: GeneratedAreaInspector) -> list[str]:
    failures: list[str] = []
    if inspector.key_elements_missing_proto_id:
        failures.append("关键业务元素缺少 data-proto-id。")
    if inspector.dialogs_outside_surface:
        failures.append("弹窗不在手机/页面表面内。")
    if inspector.multi_state_step_count:
        failures.append("多个 PRD 状态被折叠进一个 journey-step。")
    if inspector.state_switcher_count:
        failures.append("用手机内切换控件承载多个 PRD 状态。")
    if inspector.multi_surface_step_count:
        failures.append("一个 journey-step 内包含多个主要界面。")
    if inspector.suspicious_half_screen_count or inspector.phone_frame_missing_home_indicator_count:
        failures.append("手机界面疑似不是完整屏。")
    if inspector.phone_frame_count >= 3 and inspector.phone_frame_extended_count == inspector.phone_frame_count:
        failures.append("短页面疑似全量滥用 is-extended。")
    if any(count > 1 for count in inspector.row_extended_counts):
        failures.append("同一行多个长页手机可能导致上下行压叠。")
    return failures


EXISTING_SCREEN_PATTERNS = [
    "原有界面",
    "已有界面",
    "现有界面",
    "当前界面",
    "原页面",
    "已有页面",
    "现有页面",
    "当前页面",
    "在原",
    "在现有",
    "新增入口",
    "增加入口",
    "保留原",
    "基于原",
    "基于现有",
    "existing screen",
    "existing page",
    "current screen",
    "current page",
    "add entry",
    "modify existing",
]


def read_text_best_effort(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""


def prd_mentions_existing_screen(prd_path: Path) -> bool:
    text = read_text_best_effort(prd_path).lower()
    return any(pattern.lower() in text for pattern in EXISTING_SCREEN_PATTERNS)


def find_original_screen_candidates(references: dict[str, object]) -> list[str]:
    candidate_items = [*references["demand_assets"], *references["demand_references"]]
    return [
        str(item)
        for item in candidate_items
        if re.search(r"(original|current|existing|before|screen|screenshot|原|现有|已有|当前|截图|界面)", str(item), re.I)
    ]


def find_demand_prd(demand_dir: Path) -> Path | None:
    if demand_dir.name == PROTOTYPE_DIRNAME:
        demand_dir = demand_dir.parent
    direct = demand_dir / f"{demand_dir.name}.md"
    if direct.is_file():
        return direct
    markdowns = sorted(
        [item for item in demand_dir.glob("*") if item.is_file() and item.suffix.lower() in MARKDOWN_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )
    return markdowns[0] if markdowns else None


def prototype_dir_for_demand(demand_dir: Path) -> Path:
    demand = demand_dir.expanduser().resolve()
    return demand if demand.name == PROTOTYPE_DIRNAME else demand / PROTOTYPE_DIRNAME


def demand_root_for_prototype(prototype_dir: Path) -> Path:
    prototype = prototype_dir.expanduser().resolve()
    return prototype.parent if prototype.name == PROTOTYPE_DIRNAME else prototype


def prototype_dir_for_target(target: Path) -> Path:
    resolved = target.expanduser().resolve()
    if resolved.is_dir():
        return resolved if resolved.name == PROTOTYPE_DIRNAME else resolved / PROTOTYPE_DIRNAME
    if resolved.is_file():
        if resolved.parent.name == PROTOTYPE_DIRNAME:
            return resolved.parent
        if resolved.suffix.lower() in MARKDOWN_EXTENSIONS:
            return resolved.parent / PROTOTYPE_DIRNAME
        return resolved.parent
    parent = resolved.parent
    if parent.name == PROTOTYPE_DIRNAME:
        return parent
    if resolved.suffix.lower() in MARKDOWN_EXTENSIONS:
        return parent / PROTOTYPE_DIRNAME
    return resolved / PROTOTYPE_DIRNAME


def path_has_generated_area(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    if not text.strip():
        return False
    if path.name.lower() == "index.html":
        fragment = extract_generated_fragment(text)
        if "待补充" in fragment or "请将 PRD" in fragment:
            return False
        return "journey-step" in fragment
    return "journey-step" in text or "proto-generated-area" in text


def find_fragment_candidate(folder: Path) -> Path | None:
    fragment = folder / "generated-area-fragment.html"
    if path_has_generated_area(fragment):
        return fragment
    index = folder / "index.html"
    if path_has_generated_area(index):
        return index
    return None


def find_legacy_candidates(demand_dir: Path) -> list[Path]:
    parent = demand_dir.parent
    if not parent.exists():
        return []
    patterns = ("proto*", "*prototype*", "*草稿*")
    candidates: dict[str, Path] = {}
    for pattern in patterns:
        for item in parent.glob(pattern):
            if item.is_dir() and item.resolve() != demand_dir.resolve() and find_fragment_candidate(item):
                candidates[str(item.resolve()).lower()] = item
    return sorted(candidates.values(), key=lambda p: p.name.lower())


def choose_recommended_action(demand_dir: Path) -> tuple[str, Path | None, list[Path]]:
    local_fragment = find_fragment_candidate(demand_dir)
    if local_fragment:
        return "inject_fragment", local_fragment, []
    legacy_candidates = find_legacy_candidates(demand_dir)
    if legacy_candidates:
        return "migrate_legacy", find_fragment_candidate(legacy_candidates[0]), legacy_candidates
    return "generate_from_prd", None, []


def resolve_preflight_target(target: Path) -> tuple[Path, Path | None, bool]:
    source = target.expanduser().resolve()
    if source.is_file():
        if source.suffix.lower() not in MARKDOWN_EXTENSIONS:
            fail(f"Preflight target must be a Markdown PRD or demand folder: {source}")
        if is_standard_demand_prd(source):
            prototype_dir = source.parent / PROTOTYPE_DIRNAME
            return prototype_dir, source, prototype_dir.exists()
        demand_dir = source.parent / source.stem
        return demand_dir / PROTOTYPE_DIRNAME, source, False
    if source.is_dir():
        prototype_dir = prototype_dir_for_target(source)
        return prototype_dir, find_demand_prd(prototype_dir), prototype_dir.exists()
    fail(f"Preflight target not found: {source}")


def build_preflight_result(target: Path) -> dict[str, object]:
    demand_dir, prd_path, is_standard = resolve_preflight_target(target)
    demand_root = demand_root_for_prototype(demand_dir)
    references = discover_references(demand_root.resolve())
    recommended_action, reusable_fragment, legacy_candidates = choose_recommended_action(demand_dir.resolve())
    existing_screen_change_detected = bool(prd_path and prd_mentions_existing_screen(prd_path))
    original_screen_candidates = find_original_screen_candidates(references)
    demand_reference_prompt_required = False
    existing_screen_prompt_recommended = False

    agent_next_actions = list(references["agent_next_actions"])
    if not bool(references["has_demand_references"]):
        agent_next_actions.append("未发现需求级参考图；默认继续生成，并在 plan.source_audit 记录 reference_status=not_provided。")
    if original_screen_candidates:
        agent_next_actions.append("已发现疑似原界面图；生成前抽样查看并记录采用点。")
    elif existing_screen_change_detected:
        agent_next_actions.append("PRD 疑似在原有界面上修改但未发现原界面图；默认继续，仅在明确像素级复刻时再询问。")
    if references.get("design_context_warning"):
        agent_next_actions.append(str(references["design_context_warning"]))

    return {
        "ok": True,
        "target": str(target.expanduser().resolve()),
        "is_standard_demand_folder": is_standard,
        "demand_dir": str(demand_dir.resolve()),
        "prd_path": str(prd_path.resolve()) if prd_path else None,
        "recommended_action": recommended_action,
        "reusable_fragment": str(reusable_fragment.resolve()) if reusable_fragment else None,
        "legacy_candidates": [str(item.resolve()) for item in legacy_candidates],
        "references": references,
        "demand_reference_prompt_required": demand_reference_prompt_required,
        "existing_screen_change_detected": existing_screen_change_detected,
        "existing_screen_prompt_recommended": existing_screen_prompt_recommended,
        "original_screen_candidates": original_screen_candidates,
        "reference_images_found": references["reference_images_found"],
        "reference_usage_required": references["reference_usage_required"],
        "reference_status": "provided" if references["reference_images_found"] else "not_provided",
        "reference_prompt_policy": "continue_by_default",
        "original_screen_status": "available" if existing_screen_change_detected else "not_applicable",
        "original_screen_prompt_policy": "ask_only_when_blocking",
        "design_context_warning": references.get("design_context_warning"),
        "recommended_design_context": references.get("recommended_design_context"),
        "agent_next_actions": agent_next_actions,
    }


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(code)


def skill_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def rel_or_abs(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


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


def expected_prd_viewer_src(prototype_dir: Path) -> str | None:
    prototype = prototype_dir.expanduser().resolve()
    demand_root = demand_root_for_prototype(prototype)
    plan_src = plan_prd_source_for_prototype(prototype)
    if plan_src:
        target, reason = browser_local_path(prototype, plan_src)
        if not reason and target and target.is_file():
            try:
                target.relative_to(demand_root)
            except ValueError:
                target = None
        if target and target.is_file():
            return plan_src.replace("\\", "/")
    prd = find_demand_prd(demand_root)
    if prd and prd.is_file():
        return browser_relative_path(prd, prototype)
    return None


def collect_files(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []
    files = [item for item in folder.rglob("*") if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS]
    return sorted(files, key=lambda p: str(p).lower())


def find_product_design_dir(demand_dir: Path) -> Path | None:
    for ancestor in [demand_dir.parent, *demand_dir.parent.parents]:
        candidate = ancestor / "Design"
        if candidate.is_dir():
            return candidate
    return None


def collect_design_context_files(design_dir: Path | None) -> list[Path]:
    if not design_dir or not design_dir.is_dir():
        return []
    wanted = {name.lower() for name in DESIGN_CONTEXT_FILENAMES}
    order = {name.lower(): index for index, name in enumerate(DESIGN_CONTEXT_FILENAMES)}
    candidates = [item for item in design_dir.iterdir() if item.is_file() and item.name.lower() in wanted]
    return sorted(candidates, key=lambda p: order.get(p.name.lower(), 99))


def find_product_design_md(demand_dir: Path) -> Path | None:
    design_dir = find_product_design_dir(demand_dir)
    if not design_dir:
        return None
    candidate = design_dir / "design.md"
    return candidate if candidate.is_file() else None


def product_match_tokens(product_name: str) -> set[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", product_name)
    raw_tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", spaced.lower())
    ignored = {"ai", "app", "mobile", "client", "prd", "design"}
    return {token for token in raw_tokens if len(token) >= 3 and token not in ignored}


def design_context_match_score(path: Path, product_tokens: set[str]) -> int:
    if not product_tokens:
        return 0
    text = read_text_best_effort(path)[:12000].lower()
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return sum(1 for token in product_tokens if token in normalized)


def choose_recommended_design_context(demand_dir: Path, contexts: list[Path]) -> tuple[Path | None, str]:
    if not contexts:
        return None, ""
    product_name = demand_dir.parent.name
    tokens = product_match_tokens(product_name)
    scored = [(design_context_match_score(path, tokens), path) for path in contexts]
    design_md = next((path for path in contexts if path.name.lower() == "design.md"), None)
    design_md_score = design_context_match_score(design_md, tokens) if design_md else -1
    best_score, best_path = max(scored, key=lambda item: (item[0], item[1].name.lower()))
    if design_md and best_path != design_md and best_score > design_md_score:
        return best_path, (
            f"Design/design.md appears weakly matched to product '{product_name}', "
            f"while {best_path.name} matches better; read the recommended context before generating UI."
        )
    return design_md or best_path, ""


def discover_references(demand_dir: Path) -> dict[str, object]:
    product_design_dir = find_product_design_dir(demand_dir)
    design_contexts = collect_design_context_files(product_design_dir)
    design_md = next((path for path in design_contexts if path.name.lower() == "design.md"), None)
    recommended_context, design_context_warning = choose_recommended_design_context(demand_dir, design_contexts)

    product_assets: list[Path] = []
    product_references: list[Path] = []
    if product_design_dir:
        product_assets = collect_files(product_design_dir / "assets")
        product_references = collect_files(product_design_dir / "references")

    demand_assets = collect_files(demand_dir / "assets")
    demand_references = collect_files(demand_dir / "references")
    has_demand_references = bool(demand_assets or demand_references)
    all_reference_images = product_assets + product_references + demand_assets + demand_references

    return {
        "design_md": str(design_md.resolve()) if design_md else None,
        "design_context_candidates": [rel_or_abs(p, demand_dir) for p in design_contexts],
        "recommended_design_context": str(recommended_context.resolve()) if recommended_context else None,
        "design_context_warning": design_context_warning,
        "product_assets": [rel_or_abs(p, demand_dir) for p in product_assets],
        "product_references": [rel_or_abs(p, demand_dir) for p in product_references],
        "demand_assets": [rel_or_abs(p, demand_dir) for p in demand_assets],
        "demand_references": [rel_or_abs(p, demand_dir) for p in demand_references],
        "all_reference_images": [rel_or_abs(p, demand_dir) for p in all_reference_images],
        "reference_images_found": bool(all_reference_images),
        "reference_usage_required": bool(all_reference_images),
        "has_demand_references": has_demand_references,
        "reference_prompt_needed": False,
        "reference_prompt": (
            "未发现需求级参考图时默认继续生成，并在 plan.source_audit 记录 reference_status=not_provided。"
            if not has_demand_references
            else ""
        ),
        "agent_next_actions": [
            "读取源 PRD。",
            "如果 design_md 存在，读取 Design/design.md；如果 recommended_design_context 指向另一个文件，优先补读该文件并说明原因。",
            "如果 all_reference_images 非空，逐张打开或抽样打开关键参考图，提炼布局、组件、圆角、密度和弹层规则；不能只列路径。",
            "如果没有需求级参考图，默认继续，不打断；只有明确像素级复刻或 PRD 因缺原界面无法判断时才询问。",
        ],
    }


def is_standard_demand_prd(prd_path: Path) -> bool:
    return prd_path.parent.name == prd_path.stem


def copy_shell_assets(skill_root: Path, demand_dir: Path, dry_run: bool) -> list[str]:
    copied: list[str] = []
    for filename in SHELL_ASSETS:
        src = skill_root / filename
        if not src.is_file():
            fail(f"Missing required presentation-stage asset: {src}")
        dest = demand_dir / filename
        copied.append(str(dest.resolve()))
        if not dry_run:
            shutil.copy2(src, dest)
    return copied


def prepare(prd_path: Path, skill_root: Path, dry_run: bool = False) -> dict[str, object]:
    source_prd = prd_path.expanduser().resolve()
    if not source_prd.is_file():
        fail(f"PRD file not found: {source_prd}")
    if source_prd.suffix.lower() not in MARKDOWN_EXTENSIONS:
        fail(f"PRD must be a Markdown file: {source_prd}")

    moved = False
    if is_standard_demand_prd(source_prd):
        demand_dir = source_prd.parent
        final_prd = source_prd
    else:
        demand_dir = source_prd.parent / source_prd.stem
        final_prd = demand_dir / source_prd.name
        if demand_dir.exists():
            fail(
                "Target demand folder already exists; stop to avoid inventing a parallel prototype folder: "
                f"{demand_dir}"
            )
        if final_prd.exists():
            fail(f"Target PRD already exists: {final_prd}")
        moved = True
        if not dry_run:
            demand_dir.mkdir(parents=False, exist_ok=False)
            shutil.move(str(source_prd), str(final_prd))

    prototype_dir = demand_dir / PROTOTYPE_DIRNAME
    if not dry_run:
        prototype_dir.mkdir(parents=True, exist_ok=True)
    index_path = prototype_dir / "index.html"
    shell_assets = copy_shell_assets(skill_root.resolve(), prototype_dir.resolve(), dry_run=dry_run)
    references = discover_references(demand_dir.resolve())
    recommended_action, reusable_fragment, legacy_candidates = choose_recommended_action(prototype_dir.resolve())
    existing_screen_change_detected = prd_mentions_existing_screen(final_prd if final_prd.exists() else source_prd)
    original_screen_candidates = find_original_screen_candidates(references)
    existing_screen_prompt_recommended = False
    agent_next_actions = list(references["agent_next_actions"])
    if original_screen_candidates:
        agent_next_actions.append("已发现疑似原界面图；生成前抽样查看并记录采用点。")
    elif existing_screen_change_detected:
        agent_next_actions.append("PRD 疑似在原有界面上修改但未发现原界面图；默认继续，仅在明确像素级复刻时再询问。")
    if references.get("design_context_warning"):
        agent_next_actions.append(str(references["design_context_warning"]))
    return {
        "ok": True,
        "dry_run": dry_run,
        "moved_prd": moved,
        "demand_dir": str(demand_dir.resolve()),
        "project_dir": str(demand_dir.resolve()),
        "prototype_dir": str(prototype_dir.resolve()),
        "prd_path": str(final_prd.resolve()),
        "index_path": str(index_path.resolve()),
        "prd_viewer_src": browser_relative_path(final_prd, prototype_dir),
        "stage_assets": shell_assets,
        "shell_assets": shell_assets,
        "references": references,
        "recommended_action": recommended_action,
        "reusable_fragment": str(reusable_fragment.resolve()) if reusable_fragment else None,
        "legacy_candidates": [str(item.resolve()) for item in legacy_candidates],
        "demand_reference_prompt_required": False,
        "existing_screen_change_detected": existing_screen_change_detected,
        "existing_screen_prompt_recommended": existing_screen_prompt_recommended,
        "original_screen_candidates": original_screen_candidates,
        "reference_images_found": references["reference_images_found"],
        "reference_usage_required": references["reference_usage_required"],
        "reference_status": "provided" if references["reference_images_found"] else "not_provided",
        "reference_prompt_policy": "continue_by_default",
        "original_screen_status": "available" if existing_screen_change_detected else "not_applicable",
        "original_screen_prompt_policy": "ask_only_when_blocking",
        "design_context_warning": references.get("design_context_warning"),
        "recommended_design_context": references.get("recommended_design_context"),
        "agent_next_actions": agent_next_actions,
    }


def clean_markdown_title(value: str) -> str:
    text = (value or "").strip().lstrip("\ufeff").strip()
    text = re.sub(r"^\s*#+\s*", "", text).strip()
    text = re.sub(r"\s+#+\s*$", "", text).strip()
    for pattern in (
        r"\*\*(.+?)\*\*",
        r"__(.+?)__",
        r"`(.+?)`",
        r"\*(.+?)\*",
        r"_(.+?)_",
    ):
        text = re.sub(pattern, r"\1", text).strip()
    return text


def read_prd_title(prd_path: Path) -> str:
    try:
        for line in prd_path.read_text(encoding="utf-8").splitlines():
            text = line.strip().lstrip("\ufeff").strip()
            if text.startswith("#"):
                return clean_markdown_title(text) or prd_path.stem
    except UnicodeDecodeError:
        pass
    return prd_path.stem


def default_generated_area(title: str) -> str:
    safe_title = html.escape(title)
    return f"""      <div class="proto-area-label"><span class="proto-generated-note">生成区 · 待补充</span></div>
      <section class="journey-row">
        <div class="journey-step is-active" id="step-1" data-proto-id="step-1" data-proto-label="{safe_title}">
          <div class="step-header">
            <span class="step-number">1</span>
            <span class="step-title">{safe_title}</span>
          </div>
          <div class="proto-generated-note">请将 PRD 讲解内容生成到这个区域。</div>
        </div>
      </section>"""


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def render_shell_index(
    skill_root: Path,
    prd_path: Path,
    title: str,
    lang: str,
    prd_viewer_src: str,
    generated_area: str,
    design_context: str,
) -> str:
    template_path = skill_root / "templates" / "html" / "prototype-shell.html"
    if not template_path.is_file():
        template_path = skill_root / "templates" / "prototype-shell.html"
    if not template_path.is_file():
        fail(f"Missing presentation-stage template: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    return render_template(
        template,
        {
            "lang": html.escape(lang, quote=True),
            "title": html.escape(title),
            "prd_viewer_src": html.escape(prd_viewer_src, quote=True),
            "generated_area": generated_area,
            "design_context": html.escape(design_context or "none"),
        },
    )


def extract_generated_fragment(raw: str) -> str:
    if START_MARKER in raw and END_MARKER in raw:
        return raw.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0].strip()

    match = re.search(r'<(?:main|div)\s+[^>]*class=["\'][^"\']*proto-generated-area[^"\']*["\'][^>]*>(.*?)</(?:main|div)>', raw, re.S)
    if match:
        return match.group(1).strip()
    return raw.strip()


def inject_generated_area(index_path: Path, fragment_path: Path) -> dict[str, object]:
    index = index_path.resolve()
    fragment = fragment_path.resolve()
    if not index.is_file():
        fail(f"index.html not found: {index}")
    if not fragment.is_file():
        fail(f"Generated area fragment not found: {fragment}")
    html_text = index.read_text(encoding="utf-8")
    if START_MARKER not in html_text or END_MARKER not in html_text:
        fail("Prototype generated-area markers are missing; refuse to replace arbitrary HTML.")
    fragment_text = extract_generated_fragment(fragment.read_text(encoding="utf-8"))
    updated = re.sub(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        START_MARKER + "\n" + fragment_text + "\n" + END_MARKER,
        html_text,
        flags=re.S,
    )
    prd_src = expected_prd_viewer_src(index.parent)
    if prd_src:
        updated = re.sub(r'(\bdata-prd-src=)(["\'])([^"\']*)(["\'])', lambda m: f"{m.group(1)}{m.group(2)}{html.escape(prd_src, quote=True)}{m.group(4)}", updated, count=1)
        updated = re.sub(r"(Source PRD:\s*)[^\r\n]*", lambda m: m.group(1) + prd_src, updated, count=1)
        updated = re.sub(
            r'(<p id="prd-viewer-fallback-message">当前绑定的 PRD 路径是：<code>)(.*?)(</code></p>)',
            lambda m: m.group(1) + html.escape(prd_src) + m.group(3),
            updated,
            count=1,
            flags=re.S,
        )
    index.write_text(updated, encoding="utf-8")
    return {"ok": True, "index_path": str(index), "fragment_path": str(fragment), "prd_viewer_src": prd_src}




def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json_file(path: Path) -> dict[str, object]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail(f"JSON file is not valid UTF-8: {path}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"JSON root must be an object: {path}")
    return data


def write_json_file(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_id(value: str, fallback: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9_-]+", "-", value or "").strip("-").lower()
    return raw or fallback


def short_hash(value: str, length: int = 8) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def stable_proto_id(prefix: str, value: str, context: str = "") -> str:
    slug = normalize_id(value, "")
    slug = slug[:42].strip("-")
    suffix = short_hash(f"{context}\n{value}")
    return f"{prefix}-{slug}-{suffix}" if slug else f"{prefix}-{suffix}"


def step_match_key(step: dict[str, object]) -> str:
    sections = [str(item).strip().lower() for item in step.get("prd_sections", []) or [] if str(item).strip()]
    title = str(step.get("title") or "").strip().lower()
    return " | ".join(sections or [title])


def extract_markdown_headings(text: str) -> list[dict[str, object]]:
    headings: list[dict[str, object]] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if not match:
            continue
        title = clean_markdown_title(match.group(2))
        headings.append({"level": len(match.group(1)), "title": title})
    return headings


def infer_platform_from_text(value: str) -> str:
    text = value.lower()
    if "ios" in text:
        return "Mobile App / iOS"
    if "android" in text or "安卓" in value:
        return "Mobile App / Android"
    if "web" in text or "网页" in value or "desktop" in text or "pc" in text:
        return "Web Page"
    return "Mobile App"


def title_contains_any(title: str, terms: set[str]) -> bool:
    lowered = title.lower()
    return any(term.lower() in lowered for term in terms)


def classify_prd_section(title: str, group_title: str = "") -> dict[str, str]:
    combined = f"{group_title} {title}".strip()
    title_text = title.strip()
    is_document = title_contains_any(combined, DOCUMENT_SECTION_TERMS)
    is_screen = title_contains_any(combined, STRONG_SCREEN_SECTION_TERMS)
    if is_document:
        if title_contains_any(combined, DELIVERY_NOTE_SECTION_TERMS):
            disposition = "delivery_note"
            reason = "section describes source, reference, delivery, or publishing context; keep it out of product screens"
        elif title_contains_any(combined, ANNOTATION_SECTION_TERMS) and len(title_text) <= 42:
            disposition = "annotation"
            reason = "section is explanatory context that should become a short annotation when tied to a screen"
        else:
            disposition = "prd_viewer"
            reason = "section is background, rules, fields, specs, acceptance, SOP, or other explanatory material"
        return {
            "disposition": disposition,
            "reason": reason,
            "decision_source": "auto_section_disposition",
        }
    if is_screen:
        return {
            "disposition": "screen",
            "reason": "section describes a user-visible page, state, modal, toast, or flow node",
            "decision_source": "auto_section_disposition",
        }
    return {
        "disposition": "prd_viewer",
        "reason": "section is not clearly a user-visible product state; keep it in PRD Viewer unless the plan is manually overridden",
        "decision_source": "auto_section_disposition",
    }


def make_disposition_record(title: str, group_title: str, classification: dict[str, str]) -> dict[str, object]:
    return {
        "prd_section": title,
        "group_title": group_title,
        "disposition": classification["disposition"],
        "reason": classification["reason"],
        "decision_source": classification["decision_source"],
    }


def build_steps_from_prd(prd_path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    prd_text = read_text_best_effort(prd_path)
    headings = extract_markdown_headings(prd_text)
    if not headings:
        title = read_prd_title(prd_path)
        step_id = stable_proto_id("step", title, "group-main")
        return [
            {
                "id": "group-main",
                "title": "Main flow",
                "description": "Default generation block created from the PRD.",
                "step_ids": [step_id],
            }
        ], [
            {
                "id": step_id,
                "title": title,
                "group_id": "group-main",
                "platform": "Mobile App",
                "prd_sections": [],
                "render_as": "screen",
                "screen_kind": "fallback",
                "eligibility_reason": "No markdown headings were found, so a single fallback product screen is required.",
                "state": "planned",
                "rendered": False,
                "notes": "Refine this step from the PRD before rendering.",
            }
        ], []

    groups: list[dict[str, object]] = []
    steps: list[dict[str, object]] = []
    dispositions: list[dict[str, object]] = []
    current_group_id = "group-main"
    current_group_title = "Main flow"

    def ensure_group(group_id: str, title: str) -> None:
        if not any(group["id"] == group_id for group in groups):
            groups.append({"id": group_id, "title": title, "description": "", "step_ids": []})

    ensure_group(current_group_id, current_group_title)
    for heading in headings:
        level = int(heading["level"])
        title = str(heading["title"])
        if level <= 2:
            continue
        if level == 3:
            current_group_title = title
            current_group_id = stable_proto_id("group", title)
            ensure_group(current_group_id, current_group_title)
            continue
        if level >= 4:
            classification = classify_prd_section(title, current_group_title)
            if classification["disposition"] != "screen":
                dispositions.append(make_disposition_record(title, current_group_title, classification))
                continue
            step_id = stable_proto_id("step", title, current_group_title)
            step = {
                "id": step_id,
                "title": title,
                "group_id": current_group_id,
                "platform": infer_platform_from_text(title + " " + current_group_title),
                "prd_sections": [title],
                "render_as": "screen",
                "screen_kind": "auto",
                "eligibility_reason": classification["reason"],
                "state": "planned",
                "rendered": False,
                "notes": "Auto-extracted from a PRD heading; refine before final rendering.",
            }
            steps.append(step)
            for group in groups:
                if group["id"] == current_group_id:
                    group.setdefault("step_ids", []).append(step_id)
                    break

    if not steps:
        for heading in headings:
            level = int(heading["level"])
            title = str(heading["title"])
            if level >= 2:
                classification = classify_prd_section(title, "Main flow")
                if classification["disposition"] != "screen":
                    dispositions.append(make_disposition_record(title, "Main flow", classification))
                    continue
                step_id = stable_proto_id("step", title, "group-main")
                steps.append(
                    {
                        "id": step_id,
                        "title": title,
                        "group_id": "group-main",
                        "platform": infer_platform_from_text(title),
                        "prd_sections": [title],
                        "render_as": "screen",
                        "screen_kind": "auto",
                        "eligibility_reason": classification["reason"],
                        "state": "planned",
                        "rendered": False,
                        "notes": "Auto-extracted from a PRD heading; refine before final rendering.",
                    }
                )
                groups[0].setdefault("step_ids", []).append(step_id)
    if not steps:
        title = read_prd_title(prd_path)
        step_id = stable_proto_id("step", title, "group-main")
        steps.append(
            {
                "id": step_id,
                "title": title,
                "group_id": "group-main",
                "platform": "Mobile App",
                "prd_sections": [],
                "render_as": "screen",
                "screen_kind": "fallback",
                "eligibility_reason": "The PRD did not expose user-visible screen headings after disposition filtering.",
                "state": "planned",
                "rendered": False,
                "notes": "Refine this step from the PRD before rendering.",
            }
        )
        groups[0].setdefault("step_ids", []).append(step_id)
    groups = [group for group in groups if group.get("step_ids")]
    return groups, steps, dispositions


def merge_existing_plan_steps(
    new_groups: list[dict[str, object]],
    new_steps: list[dict[str, object]],
    existing_plan: dict[str, object],
    reset: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    if reset or not existing_plan:
        return new_groups, new_steps, []

    old_steps = [step for step in (existing_plan.get("steps", []) if isinstance(existing_plan.get("steps"), list) else []) if isinstance(step, dict)]
    old_by_id = {str(step.get("id")): step for step in old_steps if step.get("id")}
    old_by_key: dict[str, dict[str, object]] = {}
    for step in old_steps:
        key = step_match_key(step)
        if key and key not in old_by_key:
            old_by_key[key] = step

    id_rewrites: dict[str, str] = {}
    merged_steps: list[dict[str, object]] = []
    matched_old_ids: set[str] = set()
    for step in new_steps:
        new_step = dict(step)
        old_step = old_by_id.get(str(step.get("id"))) or old_by_key.get(step_match_key(step))
        if old_step:
            old_id = str(old_step.get("id") or "")
            new_id = str(step.get("id") or "")
            if old_id and old_id != new_id:
                id_rewrites[new_id] = old_id
                new_step["id"] = old_id
            for key in ("title", "platform", "state", "rendered", "notes"):
                if key in old_step:
                    new_step[key] = old_step[key]
            for key in ("manual_notes", "source_notes"):
                if key in old_step and key not in new_step:
                    new_step[key] = old_step[key]
            matched_old_ids.add(old_id or str(step.get("id") or ""))
        merged_steps.append(new_step)

    merged_groups: list[dict[str, object]] = []
    old_groups = {
        str(group.get("id")): group
        for group in (existing_plan.get("groups", []) if isinstance(existing_plan.get("groups"), list) else [])
        if isinstance(group, dict) and group.get("id")
    }
    for group in new_groups:
        merged_group = dict(group)
        group_id = str(group.get("id") or "")
        old_group = old_groups.get(group_id)
        if old_group:
            for key in ("title", "description"):
                if key in old_group:
                    merged_group[key] = old_group[key]
        merged_group["step_ids"] = [id_rewrites.get(str(step_id), str(step_id)) for step_id in group.get("step_ids", []) or []]
        merged_groups.append(merged_group)

    removed_old_ids = sorted(
        str(step.get("id"))
        for step in old_steps
        if step.get("id") and str(step.get("id")) not in matched_old_ids
    )
    return merged_groups, merged_steps, removed_old_ids


def merge_disposition_records(
    new_dispositions: list[dict[str, object]],
    existing_coverage: dict[str, object],
) -> list[dict[str, object]]:
    existing_items = existing_coverage.get("disposition", []) if isinstance(existing_coverage.get("disposition"), list) else []
    existing_by_section: dict[str, dict[str, object]] = {}
    for item in existing_items:
        if not isinstance(item, dict):
            continue
        section = str(item.get("prd_section") or "").strip()
        if section and section not in existing_by_section:
            existing_by_section[section] = item

    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in new_dispositions:
        section = str(item.get("prd_section") or "").strip()
        if not section or section in seen:
            continue
        existing = existing_by_section.get(section)
        if existing:
            copied = dict(existing)
            copied.setdefault("disposition", item.get("disposition"))
            copied.setdefault("reason", item.get("reason"))
            copied.setdefault("decision_source", item.get("decision_source"))
            copied.setdefault("group_title", item.get("group_title"))
            merged.append(copied)
        else:
            merged.append(dict(item))
        seen.add(section)

    for section, item in existing_by_section.items():
        if section not in seen:
            merged.append(dict(item))
            seen.add(section)
    return merged


def default_plan_path_for_target(target: Path, out: str | None = None) -> Path:
    if out:
        return Path(out).expanduser().resolve()
    demand_dir, _prd_path, is_standard = resolve_preflight_target(target)
    if not is_standard or not demand_dir.exists():
        fail("prototype-plan.json must live in a standard demand folder; run scaffold first for loose PRDs.")
    return prototype_dir_for_target(demand_dir).resolve() / PLAN_FILENAME


def build_prototype_plan(
    target: Path,
    out: str | None = None,
    reference_prompt_handled: bool = False,
    existing_screen_prompt_handled: bool = False,
    reset: bool = False,
    generation_mode: str | None = None,
) -> dict[str, object]:
    preflight = build_preflight_result(target)
    demand_dir = Path(str(preflight["demand_dir"]))
    demand_root = demand_root_for_prototype(demand_dir)
    prd_value = preflight.get("prd_path")
    if not prd_value:
        fail("Cannot create prototype-plan.json without a source PRD in the demand folder.")
    prd_path = Path(str(prd_value))
    if not demand_dir.exists():
        fail("prototype-plan.json must live in a standard demand folder; run scaffold first for loose PRDs.")
    plan_path = default_plan_path_for_target(target, out)
    references = preflight.get("references", {}) if isinstance(preflight.get("references"), dict) else {}
    existing_plan = load_json_file(plan_path) if plan_path.exists() and not reset else {}
    existing_preflight = existing_plan.get("preflight", {}) if isinstance(existing_plan.get("preflight"), dict) else {}
    existing_coverage = existing_plan.get("coverage", {}) if isinstance(existing_plan.get("coverage"), dict) else {}
    existing_revision_history = existing_plan.get("revision_history", []) if isinstance(existing_plan.get("revision_history"), list) else []
    revision_history = list(existing_revision_history)
    if existing_plan:
        revision_history.append(
            {
                "at": utc_now_iso(),
                "action": "plan_updated",
                "summary": "Merged context plan from current PRD and preflight output.",
            }
        )
    groups, steps, dispositions = build_steps_from_prd(prd_path)
    groups, steps, removed_old_step_ids = merge_existing_plan_steps(groups, steps, existing_plan, reset=reset)
    dispositions = merge_disposition_records(dispositions, existing_coverage)
    if reset and plan_path.exists():
        revision_history.append(
            {
                "at": utc_now_iso(),
                "action": "plan_reset",
                "summary": "Rebuilt context plan from PRD headings because --reset was requested.",
            }
        )
    elif removed_old_step_ids:
        revision_history.append(
            {
                "at": utc_now_iso(),
                "action": "plan_removed_steps_detected",
                "summary": "PRD headings no longer matched existing plan steps; removed old ids: " + ", ".join(removed_old_step_ids[:20]),
            }
        )
    all_sections: list[str] = []
    for step in steps:
        all_sections.extend(str(item) for item in step.get("prd_sections", []))
    disposition_sections = [str(item.get("prd_section")) for item in dispositions if isinstance(item, dict) and item.get("prd_section")]
    source_reference_status = "provided" if bool(preflight.get("reference_images_found")) else "not_provided"
    original_screen_status = "available" if bool(preflight.get("existing_screen_change_detected")) else "not_applicable"

    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": str(existing_plan.get("created_at") or utc_now_iso()),
        "updated_at": utc_now_iso(),
        "generation_mode": generation_mode or str(existing_plan.get("generation_mode") or "content_package"),
        "source": {
            "prd_path": browser_relative_path(prd_path, demand_dir),
            "demand_dir": str(demand_root.resolve()),
            "prototype_dir": str(demand_dir.resolve()),
            "design_context": references.get("recommended_design_context") or references.get("design_md"),
        },
        "preflight": {
            "recommended_action": preflight.get("recommended_action"),
            "reference_status": str(existing_preflight.get("reference_status") or source_reference_status),
            "reference_prompt_policy": "continue_by_default",
            "original_screen_status": str(existing_preflight.get("original_screen_status") or original_screen_status),
            "original_screen_prompt_policy": "ask_only_when_blocking",
            "demand_reference_prompt_required": False,
            "demand_reference_prompt_handled": True,
            "existing_screen_prompt_recommended": False,
            "existing_screen_prompt_handled": True,
            "legacy_candidates": preflight.get("legacy_candidates", []),
            "reference_images_found": bool(preflight.get("reference_images_found")),
            "reference_usage_required": bool(preflight.get("reference_usage_required")),
            "source_audit": {
                "reference_status": str(existing_preflight.get("reference_status") or source_reference_status),
                "original_screen_status": str(existing_preflight.get("original_screen_status") or original_screen_status),
                "prompt_policy": "Continue without interrupting unless the user explicitly asks for pixel-level replication or the PRD is blocked by missing original-screen material.",
            },
        },
        "groups": groups,
        "steps": steps,
        "coverage": {
            "covered_prd_sections": existing_coverage.get("covered_prd_sections", []) if isinstance(existing_coverage.get("covered_prd_sections", []), list) else [],
            "planned_prd_sections": sorted(set(all_sections)),
            "all_prd_sections": sorted(set(all_sections + disposition_sections)),
            "disposition": dispositions,
            "omitted": existing_coverage.get("omitted", []) if isinstance(existing_coverage.get("omitted", []), list) else [],
            "notes": str(existing_coverage.get("notes") or "The PRD remains the source of truth; this plan only controls generation context and coverage tracking."),
        },
        "references_available": references.get("all_reference_images", []),
        "references_used": existing_plan.get("references_used", []) if isinstance(existing_plan.get("references_used", []), list) else [],
        "validation": {
            "last_strict_ok": None,
            "failures": [],
            "warnings": ["Plan updated; rerun init-content/build-content and final-check before final delivery."] if existing_plan else [],
        },
        "revision_history": revision_history,
    }
    write_json_file(plan_path, plan)
    return {"ok": True, "plan_path": str(plan_path), "plan": plan, "summary": summarize_prototype_plan(plan)}


def summarize_prototype_plan(plan: dict[str, object]) -> dict[str, object]:
    groups = plan.get("groups", []) if isinstance(plan.get("groups"), list) else []
    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    preflight = plan.get("preflight", {}) if isinstance(plan.get("preflight"), dict) else {}
    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    return {
        "generation_mode": plan.get("generation_mode"),
        "group_count": len(groups),
        "step_count": len(steps),
        "rendered_step_count": sum(1 for step in steps if isinstance(step, dict) and step.get("rendered")),
        "screen_step_count": sum(1 for step in steps if isinstance(step, dict) and str(step.get("render_as") or "screen") == "screen"),
        "omitted_count": len(coverage.get("omitted", [])) if isinstance(coverage.get("omitted"), list) else 0,
        "disposition_count": len(coverage.get("disposition", [])) if isinstance(coverage.get("disposition"), list) else 0,
        "reference_status": preflight.get("reference_status"),
        "preflight_prompts": {
            "demand_reference_prompt_required": preflight.get("demand_reference_prompt_required"),
            "demand_reference_prompt_handled": preflight.get("demand_reference_prompt_handled"),
            "existing_screen_prompt_recommended": preflight.get("existing_screen_prompt_recommended"),
            "existing_screen_prompt_handled": preflight.get("existing_screen_prompt_handled"),
        },
    }


def omitted_covers_step(step: dict[str, object], omitted: list[dict[str, object]]) -> bool:
    step_id = str(step.get("id") or "")
    sections = {str(item) for item in step.get("prd_sections", []) or []}
    for item in omitted:
        if str(item.get("step_id") or "") == step_id:
            return True
        omitted_section = str(item.get("prd_section") or "")
        if omitted_section and omitted_section in sections:
            return True
    return False


def validate_prototype_plan(plan: dict[str, object], final: bool = False) -> dict[str, object]:
    failures: list[str] = []
    warnings: list[str] = []
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        failures.append(f"prototype-plan.json schema_version must be {PLAN_SCHEMA_VERSION}.")
    generation_mode = str(plan.get("generation_mode") or "")
    if generation_mode and generation_mode not in PLAN_GENERATION_MODES:
        failures.append("generation_mode must be one of: content_package, legacy_fragment, showcase.")
    if not generation_mode:
        warnings.append("prototype-plan.json is missing generation_mode; treating it as legacy_fragment until the plan is refreshed.")
    for key in ("source", "preflight", "groups", "steps", "coverage", "references_used", "validation", "revision_history"):
        if key not in plan:
            failures.append(f"Missing field: {key}.")
    source = plan.get("source", {}) if isinstance(plan.get("source"), dict) else {}
    if not source.get("prd_path"):
        failures.append("source.prd_path is required.")
    preflight = plan.get("preflight", {}) if isinstance(plan.get("preflight"), dict) else {}
    if not preflight.get("reference_status"):
        warnings.append("preflight.reference_status is missing; refresh the plan so missing reference images are recorded without blocking generation.")
    if not preflight.get("reference_prompt_policy"):
        warnings.append("preflight.reference_prompt_policy is missing; refresh the plan to use the continue-by-default reference policy.")

    groups = plan.get("groups", []) if isinstance(plan.get("groups"), list) else []
    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    if not isinstance(plan.get("groups", []), list):
        failures.append("groups must be an array.")
    if not isinstance(plan.get("steps", []), list):
        failures.append("steps must be an array.")
    if not steps:
        failures.append("steps cannot be empty.")
    step_ids: set[str] = set()
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            failures.append(f"steps[{index}] must be an object.")
            continue
        step_id = str(step.get("id") or "")
        if not step_id:
            failures.append(f"steps[{index}] is missing id.")
        elif step_id in step_ids:
            failures.append(f"Duplicate step id: {step_id}.")
        step_ids.add(step_id)
        if not step.get("title"):
            failures.append(f"{step_id or f'steps[{index}]'} is missing title.")
        render_as = str(step.get("render_as") or "screen")
        if render_as not in PLAN_DISPOSITIONS:
            failures.append(f"{step_id or f'steps[{index}]'} has invalid render_as '{render_as}'.")
        if render_as != "screen":
            failures.append(f"{step_id or f'steps[{index}]'} is in steps but render_as is '{render_as}'; non-screen PRD material belongs in coverage.disposition.")
        if not step.get("prd_sections"):
            warnings.append(f"{step_id or f'steps[{index}]'} has no linked PRD section; verify coverage tracking.")
    for group in groups:
        if not isinstance(group, dict):
            failures.append("groups contains a non-object item.")
            continue
        for step_id in group.get("step_ids", []) or []:
            if step_id not in step_ids:
                failures.append(f"group {group.get('id')} references a missing step: {step_id}.")
        if len(group.get("step_ids", []) or []) > 4:
            warnings.append(f"group {group.get('id') or group.get('title')} has many steps; the canvas wraps, but splitting may reduce generation context.")

    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    disposition = coverage.get("disposition", []) if isinstance(coverage.get("disposition", []), list) else []
    if "disposition" not in coverage:
        warnings.append("coverage.disposition is missing; refresh the plan so non-screen PRD sections are tracked.")
    for index, item in enumerate(disposition, start=1):
        if not isinstance(item, dict):
            failures.append(f"coverage.disposition[{index}] must be an object.")
            continue
        if not item.get("prd_section"):
            failures.append(f"coverage.disposition[{index}] must include prd_section.")
        disposition_value = str(item.get("disposition") or "")
        if disposition_value not in PLAN_DISPOSITIONS:
            failures.append(f"coverage.disposition[{index}] has invalid disposition '{disposition_value}'.")
        if disposition_value == "screen":
            failures.append(f"coverage.disposition[{index}] is marked screen; screen sections must be steps instead.")
        if not item.get("reason"):
            failures.append(f"coverage.disposition[{index}] must include reason.")
        if not item.get("decision_source"):
            failures.append(f"coverage.disposition[{index}] must include decision_source.")
    omitted = coverage.get("omitted", []) if isinstance(coverage.get("omitted", []), list) else []
    omitted_coverage: list[dict[str, object]] = []
    for index, item in enumerate(omitted, start=1):
        if not isinstance(item, dict):
            failures.append(f"coverage.omitted[{index}] must be an object with step_id or prd_section, reason, and decision_source.")
            continue
        has_target = bool(item.get("step_id") or item.get("prd_section"))
        if not has_target:
            failures.append(f"coverage.omitted[{index}] must include step_id or prd_section.")
        if not item.get("reason"):
            failures.append(f"coverage.omitted[{index}] must include reason.")
        if not item.get("decision_source"):
            failures.append(f"coverage.omitted[{index}] must include decision_source.")
        if has_target:
            omitted_coverage.append(item)
    unrendered = [step for step in steps if isinstance(step, dict) and not step.get("rendered") and step.get("state") != "omitted"]
    unexplained_unrendered = [step for step in unrendered if not omitted_covers_step(step, omitted_coverage)]
    if final and unexplained_unrendered:
        failures.append("The plan has unrendered steps and coverage.omitted does not explain them; do not treat it as final delivery.")
    return {"ok": not failures, "failures": failures, "warnings": warnings, "summary": summarize_prototype_plan(plan)}


def validate_plan_source_contract(plan: dict[str, object], plan_path: Path) -> list[str]:
    failures: list[str] = []
    prototype_dir = plan_path.parent.resolve()
    demand_root = demand_root_for_prototype(prototype_dir)
    source = plan.get("source", {}) if isinstance(plan.get("source"), dict) else {}
    prd_src = str(source.get("prd_path") or "").strip()
    if not prd_src:
        failures.append("source.prd_path is required.")
    else:
        prd_file, prd_error = resolve_plan_prd_source(prototype_dir, prd_src)
        if prd_error:
            failures.append(f"source.prd_path must be a local path: {prd_src}")
        elif not prd_file or not prd_file.is_file():
            failures.append(f"source.prd_path file not found: {prd_src}")
        else:
            try:
                prd_file.relative_to(demand_root)
            except ValueError:
                failures.append(f"source.prd_path must stay inside the demand folder: {prd_src}")
    prototype_src = str(source.get("prototype_dir") or "").strip()
    if not prototype_src:
        failures.append("source.prototype_dir is required.")
    elif Path(prototype_src).expanduser().resolve() != prototype_dir:
        failures.append(f"source.prototype_dir must match this prototype folder: {prototype_src}")
    demand_src = str(source.get("demand_dir") or "").strip()
    if not demand_src:
        failures.append("source.demand_dir is required.")
    elif Path(demand_src).expanduser().resolve() != demand_root:
        failures.append(f"source.demand_dir must match the parent demand folder: {demand_src}")
    return failures


def validate_plan_file(plan_path: Path, final: bool = False) -> dict[str, object]:
    plan = load_json_file(plan_path.resolve())
    result = validate_prototype_plan(plan, final=final)
    source_failures = validate_plan_source_contract(plan, plan_path.resolve())
    if source_failures:
        result["failures"].extend(source_failures)
        result["ok"] = False
    return {"plan_path": str(plan_path.resolve()), **result}


def escape_attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_package_paths(demand_dir: Path) -> dict[str, Path]:
    demand = prototype_dir_for_target(demand_dir)
    content_dir = demand / CONTENT_DIRNAME
    return {
        "demand_dir": demand,
        "content_dir": content_dir,
        "manifest": content_dir / CONTENT_MANIFEST_FILENAME,
        "content_css": content_dir / CONTENT_CSS_FILENAME,
        "screens_dir": content_dir / CONTENT_SCREENS_DIRNAME,
        "plan": demand / PLAN_FILENAME,
        "fragment": demand / "generated-area-fragment.html",
        "index": demand / "index.html",
    }


def has_content_package(demand_dir: Path) -> bool:
    paths = content_package_paths(demand_dir)
    return paths["manifest"].is_file() or paths["content_dir"].is_dir()


def default_content_namespace(demand_dir: Path) -> str:
    namespace = normalize_id(f"{demand_dir.parent.name}-{demand_dir.name}", "pc-content")
    if not re.match(r"^[A-Za-z]", namespace):
        namespace = f"pc-{namespace}"
    if namespace.split("-", 1)[0] in RESERVED_CONTENT_NAMESPACE_PREFIXES:
        namespace = f"pc-{namespace}"
    return namespace


def css_scope_failures(css_text: str, namespace: str) -> list[str]:
    failures: list[str] = []
    if not css_text.strip() or not namespace:
        return failures
    css = re.sub(r"/\*.*?\*/", "", css_text.lstrip("\ufeff"), flags=re.S)
    css = re.sub(r"@keyframes\s+[^{]+\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)
    selector_pattern = re.compile(r"([^{}]+)\{", re.S)
    for match in selector_pattern.finditer(css):
        selector_block = match.group(1).strip()
        if not selector_block or selector_block.startswith("@"):
            continue
        for selector in [part.strip() for part in selector_block.split(",") if part.strip()]:
            if selector in {"from", "to"} or re.match(r"^\d+%$", selector):
                continue
            if not (
                selector == f".{namespace}"
                or selector.startswith(f".{namespace} ")
                or selector.startswith(f".{namespace}.")
                or selector.startswith(f".{namespace}:")
                or selector.startswith(f".{namespace}[")
            ):
                failures.append(f"content.css selector must be scoped under .{namespace}: {selector}")
    return failures


def html_class_count(text: str, class_name: str) -> int:
    count = 0
    for class_value in re.findall(r"\bclass=[\"']([^\"']*)[\"']", text, flags=re.I):
        if class_name in class_value.split():
            count += 1
    return count


def screen_filename_for_step(step_id: str) -> str:
    return f"{normalize_id(step_id, 'step')}.html"


TEXT_EDIT_LEAF_TAGS = ("h1", "h2", "h3", "h4", "p", "li", "small", "strong", "span", "label", "button", "a", "td", "th", "div")
TEXT_EDIT_LEAF_RE = re.compile(
    r"<(?P<tag>h[1-4]|p|li|small|strong|span|label|button|a|td|th|div)\b(?P<attrs>[^>]*)>"
    r"(?P<text>[^<]{1,240})"
    r"</(?P=tag)>",
    re.I,
)


def normalize_text_edit_ids(text: str, step_id: str) -> tuple[str, int]:
    counter = 0
    added = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal counter, added
        tag = match.group("tag")
        attrs = match.group("attrs") or ""
        body = match.group("text") or ""
        visible = clean_patch_text(html.unescape(body))
        if not visible or len(visible) > 120:
            return match.group(0)
        if re.search(r"\bdata-proto-id\s*=", attrs, flags=re.I):
            return match.group(0)
        if re.search(r"\bdata-proto-editable\s*=\s*([\"'])false\1", attrs, flags=re.I):
            return match.group(0)
        if not visible.strip("·•-–—:：,，.。/\\|()（）[]【】 "):
            return match.group(0)
        counter += 1
        fingerprint = hashlib.sha1(f"{step_id}|{tag.lower()}|{counter}|{visible}".encode("utf-8")).hexdigest()[:8]
        proto_id = normalize_id(f"{step_id}-{tag.lower()}-{counter}-{fingerprint}", "text")
        label = visible[:40]
        added += 1
        return (
            f'<{tag}{attrs} data-proto-id="{escape_attr(proto_id)}" '
            f'data-proto-label="{escape_attr(label)}">{body}</{tag}>'
        )

    return TEXT_EDIT_LEAF_RE.sub(replace, text), added


def safe_content_relative_path(content_dir: Path, value: object) -> tuple[Path | None, str | None]:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw:
        return None, "screen file path is required."
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        return None, f"screen file path must stay inside {CONTENT_DIRNAME}: {raw}"
    resolved = (content_dir / rel).resolve()
    try:
        resolved.relative_to(content_dir.resolve())
    except ValueError:
        return None, f"screen file path escapes {CONTENT_DIRNAME}: {raw}"
    return resolved, None


def try_load_json_object(path: Path) -> tuple[dict[str, object] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, f"Missing JSON file: {path}"
    except UnicodeDecodeError:
        return None, f"JSON file is not valid UTF-8: {path}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path}: {exc}"
    if not isinstance(data, dict):
        return None, f"JSON root must be an object: {path}"
    return data, None


def ordered_plan_steps(plan: dict[str, object]) -> list[dict[str, object]]:
    steps = [step for step in (plan.get("steps", []) if isinstance(plan.get("steps"), list) else []) if isinstance(step, dict)]
    step_map = {str(step.get("id")): step for step in steps if step.get("id")}
    ordered: list[dict[str, object]] = []
    seen: set[str] = set()
    groups = plan.get("groups", []) if isinstance(plan.get("groups"), list) else []
    for group in groups:
        if not isinstance(group, dict):
            continue
        for step_id in group.get("step_ids", []) or []:
            key = str(step_id)
            if key in step_map and key not in seen:
                ordered.append(step_map[key])
                seen.add(key)
    for step in steps:
        key = str(step.get("id") or "")
        if key and key not in seen:
            ordered.append(step)
            seen.add(key)
    return ordered


def plan_group_title_map(plan: dict[str, object]) -> dict[str, str]:
    groups = plan.get("groups", []) if isinstance(plan.get("groups"), list) else []
    return {
        str(group.get("id")): str(group.get("title") or group.get("id") or "Generation block")
        for group in groups
        if isinstance(group, dict) and group.get("id")
    }


def default_content_manifest(plan: dict[str, object], demand_dir: Path, existing: dict[str, object] | None = None) -> dict[str, object]:
    existing = existing or {}
    existing_screens = existing.get("screens", []) if isinstance(existing.get("screens"), list) else []
    existing_by_id = {
        str(item.get("step_id")): item
        for item in existing_screens
        if isinstance(item, dict) and item.get("step_id")
    }
    now = utc_now_iso()
    screens: list[dict[str, object]] = []
    for step in ordered_plan_steps(plan):
        if step.get("state") == "omitted":
            continue
        if str(step.get("render_as") or "screen") != "screen":
            continue
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        old = existing_by_id.get(step_id, {})
        file_value = str(old.get("file") or f"{CONTENT_SCREENS_DIRNAME}/{screen_filename_for_step(step_id)}")
        screens.append(
            {
                "step_id": step_id,
                "file": file_value,
                "title": str(step.get("title") or old.get("title") or step_id),
                "group_id": str(step.get("group_id") or old.get("group_id") or "group-main"),
                "platform": str(step.get("platform") or old.get("platform") or "Mobile App"),
                "prd_sections": list(step.get("prd_sections", []) or old.get("prd_sections", []) or []),
                "status": str(old.get("status") or "planned"),
                "hash": str(old.get("hash") or ""),
                "notes": str(old.get("notes") or ""),
            }
        )
    existing_source = existing.get("source", {}) if isinstance(existing.get("source"), dict) else {}
    return {
        "schema_version": CONTENT_SCHEMA_VERSION,
        "created_at": str(existing.get("created_at") or now),
        "updated_at": now,
        "namespace": str(existing.get("namespace") or default_content_namespace(demand_dir)),
        "source": {
            "plan_path": str(existing_source.get("plan_path") or PLAN_FILENAME),
            "prd_path": str((plan.get("source", {}) if isinstance(plan.get("source"), dict) else {}).get("prd_path") or ""),
        },
        "screens": screens,
        "build": existing.get("build") if isinstance(existing.get("build"), dict) else {},
    }


def render_screen_stub(screen: dict[str, object]) -> str:
    step_id = str(screen.get("step_id") or "step")
    title = str(screen.get("title") or step_id)
    safe_title = html.escape(title)
    escaped_step = escape_attr(step_id)
    return f'''<div class="phone-frame" data-proto-id="{escaped_step}-phone" data-proto-label="{safe_title} phone">
  <div class="phone-screen">
    <div class="app-screen" data-proto-id="{escaped_step}-screen" data-proto-label="{safe_title} screen" data-proto-placeholder="true">
      <div class="phone-status-bar"><span>12:30</span><span>5G</span></div>
      <div class="nav-bar"><span class="nav-icon"><i data-lucide="chevron-left"></i></span><span class="nav-title">{safe_title}</span><span class="nav-icon"><i data-lucide="more-horizontal"></i></span></div>
      <div class="app-content" style="flex:1;min-height:0;padding:18px 16px;background:#f7f9fc;">
        <div data-proto-id="{escaped_step}-stub" data-proto-label="{safe_title} stub" style="background:#fff;border:1px dashed #cbd5e1;border-radius:16px;padding:18px;color:#64748b;font-size:13px;line-height:1.5;">
          Replace this stub with the real PRD screen before final delivery.
        </div>
      </div>
      <div class="phone-home-indicator"></div>
    </div>
  </div>
</div>
'''


def init_content_package(demand_dir: Path) -> dict[str, object]:
    paths = content_package_paths(demand_dir)
    demand = paths["demand_dir"]
    plan_path = paths["plan"]
    if not demand.is_dir():
        fail(f"Demand folder not found: {demand}")
    if not plan_path.is_file():
        fail(f"prototype-plan.json is required before initializing a content package: {plan_path}")
    plan = load_json_file(plan_path)
    paths["content_dir"].mkdir(parents=True, exist_ok=True)
    paths["screens_dir"].mkdir(parents=True, exist_ok=True)
    if not paths["content_css"].exists():
        namespace = default_content_namespace(demand)
        paths["content_css"].write_text(
            f"/* Scope all business UI styles under .{namespace}. Do not target shell .proto-* / .journey-* classes. */\n"
            f".{namespace} {{\n"
            "  color: #111827;\n"
            "}\n",
            encoding="utf-8",
        )
    existing: dict[str, object] | None = None
    if paths["manifest"].exists():
        existing, error = try_load_json_object(paths["manifest"])
        if error:
            fail(error)
    manifest = default_content_manifest(plan, demand, existing)
    created_stubs: list[str] = []
    for screen in manifest.get("screens", []) if isinstance(manifest.get("screens"), list) else []:
        if not isinstance(screen, dict) or str(screen.get("status") or "") == "omitted":
            continue
        screen_path, path_error = safe_content_relative_path(paths["content_dir"], screen.get("file"))
        if path_error or screen_path is None:
            continue
        if not screen_path.exists():
            screen_path.parent.mkdir(parents=True, exist_ok=True)
            screen_path.write_text(render_screen_stub(screen), encoding="utf-8")
            created_stubs.append(str(screen_path))
    write_json_file(paths["manifest"], manifest)
    return {
        "ok": True,
        "demand_dir": str(demand),
        "content_dir": str(paths["content_dir"]),
        "manifest_path": str(paths["manifest"]),
        "screens_dir": str(paths["screens_dir"]),
        "content_css": str(paths["content_css"]),
        "screen_count": len(manifest.get("screens", [])),
        "created_stub_count": len(created_stubs),
        "created_stubs": created_stubs,
        "namespace": manifest.get("namespace"),
    }


def validate_content_package(
    demand_dir: Path,
    strict: bool = False,
    final: bool = False,
    require_fresh_hashes: bool = False,
) -> dict[str, object]:
    paths = content_package_paths(demand_dir)
    demand = paths["demand_dir"]
    content_dir = paths["content_dir"]
    manifest_path = paths["manifest"]
    plan_path = paths["plan"]
    failures: list[str] = []
    warnings: list[str] = []
    screen_records: list[dict[str, object]] = []
    manifest: dict[str, object] | None = None
    plan: dict[str, object] | None = None

    if not demand.is_dir():
        failures.append(f"Demand folder not found: {demand}")
    if not manifest_path.is_file():
        failures.append(f"Missing content manifest: {manifest_path}")
    else:
        manifest, error = try_load_json_object(manifest_path)
        if error:
            failures.append(error)
    if not plan_path.is_file():
        failures.append(f"Missing prototype-plan.json: {plan_path}")
    else:
        plan, error = try_load_json_object(plan_path)
        if error:
            failures.append(error)

    if failures:
        return {
            "ok": False,
            "status": "failed",
            "strict": strict,
            "paths": {key: str(value) for key, value in paths.items()},
            "failures": failures,
            "warnings": warnings,
            "summary": {},
        }

    assert manifest is not None
    assert plan is not None
    if manifest.get("schema_version") != CONTENT_SCHEMA_VERSION:
        failures.append(f"prototype-content/manifest.json schema_version must be {CONTENT_SCHEMA_VERSION}.")
    namespace = str(manifest.get("namespace") or "").strip()
    if not namespace:
        failures.append("prototype-content/manifest.json must include namespace.")
    elif not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", namespace):
        failures.append("content namespace must be a CSS class-friendly identifier starting with a letter.")
    elif namespace.split("-", 1)[0] in RESERVED_CONTENT_NAMESPACE_PREFIXES:
        failures.append("content namespace must not start with reserved shell prefixes: proto, journey, step.")

    screens = manifest.get("screens", [])
    if not isinstance(screens, list):
        failures.append("prototype-content/manifest.json screens must be an array.")
        screens = []
    if not screens:
        warnings.append("prototype-content/manifest.json has no screens; this content package is still a draft.")

    plan_steps = ordered_plan_steps(plan)
    plan_ids = [str(step.get("id")) for step in plan_steps if step.get("id")]
    plan_id_set = set(plan_ids)
    manifest_ids: list[str] = []
    seen_manifest_ids: set[str] = set()
    internal_html_ids: dict[str, str] = {}
    current_hash_count = 0
    missing_hash_count = 0

    content_css_text = ""
    if paths["content_css"].is_file():
        try:
            content_css_text = paths["content_css"].read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"content.css is not valid UTF-8: {paths['content_css']}")
        css_for_scan = re.sub(r"/\*.*?\*/", "", content_css_text, flags=re.S)
        for pattern, message in CONTENT_CSS_FORBIDDEN_PATTERNS:
            if re.search(pattern, css_for_scan, re.I | re.M):
                (failures if strict else warnings).append(message)
        scope_failures = css_scope_failures(content_css_text, namespace)
        if scope_failures:
            (failures if strict else warnings).extend(scope_failures[:12])
    else:
        warnings.append(f"Missing {CONTENT_CSS_FILENAME}; build-content will still work, but business styles should be scoped in content.css.")

    for index, item in enumerate(screens, start=1):
        if not isinstance(item, dict):
            failures.append(f"screens[{index}] must be an object.")
            continue
        step_id = str(item.get("step_id") or "").strip()
        if not step_id:
            failures.append(f"screens[{index}] is missing step_id.")
            continue
        if step_id in seen_manifest_ids:
            failures.append(f"Duplicate screen step_id in manifest: {step_id}.")
        seen_manifest_ids.add(step_id)
        manifest_ids.append(step_id)
        if step_id not in plan_id_set:
            failures.append(f"Screen step_id is not present in prototype-plan.json: {step_id}.")
        if not item.get("title"):
            warnings.append(f"{step_id} has no title in manifest; build-content will fall back to step_id.")
        if str(item.get("status") or "planned") not in {"planned", "draft", "rendered", "omitted"}:
            failures.append(f"{step_id} has invalid status: {item.get('status')}.")
        screen_path, path_error = safe_content_relative_path(content_dir, item.get("file"))
        if path_error or screen_path is None:
            failures.append(f"{step_id}: {path_error}")
            continue
        if not screen_path.is_file():
            failures.append(f"{step_id}: missing screen file: {screen_path}")
            continue
        try:
            screen_text = screen_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"{step_id}: screen file is not valid UTF-8: {screen_path}")
            continue
        if not screen_text.strip():
            failures.append(f"{step_id}: screen file is empty: {screen_path}")
        if "data-proto-placeholder" in screen_text or "Replace this stub" in screen_text:
            message = (
                f"{step_id}: screen source is still an init-content business placeholder. "
                "Replace prototype-content/screens/*.html with PRD-specific UI and rerun package-check/build-content; "
                "do not modify skill templates for this."
            )
            (failures if strict or final else warnings).append(message)
        for pattern, message in CONTENT_SCREEN_FORBIDDEN_PATTERNS:
            if re.search(pattern, screen_text, re.I):
                failures.append(f"{step_id}: {message}")
        for action in re.findall(r"\bdata-proto-action\s*=\s*[\"']([^\"']+)[\"']", screen_text, re.I):
            normalized_action = action.strip().lower()
            if normalized_action not in LIGHT_INTERACTION_ACTIONS:
                failures.append(
                    f"{step_id}: unsupported data-proto-action '{action}'. "
                    "Use only the declared light-interaction whitelist."
                )
        surface_count = html_class_count(screen_text, "phone-frame") + html_class_count(screen_text, "web-surface")
        if surface_count != 1:
            message = f"{step_id}: screen body must contain exactly one primary surface (.phone-frame or .web-surface); found {surface_count}."
            (failures if strict else warnings).append(message)
        for html_id in re.findall(r"(?<![-A-Za-z0-9_:])id\s*=\s*[\"']([^\"']+)[\"']", screen_text):
            message = f"{step_id}: raw id '{html_id}' may collide when spotlight clones the screen; prefer data-proto-id."
            (failures if strict else warnings).append(message)
            if html_id in internal_html_ids:
                warnings.append(f"Duplicate raw id across screen bodies: {html_id} in {step_id} and {internal_html_ids[html_id]}. Prefer data-proto-id for edit targets.")
            else:
                internal_html_ids[html_id] = step_id
        actual_hash = sha256_text(screen_text)
        declared_hash = str(item.get("hash") or "")
        if declared_hash and declared_hash == actual_hash:
            current_hash_count += 1
        elif declared_hash:
            message = f"{step_id}: screen hash differs from manifest; run build-content to refresh derived artifacts."
            (failures if require_fresh_hashes else warnings).append(message)
        else:
            missing_hash_count += 1
            if require_fresh_hashes:
                failures.append(f"{step_id}: screen hash missing; run build-content.")
        screen_records.append({"manifest": item, "step_id": step_id, "path": screen_path, "text": screen_text, "hash": actual_hash})

    manifest_order = [step_id for step_id in manifest_ids if step_id in plan_id_set]
    expected_order = [step_id for step_id in plan_ids if step_id in set(manifest_order)]
    if manifest_order != expected_order:
        message = "Manifest screen order differs from prototype-plan group order; run init-content or reorder manifest intentionally."
        (failures if strict else warnings).append(message)

    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    omitted = coverage.get("omitted", []) if isinstance(coverage.get("omitted"), list) else []
    omitted_items = [item for item in omitted if isinstance(item, dict)]
    missing_manifest_steps = [
        step_id
        for step_id in plan_ids
        if step_id not in seen_manifest_ids
        and not omitted_covers_step(next((step for step in plan_steps if str(step.get("id") or "") == step_id), {}), omitted_items)
    ]
    if missing_manifest_steps:
        message = "Plan steps are not represented in manifest screens or coverage.omitted: " + ", ".join(missing_manifest_steps[:12])
        (failures if final else warnings).append(message)

    status = "failed" if failures else "ready"
    if not failures and (missing_manifest_steps or missing_hash_count or any(str(item.get("status") or "planned") != "rendered" for item in screens if isinstance(item, dict))):
        status = "draft"
    if not failures and final and omitted:
        status = "partial"
    return {
        "ok": not failures,
        "status": status,
        "strict": strict,
        "paths": {key: str(value) for key, value in paths.items()},
        "failures": failures,
        "warnings": warnings,
        "summary": {
            "screen_count": len(screen_records),
            "manifest_screen_count": len(manifest_ids),
            "plan_step_count": len(plan_ids),
            "missing_manifest_step_count": len(missing_manifest_steps),
            "current_hash_count": current_hash_count,
            "missing_hash_count": missing_hash_count,
            "namespace": namespace,
        },
        "manifest": manifest,
        "plan": plan,
        "screen_records": screen_records,
    }


def render_content_package_fragment(manifest: dict[str, object], plan: dict[str, object], screen_records: list[dict[str, object]], content_css: str) -> str:
    namespace = str(manifest.get("namespace") or "proto-content")
    group_titles = plan_group_title_map(plan)
    step_by_id = {str(step.get("id")): step for step in ordered_plan_steps(plan) if step.get("id")}
    screen_by_id = {str(record["step_id"]): record for record in screen_records}
    screens = [item for item in (manifest.get("screens", []) if isinstance(manifest.get("screens"), list) else []) if isinstance(item, dict)]
    rendered: list[str] = [
        '<div class="proto-area-label"><span class="proto-generated-note">Generated area - Content package render</span></div>',
    ]
    if content_css.strip():
        rendered.append('<style data-proto-content-css data-proto-source="prototype-content/content.css">')
        rendered.append(content_css.strip())
        rendered.append("</style>")

    step_number = 1
    active_written = False
    current_group_id = ""
    current_row_count = 0
    row_open = False

    def close_row() -> None:
        nonlocal current_row_count, row_open
        if row_open:
            rendered.append("</section>")
        row_open = False
        current_row_count = 0

    def open_row() -> None:
        nonlocal row_open, current_row_count
        rendered.append('<section class="journey-row">')
        row_open = True
        current_row_count = 0

    for item in screens:
        step_id = str(item.get("step_id") or "")
        if not step_id or str(item.get("status") or "") == "omitted" or step_id not in screen_by_id:
            continue
        plan_step = step_by_id.get(step_id, {})
        group_id = str(plan_step.get("group_id") or item.get("group_id") or "group-main")
        if group_id != current_group_id:
            close_row()
            current_group_id = group_id
            group_title = group_titles.get(group_id, group_id or "Generation block")
            rendered.append(f'<div class="section-divider" data-proto-id="{escape_attr(group_id)}" data-proto-label="{escape_attr(group_title)}">{html.escape(group_title)}</div>')
        if not row_open or current_row_count >= 4:
            close_row()
            open_row()
        title = str(plan_step.get("title") or item.get("title") or step_id)
        active = " is-active" if not active_written else ""
        active_written = True
        body = str(screen_by_id[step_id]["text"]).strip()
        rendered.append(f'  <div class="journey-step{active}" id="{escape_attr(step_id)}" data-proto-id="{escape_attr(step_id)}" data-proto-label="{escape_attr(title)}">')
        rendered.append(f'    <div class="step-header"><span class="step-number">{step_number}</span><span class="step-title">{html.escape(title)}</span></div>')
        rendered.append(f'    <div class="{escape_attr(namespace)} proto-content-screen" data-proto-id="{escape_attr(step_id)}-content" data-proto-label="{escape_attr(title)} content">')
        rendered.append(indent_text(body, "      "))
        rendered.append("    </div>")
        rendered.append("  </div>")
        step_number += 1
        current_row_count += 1
    close_row()
    return "\n".join(rendered) + "\n"


def indent_text(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def sync_plan_with_content_package(plan: dict[str, object], manifest: dict[str, object], fragment_validation: dict[str, object]) -> None:
    plan["generation_mode"] = "content_package"
    rendered_ids = {
        str(item.get("step_id"))
        for item in manifest.get("screens", [])
        if isinstance(item, dict) and item.get("step_id") and str(item.get("status") or "") != "omitted"
    }
    for step in plan.get("steps", []) if isinstance(plan.get("steps"), list) else []:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        if not step_id or step.get("state") == "omitted":
            continue
        if step_id in rendered_ids:
            step["rendered"] = True
            step["state"] = "rendered"
        else:
            step["rendered"] = False
            step["state"] = "planned"
    update_plan_coverage_from_rendered(plan)
    plan["updated_at"] = utc_now_iso()
    plan["validation"] = {
        "last_strict_ok": bool(fragment_validation.get("ok")),
        "failures": fragment_validation.get("failures", []),
        "warnings": fragment_validation.get("warnings", []),
    }
    revision_history = plan.get("revision_history", [])
    if not isinstance(revision_history, list):
        revision_history = []
    revision_history.append(
        {
            "at": utc_now_iso(),
            "action": "content_package_built",
            "summary": "Built generated-area-fragment.html from prototype-content manifest and screen files.",
        }
    )
    plan["revision_history"] = revision_history


def build_content_package(
    demand_dir: Path,
    check: bool = False,
    update_plan: bool = True,
) -> dict[str, object]:
    paths = content_package_paths(demand_dir)
    validation = validate_content_package(paths["demand_dir"], strict=True, final=False, require_fresh_hashes=False)
    if not validation["ok"]:
        return {
            "ok": False,
            "status": "failed",
            "paths": validation.get("paths", {}),
            "failures": validation.get("failures", []),
            "warnings": validation.get("warnings", []),
            "package_validation": validation,
        }
    if not check:
        normalized_count = 0
        for record in validation.get("screen_records", []):
            if not isinstance(record, dict):
                continue
            screen_path = Path(record["path"])
            normalized_text, added = normalize_text_edit_ids(str(record.get("text") or ""), str(record.get("step_id") or "step"))
            if added and normalized_text != str(record.get("text") or ""):
                screen_path.write_text(normalized_text, encoding="utf-8")
                normalized_count += added
        if normalized_count:
            validation = validate_content_package(paths["demand_dir"], strict=True, final=False, require_fresh_hashes=False)
            if not validation["ok"]:
                return {
                    "ok": False,
                    "status": "failed",
                    "paths": validation.get("paths", {}),
                    "failures": validation.get("failures", []),
                    "warnings": validation.get("warnings", []),
                    "package_validation": validation,
                }
    manifest = validation["manifest"]
    plan = validation["plan"]
    screen_records = validation["screen_records"]
    content_css = paths["content_css"].read_text(encoding="utf-8") if paths["content_css"].is_file() else ""
    fragment_text = render_content_package_fragment(manifest, plan, screen_records, content_css)
    fragment_validation = validate_fragment_text(fragment_text, strict=True)
    if not fragment_validation["ok"]:
        return {
            "ok": False,
            "status": "failed",
            "paths": validation.get("paths", {}),
            "failures": [f"built fragment: {item}" for item in fragment_validation.get("failures", [])],
            "warnings": validation.get("warnings", []) + [f"built fragment: {item}" for item in fragment_validation.get("warnings", [])],
            "package_validation": validation,
            "fragment_validation": fragment_validation,
        }

    existing_fragment = ""
    fragment_exists = paths["fragment"].is_file()
    if fragment_exists:
        existing_fragment = extract_generated_fragment(paths["fragment"].read_text(encoding="utf-8")).strip() + "\n"
    if check:
        fresh = fragment_exists and existing_fragment == fragment_text
        return {
            "ok": fresh,
            "status": "ready" if fresh else "failed",
            "paths": validation.get("paths", {}),
            "failures": [] if fresh else ["generated-area-fragment.html is missing or stale; run build-content before final delivery."],
            "warnings": validation.get("warnings", []),
            "package_validation": validation,
            "fragment_validation": fragment_validation,
            "summary": {
                "screen_count": len(screen_records),
                "fragment_hash": sha256_text(fragment_text),
                "fresh": fresh,
            },
        }

    updated_manifest = dict(manifest)
    updated_screens: list[dict[str, object]] = []
    hash_by_id = {str(record["step_id"]): str(record["hash"]) for record in screen_records}
    for item in manifest.get("screens", []) if isinstance(manifest.get("screens"), list) else []:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        step_id = str(copied.get("step_id") or "")
        if step_id in hash_by_id and str(copied.get("status") or "") != "omitted":
            copied["hash"] = hash_by_id[step_id]
            copied["status"] = "rendered"
        updated_screens.append(copied)
    updated_manifest["screens"] = updated_screens
    updated_manifest["updated_at"] = utc_now_iso()
    updated_manifest["build"] = {
        "fragment_path": "generated-area-fragment.html",
        "last_built_at": utc_now_iso(),
        "fragment_hash": sha256_text(fragment_text),
        "content_css_hash": sha256_text(content_css),
    }
    paths["fragment"].write_text(fragment_text, encoding="utf-8")
    write_json_file(paths["manifest"], updated_manifest)
    if update_plan:
        plan_to_write = dict(plan)
        sync_plan_with_content_package(plan_to_write, updated_manifest, fragment_validation)
        write_json_file(paths["plan"], plan_to_write)
    return {
        "ok": True,
        "status": "ready",
        "paths": validation.get("paths", {}),
        "fragment_path": str(paths["fragment"]),
        "manifest_path": str(paths["manifest"]),
        "package_validation": validate_content_package(paths["demand_dir"], strict=True, final=False, require_fresh_hashes=True),
        "fragment_validation": fragment_validation,
        "summary": {
            "screen_count": len(screen_records),
            "fragment_hash": sha256_text(fragment_text),
        },
    }


def render_mobile_step(step: dict[str, object], number: int) -> str:
    step_id = escape_attr(step.get("id") or f"step-{number}")
    title = html.escape(str(step.get("title") or f"Step {number}"))
    platform = html.escape(str(step.get("platform") or "Mobile App"))
    notes = html.escape(str(step.get("notes") or "Refine this state from the PRD."))
    active = " is-active" if number == 1 else ""
    return f'''  <div class="journey-step{active}" id="{step_id}" data-proto-id="{step_id}" data-proto-label="{title}">
    <div class="step-header"><span class="step-number">{number}</span><span class="step-title">{title}</span></div>
    <div class="proto-surface-slot">
      <div class="phone-frame" data-proto-id="{step_id}-phone" data-proto-label="{title} phone screen">
        <div class="phone-screen">
          <div class="app-screen" data-proto-id="{step_id}-screen" data-proto-label="{title} screen">
            <div class="phone-status-bar"><span>12:30</span><span>5G</span></div>
            <div class="nav-bar"><span class="nav-icon"><i data-lucide="chevron-left"></i></span><span class="nav-title">{title}</span><span class="nav-icon"><i data-lucide="more-horizontal"></i></span></div>
            <div class="app-content" style="flex:1;min-height:0;padding:18px 16px;">
              <div class="pp-plan-panel" data-proto-id="{step_id}-content" data-proto-label="{title} content block" style="border:1px solid #e5e7eb;border-radius:16px;background:#fff;padding:16px;box-shadow:0 6px 18px rgba(15,23,42,.06);">
                <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">{platform}</div>
                <h3 style="margin:0 0 8px;font-size:16px;color:#111827;">{title}</h3>
                <p style="margin:0;color:#6b7280;font-size:13px;line-height:1.55;">{notes}</p>
              </div>
            </div>
            <div class="phone-home-indicator"></div>
          </div>
        </div>
      </div>
    </div>
  </div>'''


def render_web_step(step: dict[str, object], number: int) -> str:
    step_id = escape_attr(step.get("id") or f"step-{number}")
    title = html.escape(str(step.get("title") or f"Step {number}"))
    platform = html.escape(str(step.get("platform") or "Web Page"))
    notes = html.escape(str(step.get("notes") or "Refine this state from the PRD."))
    active = " is-active" if number == 1 else ""
    return f'''  <div class="journey-step{active}" id="{step_id}" data-proto-id="{step_id}" data-proto-label="{title}">
    <div class="step-header"><span class="step-number">{number}</span><span class="step-title">{title}</span></div>
    <div class="web-surface" data-proto-id="{step_id}-surface" data-proto-label="{title} screen" style="min-width:520px;max-width:720px;padding:20px;border-radius:16px;background:#fff;border:1px solid #e5e7eb;box-shadow:0 10px 30px rgba(15,23,42,.08);">
      <div data-proto-id="{step_id}-content" data-proto-label="{title} content block">
        <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">{platform}</div>
        <h3 style="margin:0 0 8px;font-size:18px;color:#111827;">{title}</h3>
        <p style="margin:0;color:#6b7280;font-size:14px;line-height:1.6;">{notes}</p>
      </div>
    </div>
  </div>'''


def render_fragment_from_plan(plan: dict[str, object]) -> str:
    groups = plan.get("groups", []) if isinstance(plan.get("groups"), list) else []
    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    step_map = {str(step.get("id")): step for step in steps if isinstance(step, dict)}
    rendered: list[str] = [
        '<div class="proto-area-label"><span class="proto-generated-note">Generated area - Context Plan render</span></div>',
        '<style>.pp-plan-panel strong{color:#111827;}</style>',
    ]
    number = 1
    if not groups:
        groups = [{"id": "group-main", "title": "Main flow", "step_ids": [step.get("id") for step in steps if isinstance(step, dict)]}]
    for group in groups:
        if not isinstance(group, dict):
            continue
        title = str(group.get("title") or group.get("id") or "Generation block")
        group_id = escape_attr(group.get("id") or normalize_id(title, "group"))
        rendered.append(f'<div class="section-divider" data-proto-id="{group_id}" data-proto-label="{escape_attr(title)}">{html.escape(title)}</div>')
        group_steps = [step_map[str(step_id)] for step_id in group.get("step_ids", []) or [] if str(step_id) in step_map]
        if not group_steps:
            continue
        for row_start in range(0, len(group_steps), 4):
            rendered.append('<section class="journey-row">')
            for step in group_steps[row_start : row_start + 4]:
                if step.get("state") == "omitted":
                    continue
                platform = str(step.get("platform") or "Mobile App").lower()
                rendered.append(render_web_step(step, number) if "web" in platform or "desktop" in platform else render_mobile_step(step, number))
                step["rendered"] = True
                step["state"] = "rendered"
                number += 1
            rendered.append('</section>')
    rendered.append('<script>if(window.lucide)window.lucide.createIcons();</script>')
    return "\n".join(rendered) + "\n"


def validate_fragment_text(text: str, strict: bool = False) -> dict[str, object]:
    failures: list[str] = []
    warnings: list[str] = []
    if "\ufffd" in text or re.search(r"\?{3,}", text):
        failures.append("fragment contains suspected mojibake or replacement characters.")
    if re.search(r"</?motion\b", text, re.I):
        failures.append("fragment contains suspected typo tag: motion.")
    generated_area = inspect_generated_area(text)
    strict_failures = generated_area.get("strict_failures", []) if isinstance(generated_area, dict) else []
    if strict and strict_failures:
        failures.extend(str(item) for item in strict_failures)
    warnings.extend(str(item) for item in generated_area.get("warnings", []) if isinstance(generated_area, dict))
    return {"ok": not failures, "strict": strict, "failures": failures, "warnings": warnings, "generated_area": generated_area}


def validate_fragment_file(fragment_path: Path, strict: bool = False) -> dict[str, object]:
    fragment = fragment_path.resolve()
    if not fragment.is_file():
        fail(f"fragment not found: {fragment}")
    try:
        text = fragment.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail(f"fragment is not valid UTF-8: {fragment}")
    result = validate_fragment_text(extract_generated_fragment(text), strict=strict)
    return {"fragment_path": str(fragment), **result}


class ProtoQualityInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, object]] = []
        self.steps: list[dict[str, object]] = []
        self.current_step: dict[str, object] | None = None
        self.annotation_stack: list[dict[str, object]] = []
        self.annotation_missing_proto_id = 0
        self.annotation_missing_proto_label = 0
        self.annotation_in_surface = 0
        self.long_annotations: list[str] = []
        self.annotation_structure_count = 0

    @staticmethod
    def classes_from_attrs(attrs: list[tuple[str, str | None]]) -> set[str]:
        raw = ""
        for key, value in attrs:
            if key.lower() == "class" and value:
                raw = value
                break
        return {item for item in raw.split() if item}

    @staticmethod
    def attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): value or "" for key, value in attrs}

    def has_surface_ancestor(self) -> bool:
        surface_classes = {"phone-frame", "phone-screen", "app-screen", "app-content", "web-surface"}
        return any(surface_classes.intersection(node["classes"]) for node in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        classes = self.classes_from_attrs(attrs)
        attr_map = self.attrs_dict(attrs)
        node = {"tag": tag, "classes": classes, "attrs": attr_map, "text": ""}
        class_blob = " ".join(sorted(classes | {attr_map.get("id", ""), attr_map.get("data-proto-label", "")})).strip()

        if "journey-step" in classes:
            self.current_step = {
                "id": attr_map.get("data-proto-id") or attr_map.get("id") or "",
                "label": attr_map.get("data-proto-label") or "",
                "text": "",
                "nav_titles": [],
                "surface_count": 0,
                "annotation_count": 0,
                "explanation_token_count": 0,
                "list_or_table_count": 0,
                "control_count": 0,
            }
            self.steps.append(self.current_step)

        if self.current_step is not None:
            if {"phone-frame", "web-surface"}.intersection(classes):
                self.current_step["surface_count"] = int(self.current_step["surface_count"]) + 1
            if QUALITY_EXPLANATION_CLASS_RE.search(class_blob):
                self.current_step["explanation_token_count"] = int(self.current_step["explanation_token_count"]) + 1
            if tag in {"ul", "ol", "table", "dl"}:
                self.current_step["list_or_table_count"] = int(self.current_step["list_or_table_count"]) + 1
            if tag in {"button", "input", "textarea", "select"}:
                self.current_step["control_count"] = int(self.current_step["control_count"]) + 1

        if "nav-title" in classes:
            node["is_nav_title"] = True

        if "annotation" in classes:
            annotation = {
                "id": attr_map.get("data-proto-id", ""),
                "label": attr_map.get("data-proto-label", ""),
                "text": "",
                "has_structure": False,
            }
            self.annotation_stack.append(annotation)
            if self.current_step is not None:
                self.current_step["annotation_count"] = int(self.current_step["annotation_count"]) + 1
            if not attr_map.get("data-proto-id"):
                self.annotation_missing_proto_id += 1
            if not attr_map.get("data-proto-label"):
                self.annotation_missing_proto_label += 1
            if self.has_surface_ancestor():
                self.annotation_in_surface += 1

        if self.annotation_stack and tag in {"ul", "ol", "table", "dl"}:
            self.annotation_stack[-1]["has_structure"] = True
            self.annotation_structure_count += 1

        self.stack.append(node)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        compact = " ".join(data.split())
        if not compact:
            return
        if self.current_step is not None:
            self.current_step["text"] = str(self.current_step["text"]) + " " + compact
            if any(term in compact for term in QUALITY_EXPLANATION_TERMS):
                self.current_step["explanation_token_count"] = int(self.current_step["explanation_token_count"]) + 1
            if any(node.get("is_nav_title") for node in self.stack):
                self.current_step["nav_titles"].append(compact)
        if self.annotation_stack:
            self.annotation_stack[-1]["text"] = str(self.annotation_stack[-1]["text"]) + " " + compact

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        while self.stack:
            node = self.stack.pop()
            if "annotation" in node["classes"] and self.annotation_stack:
                annotation = self.annotation_stack.pop()
                text = " ".join(str(annotation.get("text") or "").split())
                if len(text) > 180 or bool(annotation.get("has_structure")):
                    label = str(annotation.get("label") or annotation.get("id") or "annotation")
                    self.long_annotations.append(label)
            if "journey-step" in node["classes"]:
                self.current_step = None
            if node["tag"] == tag:
                break


def quality_plan_context(plan: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(plan, dict):
        return {
            "plan_step_count": 0,
            "plan_disposition_count": 0,
            "document_step_ids": set(),
            "disposition_sections": [],
        }
    showcase_mode = str(plan.get("generation_mode") or "") == "showcase"
    groups = {
        str(group.get("id")): str(group.get("title") or "")
        for group in (plan.get("groups", []) if isinstance(plan.get("groups"), list) else [])
        if isinstance(group, dict)
    }
    document_step_ids: set[str] = set()
    for step in plan.get("steps", []) if isinstance(plan.get("steps"), list) else []:
        if not isinstance(step, dict):
            continue
        if showcase_mode or bool(step.get("is_showcase_sample")):
            continue
        step_id = str(step.get("id") or "")
        title = str(step.get("title") or "")
        group_title = groups.get(str(step.get("group_id") or ""), "")
        classification = classify_prd_section(title, group_title)
        if step_id and classification["disposition"] != "screen":
            document_step_ids.add(step_id)
    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    disposition = coverage.get("disposition", []) if isinstance(coverage.get("disposition"), list) else []
    return {
        "plan_step_count": len(plan.get("steps", []) if isinstance(plan.get("steps"), list) else []),
        "plan_disposition_count": len(disposition),
        "document_step_ids": document_step_ids,
        "disposition_sections": [
            str(item.get("prd_section"))
            for item in disposition
            if isinstance(item, dict) and item.get("prd_section")
        ],
    }


def inspect_quality_static(fragment_text: str, plan: dict[str, object] | None = None) -> dict[str, object]:
    inspector = ProtoQualityInspector()
    inspector.feed(fragment_text)
    plan_context = quality_plan_context(plan)
    document_step_ids = plan_context["document_step_ids"] if isinstance(plan_context["document_step_ids"], set) else set()
    suspicious_steps: list[dict[str, object]] = []
    for step in inspector.steps:
        step_id = str(step.get("id") or "")
        nav_titles = [str(item).strip() for item in step.get("nav_titles", []) if str(item).strip()]
        nav_title_text = " ".join(nav_titles)
        label = str(step.get("label") or step.get("id") or "")
        text = str(step.get("text") or "")
        explanation_score = int(step.get("explanation_token_count") or 0)
        has_explanation_nav = any(title.strip().lower() in {"说明", "explanation", "notes", "requirements", "rules"} for title in nav_titles)
        has_explanation_label = QUALITY_EXPLANATION_CLASS_RE.search(label) is not None
        has_explanation_text = any(term in nav_title_text for term in QUALITY_EXPLANATION_TERMS)
        if (
            int(step.get("surface_count") or 0) >= 1
            and int(step.get("annotation_count") or 0) == 0
            and (has_explanation_nav or has_explanation_label or (has_explanation_text and explanation_score >= 3))
            and (int(step.get("list_or_table_count") or 0) >= 1 or len(text) >= 80)
        ):
            suspicious_steps.append(
                {
                    "step_id": step.get("id"),
                    "label": step.get("label"),
                    "nav_titles": nav_titles,
                    "reason": "screen looks like explanation material rather than a user-visible product state",
                }
            )
        elif step_id in document_step_ids:
            suspicious_steps.append(
                {
                    "step_id": step.get("id"),
                    "label": step.get("label"),
                    "nav_titles": nav_titles,
                    "reason": "plan-aware disposition says this heading is explanatory material, not a product screen",
                }
            )
        elif (
            int(step.get("surface_count") or 0) >= 1
            and int(step.get("annotation_count") or 0) == 0
            and explanation_score >= 6
            and len(text) >= 260
            and int(step.get("interactive_count") or 0) <= 1
        ):
            suspicious_steps.append(
                {
                    "step_id": step.get("id"),
                    "label": step.get("label"),
                    "nav_titles": nav_titles,
                    "reason": "long rule/spec text appears inside a product surface with little interaction",
                }
            )

    return {
        "step_count": len(inspector.steps),
        "suspicious_explanation_screen_count": len(suspicious_steps),
        "suspicious_explanation_screens": suspicious_steps,
        "annotation_count": sum(int(step.get("annotation_count") or 0) for step in inspector.steps),
        "annotation_missing_proto_id": inspector.annotation_missing_proto_id,
        "annotation_missing_proto_label": inspector.annotation_missing_proto_label,
        "annotation_in_surface": inspector.annotation_in_surface,
        "long_annotation_count": len(inspector.long_annotations),
        "long_annotations": inspector.long_annotations,
        "annotation_structure_count": inspector.annotation_structure_count,
        "plan_disposition_count": int(plan_context["plan_disposition_count"]),
        "plan_document_step_count": len(document_step_ids),
    }


def dangerous_generated_css_warnings(fragment_text: str) -> list[str]:
    warnings: list[str] = []
    style_chunks = re.findall(r"<style\b[^>]*>(.*?)</style>", fragment_text, re.I | re.S)
    style_chunks.extend(match.group(2) for match in re.finditer(r"\bstyle\s*=\s*([\"'])(.*?)\1", fragment_text, re.I | re.S))
    css_text = "\n".join(style_chunks)
    if not css_text.strip():
        return warnings
    for pattern, message in QUALITY_DANGEROUS_CSS_PATTERNS:
        if re.search(pattern, css_text, re.I):
            warnings.append(message)
    return warnings


def generated_css_quality_warnings(fragment_text: str) -> list[str]:
    warnings: list[str] = []
    style_chunks = re.findall(r"<style\b[^>]*>(.*?)</style>", fragment_text, re.I | re.S)
    style_chunks.extend(match.group(2) for match in re.finditer(r"\bstyle\s*=\s*([\"'])(.*?)\1", fragment_text, re.I | re.S))
    css_text = "\n".join(style_chunks)
    if not css_text.strip():
        return warnings
    for pattern, message in QUALITY_CSS_WARNING_PATTERNS:
        if re.search(pattern, css_text, re.I):
            warnings.append(message)
    return warnings


def edit_state_residue_warnings(fragment_text: str, raw_text: str) -> list[str]:
    warnings: list[str] = []
    residue_patterns = (
        (r"\bcontenteditable\s*=\s*[\"']true[\"']", "contenteditable=true remains in generated content."),
        (r"\bdata-edit-selected\b", "edit selection state remains in generated content."),
        (r"\bdata-editable-text\b", "runtime data-editable-text remains in generated content."),
        (r"\bdata-edit-removable\b", "runtime data-edit-removable remains in generated content."),
        (r"\bdata-proto-auto\b", "runtime data-proto-auto remains in generated content."),
        (r"\bis-revision-selected\b", "revision selection class remains in generated content."),
    )
    for pattern, message in residue_patterns:
        if re.search(pattern, fragment_text, re.I):
            warnings.append(message)
    body_class_match = re.search(r"<body\b[^>]*\bclass\s*=\s*([\"'])(.*?)\1", raw_text, re.I | re.S)
    if body_class_match and re.search(r"\bproto-(?:edit|revision|prd)-mode\b", body_class_match.group(2)):
        warnings.append("prototype body still carries authoring/presentation mode classes.")
    return warnings


def resolve_quality_target(target: Path) -> dict[str, Path | None]:
    resolved = target.expanduser().resolve()
    if resolved.is_dir():
        prototype = prototype_dir_for_target(resolved)
        return {
            "demand_dir": prototype,
            "index": prototype / "index.html",
            "fragment": prototype / "generated-area-fragment.html",
        }
    if resolved.is_file():
        demand = resolved.parent
        fragment = resolved if resolved.name.lower() == "generated-area-fragment.html" else demand / "generated-area-fragment.html"
        index = resolved if resolved.name.lower() == "index.html" else demand / "index.html"
        return {"demand_dir": demand, "index": index, "fragment": fragment}
    fail(f"quality-check target not found: {resolved}")
    return {"demand_dir": None, "index": None, "fragment": None}


def render_quality_check(index_path: Path) -> dict[str, object]:
    if not index_path.is_file():
        return {
            "ok": False,
            "status": "failed",
            "failures": [f"render check requires index.html: {index_path}"],
            "warnings": [],
            "summary": {},
        }
    try:
        probe = subprocess.run(
            [
                "node",
                "-e",
                "try{require('playwright');console.log('playwright')}catch(e){try{require('@playwright/test');console.log('@playwright/test')}catch(e2){process.exit(9)}}",
            ],
            cwd=str(index_path.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "status": "unavailable",
            "failures": ["Node.js is not available; render quality check cannot run."],
            "warnings": [],
            "summary": {},
        }
    if probe.returncode != 0:
        return {
            "ok": False,
            "status": "unavailable",
            "failures": ["Playwright is not available; install it or run quality-check without --render."],
            "warnings": [],
            "summary": {},
        }
    module_name = probe.stdout.strip() or "playwright"
    node_script = r"""
const fs = require('fs');
const path = require('path');
const moduleName = process.argv[2];
const indexPath = path.resolve(process.argv[3]);
const mod = require(require.resolve(moduleName, { paths: [path.dirname(indexPath), process.cwd()] }));
const chromium = mod.chromium || (mod.default && mod.default.chromium);
function intersects(a, b) {
  return !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
}
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto('file:///' + indexPath.replace(/\\/g, '/'));
  await page.waitForTimeout(250);
  const result = await page.evaluate(() => {
    const failures = [];
    const warnings = [];
    const rectOf = (el) => {
      const r = el.getBoundingClientRect();
      return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
    };
    document.querySelectorAll('#proto-generated-area .journey-step').forEach((step) => {
      const stepId = step.getAttribute('data-proto-id') || step.id || 'unknown-step';
      const stepRect = rectOf(step);
      step.querySelectorAll('.phone-frame, .web-surface').forEach((surface) => {
        const r = rectOf(surface);
        if (r.width <= 10 || r.height <= 10) failures.push(`${stepId}: primary surface is blank or collapsed.`);
        if (r.left < stepRect.left - 8 || r.right > stepRect.right + 8 || r.top < stepRect.top - 8 || r.bottom > stepRect.bottom + 8) {
          failures.push(`${stepId}: primary surface overflows its journey step.`);
        }
      });
      const surfaces = [...step.querySelectorAll('.phone-frame, .web-surface')].map(rectOf);
      step.querySelectorAll('.annotation').forEach((annotation) => {
        const r = rectOf(annotation);
        if (r.width <= 4 || r.height <= 4) failures.push(`${stepId}: annotation is collapsed.`);
        if (surfaces.some((surface) => intersects(r, surface))) failures.push(`${stepId}: annotation overlaps a product surface.`);
      });
      step.querySelectorAll('button, [class*="badge"], [class*="Badge"]').forEach((el) => {
        const parent = el.closest('.nav-bar, .app-screen, .phone-screen, .web-surface');
        if (!parent) return;
        const r = rectOf(el);
        const p = rectOf(parent);
        if (r.left < p.left - 3 || r.right > p.right + 3 || r.top < p.top - 3 || r.bottom > p.bottom + 3) {
          failures.push(`${stepId}: button/badge overflows its nearest surface.`);
        }
      });
    });
    const area = document.querySelector('#proto-generated-area');
    if (area && area.scrollWidth > area.clientWidth + 12) warnings.push('generated area has horizontal overflow.');
    return { failures, warnings };
  });
  await browser.close();
  console.log(JSON.stringify(result));
})().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
"""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as handle:
        handle.write(node_script)
        script_path = Path(handle.name)
    try:
        run = subprocess.run(
            ["node", str(script_path), module_name, str(index_path.resolve())],
            cwd=str(index_path.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
        )
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass
    if run.returncode != 0:
        return {
            "ok": False,
            "status": "failed",
            "failures": ["render quality check failed to execute: " + ((run.stderr or "").strip() or (run.stdout or "").strip())],
            "warnings": [],
            "summary": {},
        }
    try:
        payload = json.loads(run.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "status": "failed",
            "failures": ["render quality check returned invalid JSON."],
            "warnings": [run.stdout.strip()],
            "summary": {},
        }
    failures = [str(item) for item in payload.get("failures", []) if item]
    warnings = [str(item) for item in payload.get("warnings", []) if item]
    return {
        "ok": not failures,
        "status": "ready" if not failures else "failed",
        "failures": failures,
        "warnings": warnings,
        "summary": {"failure_count": len(failures), "warning_count": len(warnings)},
    }


def quality_check(target: Path, strict: bool = False, render: bool = False) -> dict[str, object]:
    paths = resolve_quality_target(target)
    index_path = paths["index"]
    fragment_path = paths["fragment"]
    plan_path = (paths["demand_dir"] / PLAN_FILENAME) if paths.get("demand_dir") is not None else None
    source_path = index_path if index_path and index_path.is_file() else fragment_path
    failures: list[str] = []
    warnings: list[str] = []
    if source_path is None or not source_path.is_file():
        return {
            "ok": False,
            "status": "failed",
            "strict": strict,
            "render_requested": render,
            "paths": {key: str(value) for key, value in paths.items() if value is not None},
            "failures": ["quality-check requires index.html or generated-area-fragment.html."],
            "warnings": [],
        }
    try:
        raw_text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "ok": False,
            "status": "failed",
            "strict": strict,
            "render_requested": render,
            "paths": {key: str(value) for key, value in paths.items() if value is not None},
            "failures": [f"target is not valid UTF-8: {source_path}"],
            "warnings": [],
        }
    fragment_text = extract_generated_fragment(raw_text)
    if source_path.name.lower() != "generated-area-fragment.html" and fragment_path and fragment_path.is_file():
        try:
            fragment_text = extract_generated_fragment(fragment_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            failures.append(f"fragment is not valid UTF-8: {fragment_path}")
    plan: dict[str, object] | None = None
    if plan_path and plan_path.is_file():
        try:
            loaded_plan = load_json_file(plan_path)
            plan = loaded_plan if isinstance(loaded_plan, dict) else None
        except SystemExit:
            raise
        except Exception as error:
            warnings.append(f"Could not read prototype-plan.json for plan-aware quality checks: {error}")
    static = inspect_quality_static(fragment_text, plan=plan)
    generated_area = inspect_generated_area(fragment_text)
    warnings.extend(str(item) for item in generated_area.get("warnings", []))
    css_failures = dangerous_generated_css_warnings(fragment_text)
    css_warnings = generated_css_quality_warnings(fragment_text)
    residue = edit_state_residue_warnings(fragment_text, raw_text)
    warnings.extend(css_warnings)
    warnings.extend(css_failures)
    warnings.extend(residue)

    if static["suspicious_explanation_screen_count"]:
        message = (
            "Explanation-only product screens detected; move rules/source/acceptance text to PRD Viewer, "
            "delivery notes, plan coverage, or short annotations: "
            + ", ".join(str(item.get("step_id") or item.get("label")) for item in static["suspicious_explanation_screens"][:10])
        )
        (failures if strict else warnings).append(message)
    if static["annotation_missing_proto_id"] or static["annotation_missing_proto_label"]:
        message = "Annotations must include stable data-proto-id and data-proto-label."
        (failures if strict else warnings).append(message)
    if static["annotation_in_surface"]:
        message = "Annotations must not be placed inside phone/web product surfaces."
        (failures if strict else warnings).append(message)
    if static["long_annotation_count"]:
        message = "Long or structured annotations detected; keep long rules/tables in the PRD Viewer: " + ", ".join(static["long_annotations"][:10])
        (failures if strict else warnings).append(message)
    if (
        int(static.get("plan_disposition_count") or 0) > 0
        and int(static.get("annotation_count") or 0) == 0
        and int(static.get("step_count") or 0) >= 3
    ):
        message = "Plan contains explanatory PRD material but the prototype has 0 annotations; add short annotations or keep explanations only in PRD Viewer/delivery notes."
        (failures if strict else warnings).append(message)
    if residue and strict:
        failures.extend(residue)
    if css_failures and strict:
        failures.extend(css_failures)

    render_result = None
    if render:
        if index_path is None:
            render_result = {
                "ok": False,
                "status": "failed",
                "failures": ["render check requires index.html."],
                "warnings": [],
                "summary": {},
            }
        else:
            render_result = render_quality_check(index_path)
        if render_result.get("failures"):
            (failures if strict else warnings).extend(str(item) for item in render_result.get("failures", []))
        warnings.extend(str(item) for item in render_result.get("warnings", []))

    status = "failed" if failures else ("warning" if warnings else "ready")
    return {
        "ok": not failures,
        "status": status,
        "strict": strict,
        "render_requested": render,
        "paths": {key: str(value) for key, value in paths.items() if value is not None},
        "failures": failures,
        "warnings": warnings,
        "summary": {
            "step_count": static["step_count"],
            "annotation_count": static["annotation_count"],
            "suspicious_explanation_screen_count": static["suspicious_explanation_screen_count"],
            "long_annotation_count": static["long_annotation_count"],
            "plan_disposition_count": static["plan_disposition_count"],
            "plan_document_step_count": static["plan_document_step_count"],
            "generated_area_warning_count": len(generated_area.get("warnings", [])),
        },
        "static": static,
        "render": render_result,
    }


def extract_journey_step_proto_items(raw: str) -> list[dict[str, str]]:
    text = extract_generated_fragment(raw)
    items: list[dict[str, str]] = []
    for match in re.finditer(r"<[A-Za-z][^>]*>", text):
        tag = match.group(0)
        class_match = re.search(r"\bclass=[\"']([^\"']*)[\"']", tag)
        if not class_match or "journey-step" not in class_match.group(1).split():
            continue
        id_match = re.search(r"\bdata-proto-id=[\"']([^\"']+)[\"']", tag)
        if id_match:
            step_id = html.unescape(id_match.group(1))
            label_match = re.search(r"\bdata-proto-label=[\"']([^\"']+)[\"']", tag)
            label = html.unescape(label_match.group(1)) if label_match else step_id
            items.append({"id": step_id, "label": label})
    return items


def extract_journey_step_proto_ids(raw: str) -> list[str]:
    return [item["id"] for item in extract_journey_step_proto_items(raw)]


def plan_step_ids(plan: dict[str, object]) -> set[str]:
    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    return {str(step.get("id")) for step in steps if isinstance(step, dict) and step.get("id")}


def rendered_step_ids_from_plan(plan: dict[str, object]) -> set[str]:
    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    return {
        str(step.get("id"))
        for step in steps
        if isinstance(step, dict) and step.get("id") and (step.get("rendered") or step.get("state") == "rendered")
    }


def update_plan_coverage_from_rendered(plan: dict[str, object]) -> None:
    plan.setdefault("coverage", {})
    if isinstance(plan["coverage"], dict):
        plan["coverage"]["covered_prd_sections"] = sorted(
            {
                str(section)
                for step in plan.get("steps", [])
                if isinstance(step, dict) and step.get("rendered")
                for section in step.get("prd_sections", []) or []
            }
        )


def sync_plan_with_fragment(plan_path: Path, fragment_path: Path) -> dict[str, object]:
    plan_file = plan_path.resolve()
    fragment_file = fragment_path.resolve()
    plan = load_json_file(plan_file)
    fragment_validation = validate_fragment_file(fragment_file, strict=True)
    if not fragment_validation["ok"]:
        return {
            "ok": False,
            "plan_path": str(plan_file),
            "fragment_path": str(fragment_file),
            "fragment_validation": fragment_validation,
        }
    fragment_ids = set(extract_journey_step_proto_ids(fragment_file.read_text(encoding="utf-8")))
    matched: list[str] = []
    unmatched: list[str] = []
    for step in (plan.get("steps", []) if isinstance(plan.get("steps"), list) else []):
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        if step.get("state") == "omitted":
            continue
        if step_id in fragment_ids:
            step["rendered"] = True
            step["state"] = "rendered"
            matched.append(step_id)
        else:
            step["rendered"] = False
            step["state"] = "planned"
            unmatched.append(step_id)
    update_plan_coverage_from_rendered(plan)
    plan["updated_at"] = utc_now_iso()
    plan["validation"] = {
        "last_strict_ok": True,
        "failures": [],
        "warnings": fragment_validation.get("warnings", []),
    }
    revision_history = plan.get("revision_history", [])
    if not isinstance(revision_history, list):
        revision_history = []
    revision_history.append(
        {
            "at": utc_now_iso(),
            "action": "plan_synced_from_fragment",
            "summary": "Matched rendered steps from generated-area-fragment.html by exact data-proto-id.",
        }
    )
    plan["revision_history"] = revision_history
    extra_ids = sorted(fragment_ids - plan_step_ids(plan))
    if extra_ids:
        return {
            "ok": False,
            "status": "failed",
            "plan_path": str(plan_file),
            "fragment_path": str(fragment_file),
            "matched_step_ids": matched,
            "unmatched_step_ids": unmatched,
            "unknown_fragment_step_ids": extra_ids,
            "summary": summarize_prototype_plan(plan),
            "failures": ["Fragment contains journey-step ids not present in prototype-plan.json: " + ", ".join(extra_ids[:12])],
        }
    plan["generation_mode"] = "legacy_fragment"
    plan["legacy_fragment_kind"] = "handwritten"
    write_json_file(plan_file, plan)
    return {
        "ok": True,
        "status": "ready",
        "plan_path": str(plan_file),
        "fragment_path": str(fragment_file),
        "matched_step_ids": matched,
        "unmatched_step_ids": unmatched,
        "unknown_fragment_step_ids": extra_ids,
        "summary": summarize_prototype_plan(plan),
    }


TAG_TOKEN_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9:-]*)([^<>]*?)(/?)>", re.S)


def tag_has_data_proto_id(tag_text: str, proto_id: str) -> bool:
    pattern = r"\bdata-proto-id\s*=\s*([\"'])" + re.escape(proto_id) + r"\1"
    return re.search(pattern, tag_text) is not None


def find_element_span_by_proto_id(text: str, proto_id: str) -> tuple[int, int, int, int, str] | str:
    matches: list[tuple[int, int, int, int, str]] = []
    tokens = list(TAG_TOKEN_RE.finditer(text))
    void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    for index, token in enumerate(tokens):
        is_end = bool(token.group(1))
        tag_name = token.group(2).lower()
        is_self_closing = bool(token.group(4)) or tag_name in void_tags
        if is_end or is_self_closing or not tag_has_data_proto_id(token.group(0), proto_id):
            continue
        depth = 1
        for close_token in tokens[index + 1 :]:
            close_is_end = bool(close_token.group(1))
            close_tag = close_token.group(2).lower()
            close_self = bool(close_token.group(4)) or close_tag in void_tags
            if close_tag != tag_name:
                continue
            if close_is_end:
                depth -= 1
            elif not close_self:
                depth += 1
            if depth == 0:
                matches.append((token.start(), close_token.end(), token.end(), close_token.start(), tag_name))
                break
        else:
            return f"Element with data-proto-id '{proto_id}' has no closing </{tag_name}> tag."
    if not matches:
        return f"Element with data-proto-id '{proto_id}' was not found."
    if len(matches) > 1:
        return f"Element with data-proto-id '{proto_id}' matched {len(matches)} nodes; patch application refuses to guess."
    return matches[0]


def infer_patch_step_id(screen_records: list[dict[str, object]], proto_id: str) -> tuple[str | None, str | None]:
    matched = [
        str(record["step_id"])
        for record in screen_records
        if re.search(r"\bdata-proto-id\s*=\s*([\"'])" + re.escape(proto_id) + r"\1", str(record.get("text") or ""))
    ]
    unique = sorted(set(matched))
    if len(unique) == 1:
        return unique[0], None
    if not unique:
        return None, f"Patch target '{proto_id}' was not found in any content screen."
    return None, f"Patch target '{proto_id}' matched multiple screens: " + ", ".join(unique[:8])


def clean_patch_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def apply_edit_patch_data(demand_dir: Path, patch: dict[str, object], patch_label: str) -> dict[str, object]:
    demand = demand_dir.expanduser().resolve()
    if int(patch.get("schema_version") or 0) != EDIT_PATCH_SCHEMA_VERSION:
        return {
            "ok": False,
            "status": "failed",
            "demand_dir": str(demand),
            "patch_path": patch_label,
            "applied_count": 0,
            "failures": [f"Patch schema_version must be {EDIT_PATCH_SCHEMA_VERSION}."],
            "warnings": [],
        }
    operations = patch.get("operations", [])
    if not isinstance(operations, list):
        return {
            "ok": False,
            "status": "failed",
            "demand_dir": str(demand),
            "patch_path": patch_label,
            "applied_count": 0,
            "failures": ["Patch operations must be an array."],
            "warnings": [],
        }

    validation = validate_content_package(demand, strict=False, final=False, require_fresh_hashes=False)
    if not validation["ok"]:
        return {
            "ok": False,
            "status": "failed",
            "paths": validation.get("paths", {}),
            "failures": validation.get("failures", []),
            "warnings": validation.get("warnings", []),
        }
    manifest = validation["manifest"]
    screen_records = validation["screen_records"]
    paths = content_package_paths(demand)
    screen_by_step = {str(record["step_id"]): record for record in screen_records}
    updates_by_path: dict[Path, str] = {Path(record["path"]): str(record["text"]) for record in screen_records}
    applied: list[dict[str, object]] = []
    failures: list[str] = []
    affected_steps: set[str] = set()

    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            failures.append(f"operations[{index}] must be an object.")
            continue
        op = str(operation.get("op") or "").strip()
        proto_id = str(operation.get("data_proto_id") or operation.get("data-proto-id") or "").strip()
        step_id = str(operation.get("step_id") or "").strip()
        if op != "replace_text":
            failures.append(f"operations[{index}] has unsupported op '{op}'. Text-edit patches are text-only; use big-change notes or source edits for structure changes.")
            continue
        if not proto_id:
            failures.append(f"operations[{index}] is missing data_proto_id.")
            continue
        if not step_id:
            step_id, infer_error = infer_patch_step_id(screen_records, proto_id)
            if infer_error:
                failures.append(f"operations[{index}]: {infer_error}")
                continue
        assert step_id is not None
        record = screen_by_step.get(step_id)
        if not record:
            failures.append(f"operations[{index}]: step_id '{step_id}' is not present in prototype-content/manifest.json.")
            continue
        screen_path = Path(record["path"])
        text = updates_by_path[screen_path]
        span = find_element_span_by_proto_id(text, proto_id)
        if isinstance(span, str):
            failures.append(f"operations[{index}]: {span}")
            continue
        start, end, open_end, close_start, tag_name = span
        replacement_text = operation.get("text")
        if not isinstance(replacement_text, str):
            failures.append(f"operations[{index}]: replace_text requires a string text value.")
            continue
        inner = text[open_end:close_start]
        if re.search(r"<[A-Za-z!/]", inner):
            failures.append(
                f"operations[{index}]: target '{proto_id}' contains nested markup; use a larger structural edit instead of replace_text."
            )
            continue
        expected_text = operation.get("original_text", operation.get("before_text"))
        if isinstance(expected_text, str):
            current_text = clean_patch_text(html.unescape(inner))
            if current_text != clean_patch_text(expected_text):
                failures.append(
                    f"operations[{index}]: target '{proto_id}' original_text does not match the current source; refresh preview before saving."
                )
                continue
        text = text[:open_end] + html.escape(replacement_text, quote=False) + text[close_start:]
        updates_by_path[screen_path] = text
        affected_steps.add(step_id)
        applied.append({"op": op, "step_id": step_id, "data_proto_id": proto_id, "tag": tag_name})

    if failures:
        return {
            "ok": False,
            "status": "failed",
            "demand_dir": str(demand),
            "patch_path": patch_label,
            "applied_count": 0,
            "failures": failures,
            "warnings": validation.get("warnings", []),
        }

    for screen_path, text in updates_by_path.items():
        original = next((str(record["text"]) for record in screen_records if Path(record["path"]) == screen_path), "")
        if text != original:
            screen_path.write_text(text, encoding="utf-8")

    updated_manifest = dict(manifest)
    updated_screens: list[dict[str, object]] = []
    for item in manifest.get("screens", []) if isinstance(manifest.get("screens"), list) else []:
        if not isinstance(item, dict):
            continue
        copied = dict(item)
        if str(copied.get("step_id") or "") in affected_steps:
            copied["status"] = "draft"
            copied["hash"] = ""
        updated_screens.append(copied)
    updated_manifest["screens"] = updated_screens
    updated_manifest["updated_at"] = utc_now_iso()
    write_json_file(paths["manifest"], updated_manifest)

    plan_path = paths["plan"]
    if plan_path.is_file():
        plan = load_json_file(plan_path)
        revision_history = plan.get("revision_history", [])
        if not isinstance(revision_history, list):
            revision_history = []
        revision_history.append(
            {
                "at": utc_now_iso(),
                "action": "content_edit_patch_applied",
                "summary": f"Applied {len(applied)} text-edit operation(s) to prototype-content source screens.",
                "affected_step_ids": sorted(affected_steps),
            }
        )
        plan["revision_history"] = revision_history
        plan["updated_at"] = utc_now_iso()
        write_json_file(plan_path, plan)

    return {
        "ok": True,
        "status": "applied",
        "demand_dir": str(demand),
        "patch_path": patch_label,
        "applied_count": len(applied),
        "affected_step_ids": sorted(affected_steps),
        "operations": applied,
        "next_actions": [
            "Run package-check --strict.",
            "Run build-content.",
            "Run inject --strict.",
            "Run final-check --require-content --require-complete.",
        ],
    }


def apply_edit_patch(demand_dir: Path, patch_path: Path) -> dict[str, object]:
    patch_file = patch_path.expanduser().resolve()
    if not patch_file.is_file():
        fail(f"Patch file not found: {patch_file}")
    try:
        patch = json.loads(patch_file.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        fail(f"Patch file is not valid UTF-8: {patch_file}")
    except json.JSONDecodeError as error:
        fail(f"Patch file is not valid JSON: {patch_file}: {error}")
    if not isinstance(patch, dict):
        fail("Patch root must be a JSON object.")
    return apply_edit_patch_data(demand_dir, patch, str(patch_file))


def preview_text_save_capabilities(demand_dir: Path) -> dict[str, object]:
    paths = content_package_paths(demand_dir)
    content_package_present = paths["manifest"].is_file()
    generation_mode = ""
    plan_ok = False
    if paths["plan"].is_file():
        plan, error = try_load_json_object(paths["plan"])
        if plan is not None and not error:
            plan_ok = True
            generation_mode = str(plan.get("generation_mode") or "")
    return {
        "content_package_present": content_package_present,
        "generation_mode": generation_mode,
        "plan_available": plan_ok,
        "text_save_supported": content_package_present and generation_mode == "content_package",
        "text_save_requires": "prototype-content/screens/*.html",
    }


def save_text_patch_from_preview(demand_dir: Path, patch: dict[str, object]) -> dict[str, object]:
    capabilities = preview_text_save_capabilities(demand_dir)
    if not bool(capabilities.get("text_save_supported")):
        return {
            "ok": False,
            "status": "unsupported",
            "demand_dir": str(demand_dir.expanduser().resolve()),
            "failures": [
                "Current prototype has no content package source for text saving; migrate to prototype-content/screens/*.html before using preview save."
            ],
            "save_capabilities": capabilities,
        }
    applied = apply_edit_patch_data(demand_dir, patch, "preview-save-text-patch")
    if not applied["ok"]:
        return applied
    prototype = prototype_dir_for_target(demand_dir)
    demand = demand_root_for_prototype(prototype)
    built = build_content_package(prototype, check=False, update_plan=True)
    if not built["ok"]:
        return {
            "ok": False,
            "status": "failed",
            "demand_dir": str(demand),
            "prototype_dir": str(prototype),
            "applied": applied,
            "failures": [f"build-content after save failed: {item}" for item in built.get("failures", [])],
            "warnings": built.get("warnings", []),
        }
    try:
        injected = inject_generated_area(prototype / "index.html", prototype / "generated-area-fragment.html")
    except SystemExit as error:
        return {
            "ok": False,
            "status": "failed",
            "demand_dir": str(demand),
            "prototype_dir": str(prototype),
            "applied": applied,
            "build_content": {
                "ok": built.get("ok"),
                "status": built.get("status"),
                "fragment_path": built.get("fragment_path"),
                "manifest_path": built.get("manifest_path"),
                "summary": built.get("summary", {}),
            },
            "failures": [f"inject after save failed with exit code {error.code}."],
            "warnings": built.get("warnings", []),
        }
    checked = final_check(prototype, require_content=True)
    final_ok = bool(checked.get("ok"))
    return {
        "ok": final_ok,
        "status": "saved" if final_ok else "saved_with_validation_failures",
        "demand_dir": str(demand),
        "prototype_dir": str(prototype),
        "applied_count": applied.get("applied_count", 0),
        "affected_step_ids": applied.get("affected_step_ids", []),
        "applied": applied,
        "build_content": {
            "ok": built.get("ok"),
            "status": built.get("status"),
            "fragment_path": built.get("fragment_path"),
            "manifest_path": built.get("manifest_path"),
            "summary": built.get("summary", {}),
        },
        "inject": injected,
        "final_check": {
            "ok": checked.get("ok"),
            "status": checked.get("status"),
            "blockers": checked.get("blockers", []),
            "warnings": checked.get("warnings", []),
        },
        "failures": [] if final_ok else [f"final-check after save failed: {item}" for item in checked.get("blockers", [])],
    }


def final_check(demand_dir: Path, require_content: bool = False) -> dict[str, object]:
    demand = prototype_dir_for_target(demand_dir)
    index_path = demand / "index.html"
    fragment_path = demand / "generated-area-fragment.html"
    plan_path = demand / PLAN_FILENAME
    content_paths = content_package_paths(demand)
    package_present = has_content_package(demand)
    blockers: list[str] = []
    warnings: list[str] = []
    paths = {
        "demand_dir": str(demand),
        "index": str(index_path),
        "fragment": str(fragment_path),
        "plan": str(plan_path),
        "content_manifest": str(content_paths["manifest"]),
    }
    if not demand.is_dir():
        blockers.append(f"Demand folder not found: {demand}")
    for label, path in (("index", index_path), ("fragment", fragment_path), ("plan", plan_path)):
        if not path.is_file():
            blockers.append(f"Missing {label}: {path}")
    if blockers:
        return {
            "ok": False,
            "status": "failed",
            "paths": paths,
            "blockers": blockers,
            "warnings": warnings,
            "coverage": {},
        }

    try:
        plan = load_json_file(plan_path)
    except SystemExit:
        return {
            "ok": False,
            "status": "failed",
            "paths": paths,
            "blockers": [f"Invalid or unreadable prototype-plan.json: {plan_path}"],
            "warnings": warnings,
            "coverage": {},
        }

    generation_mode = str(plan.get("generation_mode") or "legacy_fragment")
    if generation_mode not in PLAN_GENERATION_MODES:
        blockers.append("prototype-plan.json generation_mode is invalid.")

    plan_validation = validate_plan_file(plan_path, final=True)
    if not plan_validation["ok"]:
        blockers.extend(str(item) for item in plan_validation.get("failures", []))
    warnings.extend(str(item) for item in plan_validation.get("warnings", []))

    package_validation = None
    build_check = None
    if generation_mode == "content_package" and not package_present:
        blockers.append("generation_mode is content_package, but prototype-content/manifest.json is missing; run init-content and build-content.")
    if require_content and generation_mode != "content_package":
        blockers.append("--require-content was requested, but generation_mode is not content_package.")
    if package_present:
        package_validation = validate_content_package(demand, strict=True, final=True, require_fresh_hashes=True)
        if not package_validation["ok"]:
            blockers.extend(f"content package: {item}" for item in package_validation.get("failures", []))
        warnings.extend(f"content package: {item}" for item in package_validation.get("warnings", []))
        build_check = build_content_package(demand, check=True, update_plan=False)
        if not build_check["ok"]:
            blockers.extend(f"content build: {item}" for item in build_check.get("failures", []))
        warnings.extend(f"content build: {item}" for item in build_check.get("warnings", []))
    elif generation_mode == "showcase":
        warnings.append("showcase generation_mode uses the legacy fragment flow by design.")
    elif generation_mode == "legacy_fragment":
        if str(plan.get("legacy_fragment_kind") or "") == "placeholder":
            blockers.append("legacy render-fragment output is a placeholder draft; use content package or sync a real hand-written fragment before final delivery.")
        warnings.append("prototype-content/manifest.json not found; final-check is using the legacy generated-area-fragment flow.")

    fragment_validation = validate_fragment_file(fragment_path, strict=True)
    if not fragment_validation["ok"]:
        blockers.extend(f"fragment: {item}" for item in fragment_validation.get("failures", []))
    warnings.extend(f"fragment: {item}" for item in fragment_validation.get("warnings", []))

    index_validation = validate_index(index_path, strict=True, exit_on_failure=False)
    if not index_validation["ok"]:
        generated = index_validation.get("generated_area", {}) if isinstance(index_validation.get("generated_area"), dict) else {}
        blockers.extend(f"index: {item}" for item in generated.get("strict_failures", []))
        for key, label in (("missing_tokens", "missing token"), ("missing_assets", "missing asset"), ("unexpected_tokens", "unexpected token")):
            blockers.extend(f"index: {label}: {item}" for item in index_validation.get(key, []) or [])
    index_flow_warning_fragments = (
        "复杂原型完成前必须运行 final-check",
        "基础 validate 不检查内容包新鲜度",
    )
    warnings.extend(
        f"index: {item}"
        for item in index_validation.get("warnings", [])
        if not any(fragment in str(item) for fragment in index_flow_warning_fragments)
    )

    plan_ids = plan_step_ids(plan)
    rendered_ids = rendered_step_ids_from_plan(plan)
    index_ids = set(extract_journey_step_proto_ids(index_path.read_text(encoding="utf-8")))
    index_fragment_text = extract_generated_fragment(index_path.read_text(encoding="utf-8")).strip()
    fragment_text = extract_generated_fragment(fragment_path.read_text(encoding="utf-8")).strip()
    fragment_ids = set(extract_journey_step_proto_ids(fragment_text))
    if index_fragment_text != fragment_text:
        blockers.append("index.html generated area differs from generated-area-fragment.html; run inject --strict after building the fragment.")
    missing_rendered = sorted(rendered_ids - index_ids)
    unsynced_visible = sorted((index_ids & plan_ids) - rendered_ids)
    unknown_index_ids = sorted(index_ids - plan_ids)
    unknown_fragment_ids = sorted(fragment_ids - plan_ids)
    if missing_rendered:
        blockers.append("Plan marks steps rendered but index.html does not contain them: " + ", ".join(missing_rendered[:12]))
    if unsynced_visible:
        blockers.append("index.html contains planned steps that prototype-plan.json does not mark rendered; run sync-plan or render-fragment: " + ", ".join(unsynced_visible[:12]))
    if unknown_index_ids:
        blockers.append("index.html contains journey-step ids not present in prototype-plan.json; update the plan or align data-proto-id values: " + ", ".join(unknown_index_ids[:12]))
    if unknown_fragment_ids:
        blockers.append("generated-area-fragment.html contains journey-step ids not present in prototype-plan.json: " + ", ".join(unknown_fragment_ids[:12]))

    steps = plan.get("steps", []) if isinstance(plan.get("steps"), list) else []
    coverage = plan.get("coverage", {}) if isinstance(plan.get("coverage"), dict) else {}
    omitted = coverage.get("omitted", []) if isinstance(coverage.get("omitted"), list) else []
    rendered_count = len(rendered_ids)
    step_count = len([step for step in steps if isinstance(step, dict)])
    if blockers:
        status = "failed"
    elif omitted or rendered_count < step_count:
        status = "partial"
    else:
        status = "complete"
    return {
        "ok": not blockers,
        "status": status,
        "generation_mode": generation_mode,
        "paths": paths,
        "blockers": blockers,
        "warnings": warnings,
        "coverage": {
            "step_count": step_count,
            "rendered_step_count": rendered_count,
            "omitted_count": len(omitted),
            "index_step_count": len(index_ids),
            "fragment_step_count": len(fragment_ids),
        },
        "plan_summary": summarize_prototype_plan(plan),
        "plan_validation": plan_validation,
        "package_validation": {key: value for key, value in package_validation.items() if key not in {"manifest", "plan", "screen_records"}} if isinstance(package_validation, dict) else None,
        "content_build_check": {key: value for key, value in build_check.items() if key not in {"package_validation", "fragment_validation"}} if isinstance(build_check, dict) else None,
        "fragment_validation": fragment_validation,
        "index_validation": index_validation,
    }


def demand_doctor(demand_dir: Path) -> dict[str, object]:
    demand = prototype_dir_for_target(demand_dir)
    demand_root = demand_root_for_prototype(demand)
    paths = content_package_paths(demand)
    next_actions: list[str] = []
    warnings: list[str] = []
    if not demand.is_dir():
        return {"ok": False, "status": "failed", "demand_dir": str(demand_root), "prototype_dir": str(demand), "next_actions": [f"Create or scaffold the prototype folder: {demand}"]}
    if not paths["index"].is_file():
        next_actions.append("Run scaffold to create index.html and shell assets.")
    if not paths["plan"].is_file():
        next_actions.append("Run plan to create prototype-plan.json.")
    plan: dict[str, object] = {}
    if paths["plan"].is_file():
        plan = load_json_file(paths["plan"])
    generation_mode = str(plan.get("generation_mode") or "unknown") if plan else "missing"
    if generation_mode == "content_package":
        if not paths["manifest"].is_file():
            next_actions.append("Run init-content to create prototype-content manifest and screen stubs.")
        else:
            package_check = validate_content_package(demand, strict=True, final=True, require_fresh_hashes=False)
            if not package_check["ok"]:
                next_actions.append(
                    "Fix package-check --strict failures in prototype-content source files; "
                    "placeholder screens should be rewritten from the PRD, not treated as missing skill templates."
                )
            elif not paths["fragment"].is_file():
                next_actions.append("Run build-content to create generated-area-fragment.html.")
            else:
                build_check = build_content_package(demand, check=True, update_plan=False)
                if not build_check["ok"]:
                    next_actions.append("Run build-content, then inject --strict because fragment is stale.")
                elif paths["index"].is_file():
                    index_fragment = extract_generated_fragment(paths["index"].read_text(encoding="utf-8")).strip()
                    fragment = extract_generated_fragment(paths["fragment"].read_text(encoding="utf-8")).strip()
                    if index_fragment != fragment:
                        next_actions.append("Run inject --strict to update index.html from generated-area-fragment.html.")
    elif generation_mode in {"legacy_fragment", "showcase"}:
        warnings.append(f"generation_mode is {generation_mode}; content package checks are not the default path.")
    elif plan:
        next_actions.append("Refresh plan so it records generation_mode.")

    if not next_actions and paths["index"].is_file() and paths["plan"].is_file() and paths["fragment"].is_file():
        final = final_check(demand)
        if final["ok"]:
            if final.get("status") == "complete":
                next_actions.append("Run quality-check --strict for presentation quality.")
                preview_state = load_preview_state(demand)
                preview_health = active_preview_health(preview_state, demand) if preview_state else None
                if preview_health:
                    next_actions.append(f"Open local preview: {preview_state.get('url')}. Stop with: python scripts/protopilot.py stop-preview \"{demand}\"")
                else:
                    next_actions.append(f"Run preview to view locally: python scripts/protopilot.py preview \"{demand}\"")
            elif final.get("status") == "partial":
                next_actions.append("Review coverage.omitted and confirm the partial scope; run final-check --require-content --require-complete only when complete delivery is required.")
            else:
                next_actions.append("No blocking action detected; final-check is ready.")
        else:
            next_actions.append("Fix final-check blockers.")
        return {
            "ok": bool(final["ok"]),
            "status": final.get("status"),
            "generation_mode": final.get("generation_mode", generation_mode),
            "demand_dir": str(demand_root),
            "prototype_dir": str(demand),
            "next_actions": next_actions,
            "warnings": warnings + final.get("warnings", []),
            "final_check": {key: value for key, value in final.items() if key not in {"fragment_validation", "index_validation", "plan_validation", "package_validation"}},
        }
    return {
        "ok": not next_actions,
        "status": "ready" if not next_actions else "needs_action",
        "generation_mode": generation_mode,
        "demand_dir": str(demand_root),
        "prototype_dir": str(demand),
        "next_actions": next_actions,
        "warnings": warnings,
    }


def write_rendered_fragment(plan_path: Path, out: str | None = None, update_plan: bool = True) -> dict[str, object]:
    plan_file = plan_path.resolve()
    plan = load_json_file(plan_file)
    plan_validation = validate_prototype_plan(plan, final=False)
    if not plan_validation["ok"]:
        return {"ok": False, "plan_path": str(plan_file), "plan_validation": plan_validation}
    fragment_text = render_fragment_from_plan(plan)
    output_path = Path(out).expanduser().resolve() if out else plan_file.parent / "generated-area-fragment.html"
    output_path.write_text(fragment_text, encoding="utf-8")
    fragment_validation = validate_fragment_file(output_path, strict=True)
    update_plan_coverage_from_rendered(plan)
    plan["updated_at"] = utc_now_iso()
    plan["validation"] = {
        "last_strict_ok": bool(fragment_validation["ok"]),
        "failures": fragment_validation.get("failures", []),
        "warnings": fragment_validation.get("warnings", []),
    }
    plan["generation_mode"] = "legacy_fragment"
    plan["legacy_fragment_kind"] = "placeholder"
    if update_plan:
        write_json_file(plan_file, plan)
    return {
        "ok": bool(fragment_validation["ok"]),
        "plan_path": str(plan_file),
        "fragment_path": str(output_path),
        "fragment_validation": fragment_validation,
        "summary": summarize_prototype_plan(plan),
    }

def migrate_legacy_generated_area(source_dir: Path, target: Path, inject: bool = False, force: bool = False) -> dict[str, object]:
    source = source_dir.expanduser().resolve()
    if not source.is_dir():
        fail(f"Legacy source directory not found: {source}")
    source_fragment = find_fragment_candidate(source)
    if not source_fragment:
        fail(f"No generated-area fragment or extractable index.html found in legacy directory: {source}")

    target_path = target.expanduser().resolve()
    if target_path.suffix.lower() == ".html":
        demand_dir = target_path.parent
        index_path = target_path
    else:
        demand_dir = target_path
        index_path = demand_dir / "index.html"
    if not demand_dir.is_dir():
        fail(f"Target demand folder not found: {demand_dir}")

    fragment_text = extract_generated_fragment(source_fragment.read_text(encoding="utf-8"))
    fragment_path = demand_dir / "generated-area-fragment.html"
    if fragment_path.exists() and not force:
        fail(f"Target fragment already exists; use --force only if you intend to replace it: {fragment_path}")
    fragment_path.write_text(fragment_text + "\n", encoding="utf-8")

    injected = False
    if inject:
        inject_generated_area(index_path, fragment_path)
        injected = True

    return {
        "ok": True,
        "source_dir": str(source),
        "source_fragment": str(source_fragment.resolve()),
        "target_fragment": str(fragment_path.resolve()),
        "index_path": str(index_path.resolve()),
        "injected": injected,
    }


def validate_index(index_path: Path, strict: bool = False, exit_on_failure: bool = True) -> dict[str, object]:
    index = index_path.resolve()
    if not index.is_file():
        fail(f"index.html not found: {index}")
    text = index.read_text(encoding="utf-8")
    required = [
        START_MARKER,
        END_MARKER,
        'class="proto-page"',
        'class="proto-generated-area"',
        'id="prd-drawer"',
        'class="proto-prd-viewer"',
        'id="prd-markdown-output"',
        'class="proto-prd-markdown typora-preview',
        'id="prd-viewer-fallback"',
        'id="prd-file-input"',
        'marked',
        'src="./prototype-shell.js"',
        'href="./prototype-base.css"',
    ]
    missing = [item for item in required if item not in text]
    asset_missing = [name for name in SHELL_ASSETS if not (index.parent / name).is_file()]
    prd_src_match = re.search(r"\bdata-prd-src=[\"']([^\"']+)[\"']", text)
    marked_match = re.search(r"<script\b[^>]*\bmarked[^>]*\.js[^>]*>", text, re.I)
    vendor_marked_match = re.search(r"<script\b[^>]*\bprototype-vendor\.js\b[^>]*\bmarked\b[^>]*>", text, re.I)
    unexpected = [item for item in ("<zero-md", "proto-prd-zero-md") if item in text]
    shell_warnings: list[str] = []
    shell_failures: list[str] = []
    prd_src_value = prd_src_match.group(1) if prd_src_match else ""
    if prd_src_value and (re.match(r"^[A-Za-z]:[\\/]", prd_src_value) or prd_src_value.startswith("file://") or "\\" in prd_src_value):
        shell_failures.append("PRD Viewer source must be a browser-relative URL such as ../PRD.md, not a local filesystem path.")
        shell_warnings.append("PRD Viewer source must be a browser-relative URL such as ../PRD.md, not a local filesystem path.")
    elif prd_src_value:
        prd_file, prd_error = browser_local_path(index.parent, prd_src_value)
        if prd_error:
            shell_failures.append(f"PRD Viewer source is not a local browser-relative path: {prd_src_value}")
        elif not prd_file or not prd_file.is_file():
            shell_failures.append(f"PRD Viewer source file not found from index.html: {prd_src_value}")
        else:
            demand_root = demand_root_for_prototype(index.parent)
            try:
                prd_file.relative_to(demand_root)
            except ValueError:
                shell_failures.append(f"PRD Viewer source must stay inside the demand folder: {prd_src_value}")
            plan_src = plan_prd_source_for_prototype(index.parent)
            if plan_src:
                plan_file, plan_error = resolve_plan_prd_source(index.parent, plan_src)
                if plan_error:
                    shell_failures.append(f"prototype-plan.json source.prd_path is not a local path: {plan_src}")
                elif not plan_file or not plan_file.is_file():
                    shell_failures.append(f"prototype-plan.json source.prd_path file not found: {plan_src}")
                else:
                    try:
                        plan_file.relative_to(demand_root)
                    except ValueError:
                        shell_failures.append(f"prototype-plan.json source.prd_path must stay inside the demand folder: {plan_src}")
                    if plan_file != prd_file:
                        shell_failures.append(f"PRD Viewer source does not match prototype-plan.json source: index={prd_src_value}, plan={plan_src}")
    spotlight_mount_match = re.search(r"<[^>]+\bid=[\"']proto-spotlight-mount[\"'][^>]*>", text)
    if spotlight_mount_match:
        class_match = re.search(r"\bclass=[\"']([^\"']*)[\"']", spotlight_mount_match.group(0))
        classes = set(class_match.group(1).split()) if class_match else set()
        if "proto-generated-area" not in classes:
            shell_warnings.append("spotlight 挂载点缺少 proto-generated-area 作用域，全屏可能丢失业务区 CSS，导致画布与全屏不一致。")
    main_area_match = re.search(r"<[^>]+\bid=[\"']proto-generated-area[\"'][^>]*>", text)
    if main_area_match:
        class_match = re.search(r"\bclass=[\"']([^\"']*)[\"']", main_area_match.group(0))
        classes = set(class_match.group(1).split()) if class_match else set()
        if "proto-generated-area" not in classes:
            shell_warnings.append("主业务区 #proto-generated-area 缺少 proto-generated-area class，目录、PRD 模式和作者工具可能失效。")
    else:
        shell_warnings.append("主业务区缺少 #proto-generated-area id；新版宣讲台会回退查找，但建议重新 scaffold 或刷新模板。")
    if re.search(r"body\.proto-prd-mode\s+\.proto-generated-area\s*>\s*:not\(\.journey-row\)", text):
        shell_warnings.append("PRD 模式折叠选择器疑似作用到所有 proto-generated-area；必须限定 main.proto-page，避免误伤 spotlight。")
    generated_area = inspect_generated_area(text)
    base_ok = not missing and not asset_missing and bool(prd_src_match) and bool(marked_match or vendor_marked_match) and not unexpected and not shell_failures
    strict_failures = generated_area.get("strict_failures", []) if isinstance(generated_area, dict) else []
    result = {
        "ok": base_ok and (not strict or (not strict_failures and not shell_failures)),
        "strict": strict,
        "index_path": str(index),
        "missing_tokens": missing,
        "missing_assets": asset_missing,
        "unexpected_tokens": unexpected,
        "warnings": shell_warnings,
        "shell_failures": shell_failures,
        "marked_loader": bool(marked_match or vendor_marked_match),
        "prd_viewer_src": prd_src_match.group(1) if prd_src_match else None,
        "generated_area": generated_area,
    }
    plan_path = index.parent / PLAN_FILENAME
    if plan_path.is_file():
        try:
            plan_result = validate_plan_file(plan_path, final=True)
        except SystemExit:
            plan_result = {"ok": False, "failures": ["Unable to validate prototype-plan.json."], "warnings": []}
        if not plan_result.get("ok"):
            result["warnings"].append("同目录存在 prototype-plan.json，但计划未达到最终交付状态；复杂原型完成前必须运行 final-check。")
            result["shell_failures"].extend(str(item) for item in plan_result.get("failures", []))
            result["ok"] = False
    if has_content_package(index.parent):
        result["warnings"].append("同目录存在 prototype-content；基础 validate 不检查内容包新鲜度，完成前必须运行 package-check、build-content --check 和 final-check。")
    if not result["ok"] and exit_on_failure:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(3)
    return result



def preview_state_path(demand: Path) -> Path:
    return demand / PREVIEW_STATE_FILENAME


def preview_url(port: int) -> str:
    return f"http://{PREVIEW_HOST}:{port}/{PROTOTYPE_DIRNAME}/index.html"


def preview_health_url(port: int) -> str:
    return f"http://{PREVIEW_HOST}:{port}{PREVIEW_HEALTH_PATH}"


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
    loaded, error = try_load_json_object(state_file)
    if error or not loaded:
        return None
    if loaded.get("schema_version") != PREVIEW_SCHEMA_VERSION:
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
    except Exception:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


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
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            raise


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
    prototype = prototype_dir_for_target(demand_dir)
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
        terminate_preview_pid(int(existing_health.get("pid") or existing_state.get("pid") or 0))
        wait_preview_stopped(existing_state, prototype)
    if existing_state:
        clear_preview_state(prototype)

    port, port_error = choose_preview_port(requested_port)
    if port is None:
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "failures": [str(port_error)]}

    token = uuid.uuid4().hex
    started_at = utc_now_iso()
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
        "started_at": started_at,
        "expires_at": preview_expires_at(ttl_minutes),
    }
    args = [
        sys.executable,
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
    if os.name == "nt":
        base_creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        breakaway_creationflags = base_creationflags | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
        if breakaway_creationflags:
            popen_kwargs["creationflags"] = breakaway_creationflags
    else:
        popen_kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(args, **popen_kwargs)
    except PermissionError:
        if os.name != "nt" or not popen_kwargs.get("creationflags"):
            raise
        popen_kwargs["creationflags"] = base_creationflags
        process = subprocess.Popen(args, **popen_kwargs)
    state["pid"] = process.pid

    deadline = time.time() + PREVIEW_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        health = fetch_preview_health(port, timeout=0.25)
        if health and health.get("token") == token and Path(str(health.get("prototype_dir") or health.get("demand_dir"))).resolve() == prototype:
            write_json_file(preview_state_path(prototype), state)
            return preview_result_from_state(state, prototype, "started")
        if process.poll() is not None:
            break
        time.sleep(0.1)

    if process.poll() is None:
        terminate_preview_pid(process.pid)
    return {
        "ok": False,
        "status": "failed",
        "demand_dir": str(demand),
        "prototype_dir": str(prototype),
        "port": port,
        "pid": process.pid,
        "failures": ["Preview server did not become ready in time."],
    }


def stop_preview(demand_dir: Path) -> dict[str, object]:
    prototype = prototype_dir_for_target(demand_dir)
    demand = demand_root_for_prototype(prototype)
    state = load_preview_state(prototype)
    if not state:
        return {"ok": True, "status": "not_running", "demand_dir": str(demand), "prototype_dir": str(prototype), "warnings": ["No ProtoPilot preview state found."]}
    health = active_preview_health(state, prototype)
    if not health:
        clear_preview_state(prototype)
        return {"ok": True, "status": "stale_cleared", "demand_dir": str(demand), "prototype_dir": str(prototype), "warnings": ["Stale preview state was removed; no matching live preview server was found."]}
    pid = int(health.get("pid") or state.get("pid") or 0)
    if pid > 0:
        terminate_preview_pid(pid)
    stopped = wait_preview_stopped(state, prototype)
    if not stopped:
        return {"ok": False, "status": "failed", "demand_dir": str(demand), "prototype_dir": str(prototype), "failures": [f"Preview process did not stop: {pid}"]}
    clear_preview_state(prototype)
    return {"ok": True, "status": "stopped", "demand_dir": str(demand), "prototype_dir": str(prototype), "port": state.get("port"), "pid": pid}


def run_preview_server(demand_dir: Path, port: int, token: str, ttl_minutes: int, prototype_dir: Path | None = None) -> int:
    demand = demand_dir.expanduser().resolve()
    prototype = prototype_dir.expanduser().resolve() if prototype_dir else prototype_dir_for_target(demand)
    if not demand.is_dir():
        print(json.dumps({"ok": False, "failure": f"Demand folder not found: {demand}"}, ensure_ascii=False), file=sys.stderr)
        return 3

    class ProtoPilotPreviewHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(demand), **kwargs)

        def send_json_response(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == PREVIEW_HEALTH_PATH:
                health = {
                    "ok": True,
                    "schema_version": PREVIEW_SCHEMA_VERSION,
                    "token": token,
                    "demand_dir": str(demand),
                    "prototype_dir": str(prototype),
                    "pid": os.getpid(),
                    "port": port,
                }
                health.update(preview_text_save_capabilities(prototype))
                self.send_json_response(
                    200,
                    health,
                )
                return
            super().do_GET()

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path != PREVIEW_SAVE_TEXT_PATCH_PATH:
                self.send_json_response(404, {"ok": False, "status": "failed", "failures": ["Unknown preview endpoint."]})
                return
            if self.headers.get("X-ProtoPilot-Preview-Token") != token:
                self.send_json_response(403, {"ok": False, "status": "failed", "failures": ["Invalid preview save token."]})
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self.send_json_response(400, {"ok": False, "status": "failed", "failures": ["Invalid Content-Length."]})
                return
            if length <= 0 or length > 1024 * 1024:
                self.send_json_response(413, {"ok": False, "status": "failed", "failures": ["Patch payload is empty or too large."]})
                return
            try:
                payload = self.rfile.read(length).decode("utf-8")
                patch = json.loads(payload)
            except UnicodeDecodeError:
                self.send_json_response(400, {"ok": False, "status": "failed", "failures": ["Patch payload must be UTF-8."]})
                return
            except json.JSONDecodeError as error:
                self.send_json_response(400, {"ok": False, "status": "failed", "failures": [f"Patch payload is not valid JSON: {error}"]})
                return
            if not isinstance(patch, dict):
                self.send_json_response(400, {"ok": False, "status": "failed", "failures": ["Patch root must be a JSON object."]})
                return
            try:
                result = save_text_patch_from_preview(prototype, patch)
            except Exception as error:  # pragma: no cover - keeps preview alive after unexpected local IO errors.
                result = {"ok": False, "status": "failed", "failures": [f"Unexpected save error: {error}"]}
            self.send_json_response(200 if result.get("ok") else 400, result)

        def log_message(self, _format: str, *args: object) -> None:
            return

    class PreviewTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        with PreviewTCPServer((PREVIEW_HOST, port), ProtoPilotPreviewHandler) as server:
            timer: threading.Timer | None = None
            if ttl_minutes > 0:
                timer = threading.Timer(ttl_minutes * 60, server.shutdown)
                timer.daemon = True
                timer.start()
            print(json.dumps({"ok": True, "url": preview_url(port), "pid": os.getpid()}, ensure_ascii=False), flush=True)
            try:
                server.serve_forever(poll_interval=0.5)
            finally:
                if timer:
                    timer.cancel()
    except OSError as exc:
        print(json.dumps({"ok": False, "failure": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    return 0

def command_prepare(args: argparse.Namespace) -> int:
    result = prepare(Path(args.prd), Path(args.skill_root), dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    result = build_preflight_result(Path(args.target))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_scaffold(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).resolve()
    prepared = prepare(Path(args.prd), skill_root, dry_run=False)
    prd_path = Path(str(prepared["prd_path"]))
    index_path = Path(str(prepared["index_path"]))
    if index_path.exists() and not args.force:
        fail(f"index.html already exists; use --force only when you intend to replace the presentation stage: {index_path}")

    title = args.title or read_prd_title(prd_path)
    generated_area = default_generated_area(title)
    if args.generated_area:
        generated_area = extract_generated_fragment(Path(args.generated_area).read_text(encoding="utf-8"))
    design_context = prepared["references"].get("recommended_design_context") or prepared["references"].get("design_md") or "none"
    html_text = render_shell_index(
        skill_root=skill_root,
        prd_path=prd_path,
        title=title,
        lang=args.lang,
        prd_viewer_src=str(prepared["prd_viewer_src"]),
        generated_area=generated_area,
        design_context=str(design_context),
    )
    index_path.write_text(html_text, encoding="utf-8")
    result = {**prepared, "created_index": str(index_path.resolve()), "title": title, "lang": args.lang}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_inject(args: argparse.Namespace) -> int:
    if bool(getattr(args, "strict", False)):
        fragment_validation = validate_fragment_file(Path(args.fragment), strict=True)
        if not fragment_validation["ok"]:
            print(json.dumps(fragment_validation, ensure_ascii=False, indent=2), file=sys.stderr)
            return 3
    result = inject_generated_area(Path(args.index), Path(args.fragment))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    result = build_prototype_plan(
        Path(args.target),
        out=getattr(args, "out", None),
        reference_prompt_handled=bool(getattr(args, "reference_prompt_handled", False)),
        existing_screen_prompt_handled=bool(getattr(args, "existing_screen_prompt_handled", False)),
        reset=bool(getattr(args, "reset", False)),
        generation_mode=getattr(args, "generation_mode", None),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_validate_plan(args: argparse.Namespace) -> int:
    result = validate_plan_file(Path(args.plan), final=bool(getattr(args, "final", False)))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_render_fragment(args: argparse.Namespace) -> int:
    result = write_rendered_fragment(Path(args.plan), out=getattr(args, "out", None), update_plan=not bool(getattr(args, "no_update_plan", False)))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_init_content(args: argparse.Namespace) -> int:
    result = init_content_package(Path(args.demand_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_package_check(args: argparse.Namespace) -> int:
    result = validate_content_package(
        Path(args.demand_dir),
        strict=bool(getattr(args, "strict", False)),
        final=bool(getattr(args, "final", False)),
        require_fresh_hashes=bool(getattr(args, "fresh", False)),
    )
    if not result["ok"]:
        result = {key: value for key, value in result.items() if key not in {"manifest", "plan", "screen_records"}}
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    result = {key: value for key, value in result.items() if key not in {"manifest", "plan", "screen_records"}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_build_content(args: argparse.Namespace) -> int:
    result = build_content_package(
        Path(args.demand_dir),
        check=bool(getattr(args, "check", False)),
        update_plan=not bool(getattr(args, "no_update_plan", False)),
    )
    if isinstance(result.get("package_validation"), dict):
        result["package_validation"] = {
            key: value
            for key, value in result["package_validation"].items()
            if key not in {"manifest", "plan", "screen_records"}
        }
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_validate_fragment(args: argparse.Namespace) -> int:
    result = validate_fragment_file(Path(args.fragment), strict=bool(getattr(args, "strict", False)))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_sync_plan(args: argparse.Namespace) -> int:
    result = sync_plan_with_fragment(Path(args.plan), Path(args.fragment))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_quality_check(args: argparse.Namespace) -> int:
    result = quality_check(
        Path(args.target),
        strict=bool(getattr(args, "strict", False)),
        render=bool(getattr(args, "render", False)),
    )
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_apply_edit_patch(args: argparse.Namespace) -> int:
    result = apply_edit_patch(Path(args.demand_dir), Path(args.patch_file))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_final_check(args: argparse.Namespace) -> int:
    result = final_check(Path(args.demand_dir), require_content=bool(getattr(args, "require_content", False)))
    require_complete = bool(getattr(args, "require_complete", False))
    if require_complete and result.get("status") != "complete":
        result.setdefault("blockers", []).append("--require-complete was requested, but final-check status is not complete.")
        result["ok"] = False
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_preview(args: argparse.Namespace) -> int:
    result = start_preview(
        Path(args.demand_dir),
        requested_port=int(args.port) if getattr(args, "port", None) is not None else None,
        ttl_minutes=int(getattr(args, "ttl_minutes", PREVIEW_DEFAULT_TTL_MINUTES)),
    )
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_stop_preview(args: argparse.Namespace) -> int:
    result = stop_preview(Path(args.demand_dir))
    if not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_preview_server(args: argparse.Namespace) -> int:
    return run_preview_server(
        Path(args.demand_dir),
        port=int(args.port),
        token=str(args.token),
        ttl_minutes=int(getattr(args, "ttl_minutes", PREVIEW_DEFAULT_TTL_MINUTES)),
        prototype_dir=Path(args.prototype_dir) if getattr(args, "prototype_dir", None) else None,
    )


def command_doctor(args: argparse.Namespace) -> int:
    result = demand_doctor(Path(args.demand_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_migrate_legacy(args: argparse.Namespace) -> int:
    result = migrate_legacy_generated_area(
        Path(args.source_dir),
        Path(args.target),
        inject=bool(args.inject),
        force=bool(args.force),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    target = Path(args.index)
    index = prototype_dir_for_target(target) / "index.html" if target.expanduser().resolve().is_dir() else target
    result = validate_index(index, strict=bool(getattr(args, "strict", False)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 3


def command_selfcheck(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).resolve()
    temp_context = None if args.keep else tempfile.TemporaryDirectory(prefix="protopilot-selfcheck-")
    temp_root = Path(tempfile.mkdtemp(prefix="protopilot-selfcheck-")) if args.keep else Path(temp_context.name)

    try:
        product_dir = temp_root / "Selfcheck Product"
        product_design_dir = product_dir / "Design"
        product_design_dir.mkdir(parents=True)
        (product_design_dir / "design.md").write_text(
            "# Selfcheck Design\n\n- 视觉：克制、清晰、用于验证宣讲台装配。\n- 图标：Lucide。\n",
            encoding="utf-8",
        )
        loose_prd = product_dir / "minimal-prd.md"
        loose_prd.write_text(
            "# 最小自检 PRD\n\n用于验证 Finn ProtoPilot HTML 的宣讲台、Markdown Viewer 和业务生成区插槽。\n",
            encoding="utf-8",
        )

        prepared = prepare(loose_prd, skill_root, dry_run=False)
        prd_path = Path(str(prepared["prd_path"]))
        index_path = Path(str(prepared["index_path"]))
        html_text = render_shell_index(
            skill_root=skill_root,
            prd_path=prd_path,
            title=read_prd_title(prd_path),
            lang="zh-CN",
            prd_viewer_src=str(prepared["prd_viewer_src"]),
            generated_area=default_generated_area(read_prd_title(prd_path)),
            design_context=str(prepared["references"].get("design_md") or "none"),
        )
        index_path.write_text(html_text, encoding="utf-8")

        valid_fragment = """<div class="proto-area-label"><span class="proto-generated-note">生成区 · 多状态拆屏自检</span></div>
<section class="journey-row">
  <div class="journey-step is-active" id="step-selfcheck-s1" data-proto-id="step-selfcheck-s1" data-proto-label="未开启 S1">
    <div class="step-header"><span class="step-number">1</span><span class="step-title">未开启 S1</span></div>
    <div class="phone-frame" data-proto-id="phone-s1" data-proto-label="未开启手机界面">
      <div class="phone-screen">
        <div class="app-screen" data-proto-id="screen-s1" data-proto-label="未开启界面">
          <div class="phone-status-bar"><span>9:41</span><span>100%</span></div>
          <div class="app-content" style="flex: 1; min-height: 0;">
            <div class="self-hero" data-proto-id="hero-s1" data-proto-label="功能说明区">
              <h3>记录驾驶行为，识别风险并提醒</h3>
              <p>用户可从这里开启驾驶侦测。</p>
              <button class="self-product-btn" data-proto-id="enable-s1" data-proto-label="启用按钮">启用</button>
            </div>
          </div>
          <div class="phone-home-indicator"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="journey-step" id="step-selfcheck-s3" data-proto-id="step-selfcheck-s3" data-proto-label="有数据 S3">
    <div class="step-header"><span class="step-number">2</span><span class="step-title">有数据 S3</span></div>
    <div class="phone-frame" data-proto-id="phone-s3" data-proto-label="有数据手机界面">
      <div class="phone-screen">
        <div class="app-screen" data-proto-id="screen-s3" data-proto-label="有数据界面">
          <div class="phone-status-bar"><span>9:41</span><span>100%</span></div>
          <div class="app-content" style="flex: 1; min-height: 0;">
            <div class="self-card" data-proto-id="metrics-s3" data-proto-label="数据统计卡">47 公里 · 最高时速 86 公里/小时</div>
          </div>
          <div class="phone-home-indicator"></div>
        </div>
      </div>
    </div>
  </div>
</section>
<section class="journey-row">
  <div class="journey-step" id="step-selfcheck-s4" data-proto-id="step-selfcheck-s4" data-proto-label="空数据 S4">
    <div class="step-header"><span class="step-number">3</span><span class="step-title">空数据 S4</span></div>
    <div class="phone-frame" data-proto-id="phone-s4" data-proto-label="空数据手机界面">
      <div class="phone-screen">
        <div class="app-screen" data-proto-id="screen-s4" data-proto-label="空数据界面">
          <div class="phone-status-bar"><span>9:41</span><span>100%</span></div>
          <div class="app-content" style="flex: 1; min-height: 0;">
            <div class="self-empty" data-proto-id="empty-s4" data-proto-label="空态说明">暂无有效行程记录</div>
          </div>
          <div class="phone-home-indicator"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="journey-step" id="step-selfcheck-s2b" data-proto-id="step-selfcheck-s2b" data-proto-label="过期 S2-b">
    <div class="step-header"><span class="step-number">4</span><span class="step-title">订阅过期 S2-b</span></div>
    <div class="phone-frame" data-proto-id="phone-s2b" data-proto-label="过期手机界面">
      <div class="phone-screen">
        <div class="app-screen" data-proto-id="screen-s2b" data-proto-label="过期界面">
          <div class="phone-status-bar"><span>9:41</span><span>100%</span></div>
          <div class="app-content" style="flex: 1; min-height: 0;">
            <div class="self-card" data-proto-id="expired-s2b" data-proto-label="过期提示">功能已暂停，订阅后可恢复运行</div>
          </div>
          <div class="phone-home-indicator"></div>
        </div>
      </div>
    </div>
  </div>
</section>"""
        fragment_path = index_path.parent / "_selfcheck-fragment.html"
        fragment_path.write_text(valid_fragment, encoding="utf-8")
        inject_generated_area(index_path, fragment_path)
        validation = validate_index(index_path)
        generated_warnings = validation["generated_area"]["warnings"]
        if generated_warnings:
            fail("selfcheck valid fragment produced generated-area warnings: " + json.dumps(generated_warnings, ensure_ascii=False))

        bad_fragment = """<section class="journey-row">
  <div class="journey-step" id="bad-step" data-proto-id="bad-step" data-proto-label="驾驶侦测主页 S1/S3/S4/S2-b">
    <div class="step-header"><span class="step-number">1</span><span class="step-title">驾驶侦测主页 S1/S3/S4/S2-b</span></div>
    <div class="phone-frame" data-proto-id="bad-phone" data-proto-label="坏例子手机">
      <div class="phone-screen">
        <div class="app-screen" data-proto-id="bad-screen" data-proto-label="坏例子界面">
          <div class="state-tabs" role="tablist" aria-label="状态切换">
            <button class="secondary-btn">S1 未开启</button>
            <button class="secondary-btn">S3 有数据</button>
            <button class="secondary-btn">S4 空</button>
            <button class="primary-btn">S2-b 过期</button>
          </div>
          <div class="app-content" style="height: 260px; border-radius: 28px 28px 0 0;">
            <button class="primary-btn">启用</button>
          </div>
        </div>
      </div>
      <div class="annotation" style="position: relative;">这个标注会挤压界面</div>
    </div>
    <div class="phone-frame" data-proto-id="bad-phone-2" data-proto-label="坏例子第二个手机">
      <div class="phone-screen"><div class="app-screen" data-proto-id="bad-screen-2" data-proto-label="第二个界面"></div></div>
    </div>
  </div>
</section>"""
        bad_check = inspect_generated_area(bad_fragment)
        expected_warning_parts = ["多个状态码", "状态切换控件", "半截", "标注", "primary-btn", "多个手机", "只圆上角"]
        bad_warning_text = "\n".join(bad_check["warnings"])
        missing_warning_parts = [part for part in expected_warning_parts if part not in bad_warning_text]
        if missing_warning_parts:
            fail(
                "selfcheck bad fragment did not trigger expected warnings: "
                + json.dumps({"missing": missing_warning_parts, "warnings": bad_check["warnings"]}, ensure_ascii=False)
            )

        result = {
            "ok": True,
            "selfcheck": "passed",
            "kept": bool(args.keep),
            "temp_root": str(temp_root) if args.keep else None,
            "index_path": str(index_path.resolve()) if args.keep else None,
            "prd_viewer_src": validation["prd_viewer_src"],
            "bad_fragment_warning_count": len(bad_check["warnings"]),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def ensure_showcase_content_plan(showcase_dir: Path, prd_path: Path) -> Path:
    plan_path = showcase_dir / PLAN_FILENAME
    existing_plan, _error = try_load_json_object(plan_path) if plan_path.is_file() else (None, None)
    existing_steps = {
        str(step.get("id")): step
        for step in (existing_plan.get("steps", []) if isinstance(existing_plan, dict) and isinstance(existing_plan.get("steps"), list) else [])
        if isinstance(step, dict) and step.get("id")
    }
    showcase_steps = [
        ("showcase-mobile-entry", "手机端入口页", "showcase-start", "Mobile App"),
        ("showcase-plan-card", "生成计划页面", "showcase-start", "Web"),
        ("showcase-loading", "加载状态", "showcase-states", "Mobile App"),
        ("showcase-empty", "空状态", "showcase-states", "Mobile App"),
        ("showcase-annotation-first", "标注示例页面", "showcase-ux", "Mobile App"),
        ("showcase-edit-patch", "改文字页面", "showcase-ux", "Web"),
    ]
    created_at = (
        str(existing_plan.get("created_at"))
        if isinstance(existing_plan, dict) and existing_plan.get("created_at")
        else utc_now_iso()
    )
    manifest, _manifest_error = try_load_json_object(showcase_dir / CONTENT_DIRNAME / CONTENT_MANIFEST_FILENAME)
    manifest_screens = manifest.get("screens", []) if isinstance(manifest, dict) and isinstance(manifest.get("screens"), list) else []
    if manifest_screens:
        manifest_steps: list[tuple[str, str, str, str]] = []
        for screen in manifest_screens:
            if not isinstance(screen, dict):
                continue
            step_id = str(screen.get("step_id") or "").strip()
            if not step_id:
                continue
            manifest_steps.append(
                (
                    step_id,
                    str(screen.get("title") or step_id),
                    str(screen.get("group_id") or "showcase"),
                    str(screen.get("platform") or "Web"),
                )
            )
        if manifest_steps:
            showcase_steps = manifest_steps
    steps: list[dict[str, object]] = []
    for step_id, title, group_id, platform in showcase_steps:
        existing = existing_steps.get(step_id, {})
        step_title = title
        steps.append(
            {
                "id": step_id,
                "title": step_title,
                "group_id": group_id,
                "platform": str(existing.get("platform") or platform),
                "prd_sections": existing.get("prd_sections") if isinstance(existing.get("prd_sections"), list) else [step_title],
                "render_as": "screen",
                "screen_kind": "showcase",
                "eligibility_reason": str(existing.get("eligibility_reason") or "Showcase step is hand-authored content package source."),
                "state": "rendered",
                "rendered": True,
                "is_showcase_sample": True,
            "notes": str(existing.get("notes") or "Showcase validation step."),
            }
        )

    section_titles = [str(step["title"]) for step in steps]
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "created_at": created_at,
        "updated_at": utc_now_iso(),
        "generation_mode": "content_package",
        "source": {
            "prd_path": browser_relative_path(prd_path, showcase_dir),
            "demand_dir": str(demand_root_for_prototype(showcase_dir).resolve()),
            "prototype_dir": str(showcase_dir.resolve()),
            "design_context": "examples/showcase-html",
        },
        "preflight": {
            "recommended_action": "generate_from_prd",
            "reference_status": "not_provided",
            "reference_prompt_policy": "continue_by_default",
            "original_screen_status": "not_applicable",
            "original_screen_prompt_policy": "ask_only_when_blocking",
            "demand_reference_prompt_required": False,
            "demand_reference_prompt_handled": True,
            "existing_screen_prompt_recommended": False,
            "existing_screen_prompt_handled": True,
            "legacy_candidates": [],
            "reference_images_found": False,
            "reference_usage_required": False,
        },
        "groups": [
            {
                "id": "showcase-start",
                "title": "开场与流程",
                "description": "Showcase entry and plan-first workflow.",
                "step_ids": ["showcase-mobile-entry", "showcase-plan-card"],
            },
            {
                "id": "showcase-states",
                "title": "多状态拆屏",
                "description": "Separate real UI states instead of stuffing them into one explanation screen.",
                "step_ids": ["showcase-loading", "showcase-empty"],
            },
            {
                "id": "showcase-ux",
                "title": "标注与改文字",
                "description": "Annotation-first explanation and real text-save regression.",
                "step_ids": ["showcase-annotation-first", "showcase-edit-patch"],
            },
        ],
        "steps": steps,
        "coverage": {
            "covered_prd_sections": section_titles,
            "planned_prd_sections": section_titles,
            "all_prd_sections": section_titles + ["PRD section disposition sample"],
            "disposition": [
                {
                    "prd_section": "PRD section disposition sample",
                    "disposition": "annotation",
                    "reason": "Showcase explanatory material is demonstrated as annotation/PRD Viewer content, not a phone screen.",
                    "decision_source": "showcase_fixture",
                }
            ],
            "omitted": [],
            "notes": "Showcase plan exists so final-check can exercise the full content package delivery check.",
        },
        "references_available": [],
        "references_used": [],
        "validation": {"last_strict_ok": None, "failures": [], "warnings": []},
        "revision_history": (
            existing_plan.get("revision_history", [])
            if isinstance(existing_plan, dict) and isinstance(existing_plan.get("revision_history"), list)
            else []
        ),
    }
    if manifest_screens:
        group_titles = {
            "result": "生成结果",
            "generation": "生成逻辑",
            "presenter": "宣讲体验",
            "local-review": "本地修改与检查",
            "showcase-start": "开场与流程",
            "showcase-states": "多状态拆屏",
            "showcase-ux": "标注与改文字",
        }
        group_ids = list(dict.fromkeys(str(step["group_id"]) for step in steps))
        plan["groups"] = [
            {
                "id": group_id,
                "title": group_titles.get(group_id, group_id),
                "description": "Showcase content package validation group.",
                "step_ids": [str(step["id"]) for step in steps if str(step.get("group_id")) == group_id],
            }
            for group_id in group_ids
        ]
    write_json_file(plan_path, plan)
    return plan_path


def command_build_showcase(args: argparse.Namespace) -> int:
    skill_root = Path(args.skill_root).resolve()
    showcase_root = skill_root / "examples" / "showcase-html"
    showcase_dir = showcase_root / PROTOTYPE_DIRNAME
    prd_path = showcase_root / "proto-pilot-manual.md"
    fragment_path = showcase_dir / "generated-area-fragment.html"
    index_path = showcase_dir / "index.html"

    if not prd_path.is_file():
        fail(f"Showcase manual PRD not found: {prd_path}")

    showcase_dir.mkdir(parents=True, exist_ok=True)
    old_content = showcase_root / CONTENT_DIRNAME
    if old_content.exists() and not (showcase_dir / CONTENT_DIRNAME).exists():
        shutil.move(str(old_content), str(showcase_dir / CONTENT_DIRNAME))
    plan_path = ensure_showcase_content_plan(showcase_dir, prd_path)
    copy_shell_assets(skill_root, showcase_dir, dry_run=False)
    built = build_content_package(showcase_dir, check=False, update_plan=True)
    if not built["ok"]:
        print(json.dumps(built, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    title = args.title or read_prd_title(prd_path)
    generated_area = extract_generated_fragment(fragment_path.read_text(encoding="utf-8"))
    html_text = render_shell_index(
        skill_root=skill_root,
        prd_path=prd_path,
        title=title,
        lang=args.lang,
        prd_viewer_src="../proto-pilot-manual.md",
        generated_area=generated_area,
        design_context="examples/showcase-html",
    )
    index_path.write_text(html_text, encoding="utf-8")
    result = {
        "ok": True,
        "content_package": True,
        "showcase_dir": str(showcase_root.resolve()),
        "prototype_dir": str(showcase_dir.resolve()),
        "index_path": str(index_path.resolve()),
        "manual_prd": str(prd_path.resolve()),
        "fragment_path": str(fragment_path.resolve()),
        "plan_path": str(plan_path.resolve()),
        "content_manifest": str((showcase_dir / CONTENT_DIRNAME / CONTENT_MANIFEST_FILENAME).resolve()),
        "prd_viewer_src": "../proto-pilot-manual.md",
        "build_content": {
            "ok": built.get("ok"),
            "status": built.get("status"),
            "summary": built.get("summary", {}),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Finn ProtoPilot HTML deterministic tooling.")
    parser.add_argument(
        "--skill-root",
        default=str(skill_root_from_script()),
        help="Finn ProtoPilot HTML skill root. Defaults to this script's parent folder.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_skill_root_arg(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument(
            "--skill-root",
            default=argparse.SUPPRESS,
            help="Finn ProtoPilot HTML skill root. Accepted here for wrapper/backward compatibility.",
        )

    prepare_parser = sub.add_parser("prepare", help="Prepare a standard demand folder from a PRD.")
    add_skill_root_arg(prepare_parser)
    prepare_parser.add_argument("prd", help="Path to the source PRD Markdown file.")
    prepare_parser.add_argument("--dry-run", action="store_true", help="Report actions without moving/copying files.")
    prepare_parser.set_defaults(func=command_prepare)

    preflight_parser = sub.add_parser("preflight", help="Inspect PRD/demand inputs before generating the business area.")
    add_skill_root_arg(preflight_parser)
    preflight_parser.add_argument("target", help="Path to a PRD Markdown file or standard demand folder.")
    preflight_parser.set_defaults(func=command_preflight)

    scaffold_parser = sub.add_parser("scaffold", help="Prepare and render the fixed prototype presentation stage.")
    add_skill_root_arg(scaffold_parser)
    scaffold_parser.add_argument("prd", help="Path to the source PRD Markdown file.")
    scaffold_parser.add_argument("--title", help="Prototype title. Defaults to the first PRD heading.")
    scaffold_parser.add_argument("--lang", default="zh-CN", help="HTML lang attribute.")
    scaffold_parser.add_argument("--generated-area", help="Optional generated-area HTML fragment to inject while scaffolding.")
    scaffold_parser.add_argument("--force", action="store_true", help="Replace an existing index.html shell.")
    scaffold_parser.set_defaults(func=command_scaffold)

    inject_parser = sub.add_parser("inject", help="Replace only the generated-area slot in index.html.")
    add_skill_root_arg(inject_parser)
    inject_parser.add_argument("index", help="Path to demand index.html.")
    inject_parser.add_argument("fragment", help="Path to generated-area HTML fragment.")
    inject_parser.add_argument("--strict", action="store_true", help="Validate the fragment with strict generated-area checks before injection.")
    inject_parser.set_defaults(func=command_inject)

    plan_parser = sub.add_parser("plan", help="Create or refresh prototype-plan.json for a standard demand folder.")
    add_skill_root_arg(plan_parser)
    plan_parser.add_argument("target", help="Path to a standard demand folder or PRD inside it.")
    plan_parser.add_argument("--out", help="Optional output path for prototype-plan.json.")
    plan_parser.add_argument("--reference-prompt-handled", action="store_true", help="Legacy no-op; reference gaps are now recorded in source_audit without interrupting generation.")
    plan_parser.add_argument("--existing-screen-prompt-handled", action="store_true", help="Legacy no-op; original-screen gaps are now recorded in source_audit unless pixel-level replication is requested.")
    plan_parser.add_argument("--reset", action="store_true", help="Rebuild groups/steps from the PRD instead of merging the existing plan.")
    plan_parser.add_argument("--generation-mode", choices=sorted(PLAN_GENERATION_MODES), help="Override generation_mode. Defaults to content_package for new plans.")
    plan_parser.set_defaults(func=command_plan)

    validate_plan_parser = sub.add_parser("validate-plan", help="Validate prototype-plan.json coverage and preflight handling.")
    add_skill_root_arg(validate_plan_parser)
    validate_plan_parser.add_argument("plan", help="Path to prototype-plan.json.")
    validate_plan_parser.add_argument("--final", action="store_true", help="Fail if planned steps remain unrendered without coverage.omitted reasons.")
    validate_plan_parser.set_defaults(func=command_validate_plan)

    render_fragment_parser = sub.add_parser("render-fragment", help="Render generated-area-fragment.html from prototype-plan.json.")
    add_skill_root_arg(render_fragment_parser)
    render_fragment_parser.add_argument("plan", help="Path to prototype-plan.json.")
    render_fragment_parser.add_argument("--out", help="Optional generated-area fragment output path.")
    render_fragment_parser.add_argument("--no-update-plan", action="store_true", help="Do not write rendered/validation status back to prototype-plan.json.")
    render_fragment_parser.set_defaults(func=command_render_fragment)

    init_content_parser = sub.add_parser("init-content", help="Create or refresh prototype-content manifest from prototype-plan.json.")
    add_skill_root_arg(init_content_parser)
    init_content_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    init_content_parser.set_defaults(func=command_init_content)

    package_check_parser = sub.add_parser("package-check", help="Validate prototype-content manifest, screens, and scoped content.css.")
    add_skill_root_arg(package_check_parser)
    package_check_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    package_check_parser.add_argument("--strict", action="store_true", help="Fail on source package contract warnings that would make builds unstable.")
    package_check_parser.add_argument("--final", action="store_true", help="Fail if plan steps are missing from manifest and coverage.omitted.")
    package_check_parser.add_argument("--fresh", action="store_true", help="Fail when manifest screen hashes are missing or stale.")
    package_check_parser.set_defaults(func=command_package_check)

    build_content_parser = sub.add_parser("build-content", help="Build generated-area-fragment.html from prototype-content.")
    add_skill_root_arg(build_content_parser)
    build_content_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    build_content_parser.add_argument("--check", action="store_true", help="Dry-run freshness check; do not write files.")
    build_content_parser.add_argument("--no-update-plan", action="store_true", help="Do not write rendered/validation status back to prototype-plan.json.")
    build_content_parser.set_defaults(func=command_build_content)

    validate_fragment_parser = sub.add_parser("validate-fragment", help="Validate a generated-area HTML fragment before injection.")
    add_skill_root_arg(validate_fragment_parser)
    validate_fragment_parser.add_argument("fragment", help="Path to generated-area HTML fragment.")
    validate_fragment_parser.add_argument("--strict", action="store_true", help="Fail on generated-area strict quality regressions.")
    validate_fragment_parser.set_defaults(func=command_validate_fragment)

    sync_plan_parser = sub.add_parser("sync-plan", help="Safely mark exact plan steps rendered from a strict-valid hand-written fragment.")
    add_skill_root_arg(sync_plan_parser)
    sync_plan_parser.add_argument("plan", help="Path to prototype-plan.json.")
    sync_plan_parser.add_argument("fragment", help="Path to generated-area HTML fragment.")
    sync_plan_parser.set_defaults(func=command_sync_plan)

    quality_check_parser = sub.add_parser("quality-check", help="Run generic presentation-quality checks without replacing final-check.")
    add_skill_root_arg(quality_check_parser)
    quality_check_parser.add_argument("target", help="Path to a demand folder, index.html, or generated-area-fragment.html.")
    quality_check_parser.add_argument("--render", action="store_true", help="Also run browser geometry checks when Playwright is available.")
    quality_check_parser.add_argument("--strict", action="store_true", help="Fail on quality warnings that should block a polished handoff.")
    quality_check_parser.set_defaults(func=command_quality_check)

    apply_patch_parser = sub.add_parser("apply-edit-patch", help="Apply a ProtoPilotShell content edit patch back to prototype-content screens.")
    add_skill_root_arg(apply_patch_parser)
    apply_patch_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    apply_patch_parser.add_argument("patch_file", help="JSON text patch copied from ProtoPilotShell or preview edit mode.")
    apply_patch_parser.set_defaults(func=command_apply_edit_patch)

    final_check_parser = sub.add_parser("final-check", help="Check final delivery by verifying plan, fragment, and index together.")
    add_skill_root_arg(final_check_parser)
    final_check_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    final_check_parser.add_argument("--require-content", action="store_true", help="Fail unless generation_mode is content_package.")
    final_check_parser.add_argument("--require-complete", action="store_true", help="Fail unless status is complete.")
    final_check_parser.set_defaults(func=command_final_check)

    preview_parser = sub.add_parser("preview", help="Start or reuse a local HTTP preview for one demand folder.")
    add_skill_root_arg(preview_parser)
    preview_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    preview_parser.add_argument("--port", type=int, help=f"Port to bind. Defaults to the first free port in {PREVIEW_PORT_START}-{PREVIEW_PORT_END}.")
    preview_parser.add_argument("--ttl-minutes", type=int, default=PREVIEW_DEFAULT_TTL_MINUTES, help="Auto-stop preview after this many minutes. Use 0 to disable TTL.")
    preview_parser.set_defaults(func=command_preview)

    stop_preview_parser = sub.add_parser("stop-preview", help="Stop the local HTTP preview for one demand folder.")
    add_skill_root_arg(stop_preview_parser)
    stop_preview_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    stop_preview_parser.set_defaults(func=command_stop_preview)

    preview_server_parser = sub.add_parser("preview-server", help=argparse.SUPPRESS)
    preview_server_parser.add_argument("demand_dir", help=argparse.SUPPRESS)
    preview_server_parser.add_argument("--prototype-dir", help=argparse.SUPPRESS)
    preview_server_parser.add_argument("--port", type=int, required=True, help=argparse.SUPPRESS)
    preview_server_parser.add_argument("--token", required=True, help=argparse.SUPPRESS)
    preview_server_parser.add_argument("--ttl-minutes", type=int, default=PREVIEW_DEFAULT_TTL_MINUTES, help=argparse.SUPPRESS)
    preview_server_parser.set_defaults(func=command_preview_server)

    doctor_parser = sub.add_parser("doctor", help="Inspect a demand folder and report the next ProtoPilot action.")
    add_skill_root_arg(doctor_parser)
    doctor_parser.add_argument("demand_dir", help="Path to the standard demand folder.")
    doctor_parser.set_defaults(func=command_doctor)

    migrate_parser = sub.add_parser("migrate-legacy", help="Extract a legacy generated area into a standard demand folder.")
    add_skill_root_arg(migrate_parser)
    migrate_parser.add_argument("source_dir", help="Legacy prototype directory containing generated-area-fragment.html or index.html.")
    migrate_parser.add_argument("target", help="Target demand folder or target index.html.")
    migrate_parser.add_argument("--inject", action="store_true", help="Inject the migrated fragment into target index.html immediately.")
    migrate_parser.add_argument("--force", action="store_true", help="Replace an existing generated-area-fragment.html in the target folder.")
    migrate_parser.set_defaults(func=command_migrate_legacy)

    validate_parser = sub.add_parser("validate", help="Validate a generated ProtoPilot index.html presentation stage.")
    add_skill_root_arg(validate_parser)
    validate_parser.add_argument("index", help="Path to demand index.html.")
    validate_parser.add_argument("--strict", action="store_true", help="Fail on generated-area quality regressions that break editing or presentation.")
    validate_parser.set_defaults(func=command_validate)

    selfcheck_parser = sub.add_parser("selfcheck", help="Generate a temporary minimal prototype and validate it.")
    add_skill_root_arg(selfcheck_parser)
    selfcheck_parser.add_argument("--keep", action="store_true", help="Keep the temporary selfcheck folder for manual inspection.")
    selfcheck_parser.set_defaults(func=command_selfcheck)

    showcase_parser = sub.add_parser("build-showcase", help="Build the manual-style showcase example for human review.")
    add_skill_root_arg(showcase_parser)
    showcase_parser.add_argument("--title", help="Showcase title. Defaults to the first manual heading.")
    showcase_parser.add_argument("--lang", default="zh-CN", help="HTML lang attribute.")
    showcase_parser.set_defaults(func=command_build_showcase)

    sub.metavar = (
        "{prepare,preflight,scaffold,inject,plan,validate-plan,render-fragment,init-content,"
        "package-check,build-content,validate-fragment,sync-plan,quality-check,apply-edit-patch,"
        "final-check,preview,stop-preview,doctor,migrate-legacy,validate,selfcheck,build-showcase}"
    )
    sub._choices_actions = [choice for choice in sub._choices_actions if choice.dest != "preview-server"]
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
