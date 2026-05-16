"""TargetAdapter base — abstracts the system under test.

The interface mirrors PromptMap's `engine.base_target.TargetAdapter`
(https://github.com/8vana/promptmap) so AgenticMap can drive PromptMap's
attack engine without translation.

TODO: once PromptMap is packaged as `promptmap-engine`, replace this
module with a direct re-export:

    from promptmap.engine.base_target import TargetAdapter

For now the abstract class is duplicated locally to keep AgenticMap
runnable without a PromptMap install.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TargetAdapter(ABC):
    @abstractmethod
    async def send(self, prompt: str, conversation_id: str) -> str: ...

    def set_system_prompt(self, system_prompt: str, conversation_id: str) -> None:
        """Set a system prompt for a conversation. No-op for stateless targets."""

    def reset_conversation(self, conversation_id: str) -> None:
        """Clear conversation history. No-op for stateless targets."""

    async def close(self) -> None:
        """Release any resources held by the target. No-op for stateless targets."""

    async def chat_with_tools(
        self, messages: list[dict], tools: list[dict]
    ) -> "ToolCallResponse":  # noqa: F821 — forward ref resolved when PromptMap is wired in
        raise NotImplementedError(
            f"{type(self).__name__} does not support tool calling."
        )
