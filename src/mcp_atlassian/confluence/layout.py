"""Metadata and content evidence for Confluence layout, not rendered appearance."""

import json
from typing import Any

from bs4 import BeautifulSoup

WIDTH_LABELS = {"default": "narrow", "full-width": "wide", "max": "max"}
WIDTH_ALIASES = {label: raw for raw, label in WIDTH_LABELS.items()}


def normalize_width(width: str) -> str:
    """Validate a width and return its REST property value."""
    raw = WIDTH_ALIASES.get(width, width)
    if raw not in WIDTH_LABELS:
        raise ValueError("page_width must be narrow/default, wide/full-width, or max")
    return raw


def width_property(prop: dict[str, Any] | None) -> dict[str, Any]:
    """Describe one property without inferring a default from its absence."""
    if prop is None:
        return {"state": "missing", "raw": None, "label": None}
    raw = prop.get("value")
    if isinstance(raw, dict):
        raw = raw.get("value")
    label = WIDTH_LABELS.get(raw) if isinstance(raw, str) else None
    return {"state": "known" if label else "unknown", "raw": raw, "label": label}


def layout_state(published: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Combine independent reads with published precedence for legacy width."""
    selected = published if published["state"] != "missing" else draft
    comparable = all(
        item["state"] in ("known", "unknown") for item in (published, draft)
    )
    return {
        "published": published,
        "draft": draft,
        "page_width": selected["raw"] if selected["state"] == "known" else None,
        "conflict": published["raw"] != draft["raw"] if comparable else None,
        "rendered_verified": False,
    }


def inspect_storage(storage: str, limit: int = 200) -> dict[str, Any]:
    """Extract explicit HTML alignment, size, and structure without page text."""
    soup = BeautifulSoup(storage, "html.parser")
    evidence = []
    tags = soup.find_all(
        [
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "div",
            "table",
            "td",
            "th",
            "img",
            "ac:image",
            "ac:layout",
            "ac:layout-section",
            "ac:layout-cell",
        ]
    )
    for index, tag in enumerate(tags[:limit]):
        style = {}
        for declaration in str(tag.get("style", "")).split(";"):
            key, separator, value = declaration.partition(":")
            if separator:
                style[key.strip().lower()] = value.strip()
        alignment = {
            key: value
            for key, value in {
                "text-align": style.get("text-align"),
                "align": tag.get("align"),
                "ac:align": tag.get("ac:align"),
                "ac:layout": tag.get("ac:layout"),
                "float": style.get("float"),
                "margin-left": style.get("margin-left"),
                "margin-right": style.get("margin-right"),
            }.items()
            if value is not None
        }
        size = {
            key: tag.get(key, style.get(key))
            for key in ("width", "height", "ac:width", "ac:height")
            if tag.get(key, style.get(key)) is not None
        }
        evidence.append(
            {
                "index": index,
                "type": tag.name,
                "alignment_state": "explicit" if alignment else "unspecified",
                "alignment": alignment,
                "size": size,
                "structure": {
                    key: tag[key]
                    for key in ("ac:type", "colspan", "rowspan")
                    if key in tag.attrs
                },
            }
        )
    return {"state": "read", "evidence": evidence, "truncated": len(tags) > limit}


def inspect_adf(value: str | dict[str, Any], limit: int = 200) -> dict[str, Any]:
    """Extract ADF alignment marks and block attributes without media identifiers."""
    root = json.loads(value) if isinstance(value, str) else value
    if not isinstance(root, dict):
        raise ValueError("ADF must be an object")
    evidence: list[dict[str, Any]] = []
    stack = [(root, "doc")]
    visited = 0
    while stack and len(evidence) < limit and visited < 10000:
        node, path = stack.pop()
        visited += 1
        kind = node.get("type")
        attrs = node.get("attrs", {})
        if not isinstance(attrs, dict):
            raise ValueError("ADF attrs must be an object")
        alignment = {
            key: attrs[key] for key in ("alignment", "align", "layout") if key in attrs
        }
        marks = node.get("marks", [])
        if not isinstance(marks, list):
            raise ValueError("ADF marks must be an array")
        for mark in marks:
            if not isinstance(mark, dict):
                raise ValueError("ADF marks must be objects")
            if mark.get("type") == "alignment":
                mark_attrs = mark.get("attrs", {})
                if not isinstance(mark_attrs, dict):
                    raise ValueError("ADF mark attrs must be an object")
                alignment["mark"] = mark_attrs.get("align")
        if kind not in ("doc", "text", "hardBreak"):
            evidence.append(
                {
                    "path": path,
                    "type": kind,
                    "alignment_state": "explicit" if alignment else "unspecified",
                    "alignment": alignment,
                    "size": {
                        key: attrs[key] for key in ("width", "height") if key in attrs
                    },
                    "structure": {
                        key: attrs[key]
                        for key in ("colspan", "rowspan", "colwidth", "layout")
                        if key in attrs
                    },
                }
            )
        children = node.get("content", [])
        if not isinstance(children, list):
            raise ValueError("ADF content must be an array")
        for index in range(len(children) - 1, -1, -1):
            child = children[index]
            if not isinstance(child, dict):
                raise ValueError("ADF nodes must be objects")
            stack.append((child, f"{path}/content/{index}"))
    return {"state": "read", "evidence": evidence, "truncated": bool(stack)}
