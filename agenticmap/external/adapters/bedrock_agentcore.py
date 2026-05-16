"""Bedrock AgentCore and legacy Bedrock Agents target adapters.

Two distinct AWS APIs are wrapped here because AgenticMap targets both:

- **`BedrockAgentRuntimeAdapter`** — legacy Bedrock Agents
  (`bedrock-agent-runtime:invoke_agent`). Required to address agents
  built before AgentCore GA in 2025-10 and still in production.

- **`BedrockAgentCoreRuntimeAdapter`** — new AgentCore Runtime
  (`bedrock-agentcore:invoke_agent_runtime`). The primary target for
  AgenticMap v0.1.

Both subclass [`TargetAdapter`][agenticmap.external.target_adapter] so
PromptMap's attack engine (Single PI, Crescendo, PAIR, TAP, Chunked
Request, autonomous Agent) can drive them once wired in.

Credentials follow standard boto3 resolution — never bundled here.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any

from ..target_adapter import TargetAdapter

if TYPE_CHECKING:
    import boto3  # noqa: F401


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Bedrock Agents
# ─────────────────────────────────────────────────────────────────────────────


class BedrockAgentRuntimeAdapter(TargetAdapter):
    """Invoke a legacy Bedrock Agent via `bedrock-agent-runtime:invoke_agent`.

    The legacy API returns a streaming `completion` event stream; we
    aggregate chunks into a single string for PromptMap compatibility, but
    also retain the raw trace events (Action Group invocations, Knowledge
    Base retrievals, Guardrail traces) on the adapter for use by
    AgenticMap-side tool-abuse detection.
    """

    def __init__(
        self,
        agent_id: str,
        agent_alias_id: str,
        region: str = "us-east-1",
        *,
        enable_trace: bool = True,
    ):
        import boto3

        self._agent_id = agent_id
        self._agent_alias_id = agent_alias_id
        self._enable_trace = enable_trace
        self._client = boto3.client("bedrock-agent-runtime", region_name=region)
        self._sessions: dict[str, str] = {}
        # Per-conversation accumulated trace events for tool-abuse analysis.
        self.last_trace: dict[str, list[dict[str, Any]]] = {}

    async def send(self, prompt: str, conversation_id: str) -> str:
        session_id = self._sessions.setdefault(conversation_id, str(uuid.uuid4()))
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.invoke_agent(
                agentId=self._agent_id,
                agentAliasId=self._agent_alias_id,
                sessionId=session_id,
                inputText=prompt,
                enableTrace=self._enable_trace,
            ),
        )
        return self._consume_stream(response, conversation_id)

    def _consume_stream(self, response: dict, conversation_id: str) -> str:
        """Aggregate `completion` event stream into a single response string.

        Trace events are stashed on `self.last_trace[conversation_id]` for
        downstream tool-abuse detection (which Action Groups were invoked,
        which Knowledge Bases were retrieved).
        """
        chunks: list[str] = []
        trace_events: list[dict[str, Any]] = []
        for event in response.get("completion", []):
            if "chunk" in event:
                payload = event["chunk"].get("bytes", b"")
                if isinstance(payload, (bytes, bytearray)):
                    chunks.append(payload.decode("utf-8", errors="replace"))
            elif "trace" in event:
                trace_events.append(event["trace"])
        self.last_trace[conversation_id] = trace_events
        return "".join(chunks)

    def reset_conversation(self, conversation_id: str) -> None:
        self._sessions.pop(conversation_id, None)
        self.last_trace.pop(conversation_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# AgentCore Runtime (GA 2025-10)
# ─────────────────────────────────────────────────────────────────────────────


class BedrockAgentCoreRuntimeAdapter(TargetAdapter):
    """Invoke an AgentCore agent via `bedrock-agentcore:invoke_agent_runtime`.

    Unlike the legacy `invoke_agent`, AgentCore Runtime takes an opaque
    `payload` (caller-defined JSON) and a `runtimeSessionId`. The payload
    schema is agent-specific; this adapter defaults to
    `{"prompt": <str>}` which matches the official `bedrock-agentcore-sdk`
    samples, but can be overridden by passing `payload_template`.

    NOTE: The exact response shape of `invoke_agent_runtime` is documented
    on the per-method AWS reference page (TODO: verify). Common pattern is
    a binary event stream with `application/json` chunks. The
    `_extract_text` method below is a best-effort first cut and MUST be
    validated against a real AgentCore agent before relying on it.
    """

    def __init__(
        self,
        agent_runtime_arn: str,
        region: str = "us-east-1",
        *,
        qualifier: str | None = None,  # version/alias (DEFAULT, $LATEST, etc.)
        payload_template: dict[str, Any] | None = None,
    ):
        import boto3

        self._arn = agent_runtime_arn
        self._qualifier = qualifier
        self._payload_template = payload_template or {"prompt": "{prompt}"}
        self._client = boto3.client("bedrock-agentcore", region_name=region)
        self._sessions: dict[str, str] = {}
        self.last_raw: dict[str, Any] = {}

    async def send(self, prompt: str, conversation_id: str) -> str:
        session_id = self._sessions.setdefault(conversation_id, str(uuid.uuid4()))
        payload = self._render_payload(prompt)
        kwargs: dict[str, Any] = {
            "agentRuntimeArn": self._arn,
            "runtimeSessionId": session_id,
            "payload": json.dumps(payload).encode("utf-8"),
        }
        if self._qualifier is not None:
            kwargs["qualifier"] = self._qualifier

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: self._client.invoke_agent_runtime(**kwargs)
        )
        self.last_raw[conversation_id] = response
        return self._extract_text(response)

    def _render_payload(self, prompt: str) -> dict[str, Any]:
        """Substitute `{prompt}` placeholders in the payload template."""

        def _walk(node: Any) -> Any:
            if isinstance(node, str):
                return node.replace("{prompt}", prompt)
            if isinstance(node, dict):
                return {k: _walk(v) for k, v in node.items()}
            if isinstance(node, list):
                return [_walk(v) for v in node]
            return node

        return _walk(self._payload_template)

    def _extract_text(self, response: dict) -> str:
        """Best-effort text extraction from invoke_agent_runtime response.

        TODO: verify the actual response shape against AWS docs:
        https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore/client/invoke_agent_runtime.html
        Current assumption: response["response"] is a StreamingBody whose
        body is either a JSON object with a "completion"/"output" field, or
        an event stream of JSON chunks. Adjust once verified on a live
        AgentCore agent.
        """
        body = response.get("response")
        if body is None:
            return ""
        if hasattr(body, "read"):
            raw = body.read()
        else:
            raw = body
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return str(raw)
        if isinstance(parsed, dict):
            for key in ("output", "completion", "result", "text", "message"):
                if key in parsed:
                    val = parsed[key]
                    return val if isinstance(val, str) else json.dumps(val)
        return str(parsed)

    def reset_conversation(self, conversation_id: str) -> None:
        self._sessions.pop(conversation_id, None)
        self.last_raw.pop(conversation_id, None)
