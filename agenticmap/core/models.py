"""Core data models for AgenticMap.

These types are the lingua franca between the External Probe, Internal Audit,
and the shared Findings KG. Both pipelines emit `Finding` objects; the Verifier
attaches a `Verdict`; the KG links findings via `AgentNode` / `ToolEdge`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Source(str, Enum):
    EXTERNAL = "external"
    INTERNAL = "internal"
    COMPOUND = "compound"


@dataclass
class Verdict:
    """4-axis verdict produced by the Verifier (inherited from clearwing)."""

    real: bool
    triggerable: bool
    impactful: bool
    general: bool
    rationale: str = ""

    @property
    def is_actionable(self) -> bool:
        return self.real and self.triggerable


@dataclass
class Finding:
    """A single observation from either pipeline, before or after verification."""

    id: str
    title: str
    source: Source
    severity: Severity
    category: str
    description: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    atlas_tags: list[str] = field(default_factory=list)
    related_node_ids: list[str] = field(default_factory=list)
    related_edge_ids: list[str] = field(default_factory=list)
    verdict: Verdict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentNode:
    """A node in the agent graph — an agent, a sub-agent, or an LLM call site."""

    id: str
    name: str
    kind: str  # e.g. "agent", "subagent", "llm", "router"
    system_prompt: str | None = None
    guardrails: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolEdge:
    """An edge representing a tool / capability available to an AgentNode."""

    id: str
    from_node_id: str
    tool_name: str
    protocol: str  # e.g. "mcp", "function", "http"
    hitl_required: bool = False
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
