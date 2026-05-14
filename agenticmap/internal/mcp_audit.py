"""Static audit of MCP server configurations.

Starting point for the internal pipeline — MCP config files (`mcp.json`,
`.mcp.json`, IDE-specific variants) declare tools and their permissions,
making them the most tractable static input.

Emits Findings about: missing HITL, overbroad permissions, untrusted
transports, etc. Skeleton only.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ..core.models import Finding


def audit_mcp_config(path: Path) -> Iterable[Finding]:
    """Audit an MCP configuration file and yield Findings."""
    raise NotImplementedError
