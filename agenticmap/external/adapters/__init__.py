"""Concrete TargetAdapter implementations.

AgentCore-first: `BedrockAgentRuntimeAdapter` (legacy Bedrock Agents via
`bedrock-agent-runtime:invoke_agent`) and `BedrockAgentCoreRuntimeAdapter`
(new AgentCore via `bedrock-agentcore:invoke_agent_runtime`).

For non-AgentCore targets (HTTP, OpenAI, Anthropic, Gemini, browser),
re-use PromptMap's adapters in `promptmap/targets/` once PromptMap is
packaged — AgenticMap intentionally does NOT reimplement those.
"""
