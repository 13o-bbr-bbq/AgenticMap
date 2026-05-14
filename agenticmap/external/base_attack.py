"""BaseAttack — abstract attack module.

Concrete attacks (direct PI, indirect PI, jailbreak, tool abuse, multi-agent
chained) implement `run` and emit Findings into the KG.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ..core.models import Finding
from .target_adapter import TargetAdapter


class BaseAttack(ABC):
    name: str = ""
    category: str = ""
    atlas_tags: list[str] = []

    @abstractmethod
    def run(self, target: TargetAdapter) -> Iterable[Finding]:
        """Run this attack against the target, yielding Findings."""
