"""Render context — the per-request presentation inputs.

Platform-agnostic: no `telegram` import. Replaces the bare `user_tz` string that
used to be threaded through every formatter.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderContext:
    lang: str = "en"
    tz: str = "UTC"
