"""Findings Knowledge Graph.

A single graph holds findings from both pipelines plus structural agent/tool
nodes, so that static and dynamic findings can be linked and compounded.

This is an in-memory skeleton — persistence and query layers come later.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import AgentNode, Finding, ToolEdge


class FindingsKG:
    def __init__(self) -> None:
        self._nodes: dict[str, AgentNode] = {}
        self._edges: dict[str, ToolEdge] = {}
        self._findings: dict[str, Finding] = {}

    def add_node(self, node: AgentNode) -> None:
        self._nodes[node.id] = node

    def add_edge(self, edge: ToolEdge) -> None:
        self._edges[edge.id] = edge

    def add_finding(self, finding: Finding) -> None:
        self._findings[finding.id] = finding

    def nodes(self) -> Iterable[AgentNode]:
        return self._nodes.values()

    def edges(self) -> Iterable[ToolEdge]:
        return self._edges.values()

    def findings(self) -> Iterable[Finding]:
        return self._findings.values()
