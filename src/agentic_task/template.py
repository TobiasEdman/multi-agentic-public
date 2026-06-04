"""Minimal renderer for AGENTS.md.tmpl-style templates.

Two operations on top of plain string substitution:

1. ``{{VAR}}`` placeholders → values from a context dict.
2. ``<!--IF flag-->...<!--/IF flag-->`` blocks → kept iff ``flag`` is in
   ``context["flags"]``, dropped otherwise.

Conditional blocks are line-oriented (the ``<!--IF...-->`` and ``<!--/IF...-->``
markers must each sit on their own line). HTML-comment delimiters were chosen
over Jinja-style ``{% if %}`` so the unrendered template is still valid
markdown — viewers display nothing — and so the renderer needs no third-party
dependency. When ``agentic-task init`` lands, it can either keep this minimal
renderer or upgrade to Jinja2 without changing the template's surface syntax.

Spec: docs/track1-replication-findings.md Friction #2; commit msg of
``templates: parameterise AGENTS.md.tmpl with repo_kind`` for the design call.
"""

from __future__ import annotations

import re
from typing import Iterable

_VAR_PATTERN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
_BLOCK_PATTERN = re.compile(
    r"^[ \t]*<!--IF[ \t]+([^\s>]+)[ \t]*-->[ \t]*\r?\n"
    r"(.*?)"
    r"^[ \t]*<!--/IF[ \t]+\1[ \t]*-->[ \t]*\r?\n",
    flags=re.MULTILINE | re.DOTALL,
)


def render(template: str, context: dict[str, object]) -> str:
    """Render a template using the conditional + variable rules above.

    Parameters
    ----------
    template:
        The raw template string.
    context:
        ``flags`` is an iterable of strings naming the conditional blocks to
        keep. Every other key is a ``{{KEY}}`` value; values are coerced via
        ``str()``.

    Unmatched ``{{VAR}}`` placeholders are left intact (so a missing value
    fails loudly rather than silently rendering as an empty string).
    """
    flags = set(_to_str_set(context.get("flags", ())))

    # 1. Strip / keep conditional blocks first, so any vars *inside* a
    #    dropped block never get substituted (and never produce
    #    misleading "missing var" errors).
    def _block_sub(match: re.Match[str]) -> str:
        flag, body = match.group(1), match.group(2)
        return body if flag in flags else ""

    rendered = _BLOCK_PATTERN.sub(_block_sub, template)

    # 2. Variable substitution.
    def _var_sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in context and key != "flags":
            return str(context[key])
        return match.group(0)  # leave unresolved placeholders intact

    return _VAR_PATTERN.sub(_var_sub, rendered)


def _to_str_set(value: object) -> Iterable[str]:
    if isinstance(value, str):
        # Common foot-gun: a single flag string iterates char-by-char.
        return [value]
    if isinstance(value, Iterable):
        return [str(v) for v in value]
    raise TypeError(f"flags must be iterable, got {type(value).__name__}")
