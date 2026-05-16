"""BaseAttack — abstract attack module.

Mirrors PromptMap's `engine.base_attack.BaseAttack` so AgenticMap can
host or import PromptMap attacks unchanged. Concrete AgenticMap-specific
attacks (indirect PI via KB injection, tool-abuse for Action Groups,
multi-agent chained) subclass this directly; PromptMap's 6 existing
attacks (single PI, Crescendo, PAIR, TAP, Chunked Request, autonomous
Agent) plug in by re-export once PromptMap is packaged.

TODO: replace with `from promptmap.engine.base_attack import BaseAttack`
when `promptmap-engine` is on PyPI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.models import Finding


class BaseAttack(ABC):
    name: str = ""
    category: str = ""
    atlas_tags: list[str] = []

    @abstractmethod
    async def run(self, ctx: Any, objective: str, **kwargs: Any) -> "AttackResult":  # noqa: F821
        """Run this attack with the given AttackContext and objective.

        The PromptMap signature uses `AttackContext` (which carries the
        target adapter, scorer, signatures, and session memory) and an
        `objective` string. The return type is PromptMap's `AttackResult`;
        the AgenticMap External Probe layer converts `AttackResult`
        instances into `Finding` objects before inserting them into the
        Findings KG (see `agenticmap/external/finding_adapter.py`, planned).
        """
