"""Helpers for extracting structured <tag>...</tag> blocks from AI messages."""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

from langchain_core.messages import AIMessage

_TAG_PATTERN = re.compile(r"<(?P<tag>[a-zA-Z0-9_]+)>(?P<body>.*?)</\s*(?P=tag)\s*>", re.DOTALL)


def _coerce_content(content: Sequence[object] | object) -> str:
    """Normalise LangChain content (string or content parts) into a single string."""
    if isinstance(content, str):
        return content

    parts: List[str] = []
    if isinstance(content, Iterable):
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts)


def extract_tagged_blocks(message: AIMessage) -> List[Tuple[str, str]]:
    """Return ordered (tag, body) tuples extracted from an AIMessage."""
    raw_content = _coerce_content(message.content)
    if not raw_content:
        return []

    matches: List[Tuple[str, str]] = []
    for match in _TAG_PATTERN.finditer(raw_content):
        tag = match.group("tag")
        body = match.group("body")
        if not tag or body is None:
            continue
        matches.append((tag.strip().lower(), body.strip()))
    return matches

