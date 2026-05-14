"""TargetAdapter base — abstracts the system under test.

Concrete adapters (HTTP, MCP, LangGraph trace ingest, ...) implement `send`.
Inherited shape from promptmap (https://github.com/8vana/promptmap).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TargetResponse:
    text: str
    tool_calls: list[dict[str, Any]]
    raw: dict[str, Any]


class TargetAdapter(ABC):
    @abstractmethod
    def send(self, prompt: str, **kwargs: Any) -> TargetResponse:
        """Send a prompt to the target system and return its response."""
