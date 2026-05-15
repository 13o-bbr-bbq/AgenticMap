# CLAUDE.md

This file orients future Claude Code sessions working in this repository.

## Project

**AgenticMap** is an open-source AI Security Posture Management (AI-SPM) tool for AI / agentic systems. First target platform: **Amazon Bedrock AgentCore**. It surfaces vulnerabilities and governance gaps specific to LLM chatbots, single-agent tool users, and multi-agent systems.

Tagline:
> AgenticMap combines static configuration audit of Bedrock AgentCore with dynamic red-teaming on a shared findings graph, cross-validating the two to surface compound risks that static-only AI-SPM cannot detect — with built-in mapping to Japanese AI regulations.

### Positioning (decided 2026-05)

- **OSS** — avoid head-on competition with commercial AI-SPM SaaS (Microsoft Defender, Zenity, Wiz, Prisma Cloud, Orca, CrowdStrike, Zscaler).
- **Dual-pipeline + cross-validation** — active dynamic probing on top of static config audit. SplxAI Agentic Radar (the only OSS comparator) covers framework source code only.
- **Japan-market focus** — JP regulation mapping (METI AI 事業者ガイドライン, AI 推進法, 金融庁 AI ディスカッションペーパー, 個人情報保護法) in addition to NIST AI RMF / ISO 42001 / EU AI Act.
- **Depth-first on Bedrock AgentCore.** v0.1 scope is GA components only: AgentCore Runtime / Memory / Identity / Gateway / Policy / Browser / Code Interpreter / Observability, plus legacy Bedrock Agents (Action Groups, Knowledge Bases, Guardrails, Prompt Override). Evaluations / Payments / Registry and any preview-stage features are excluded. Azure AI Foundry / Vertex AI are out of scope until AgentCore coverage is real.

### What it detects

Split into two top-level categories.

**Misconfigurations (static)** — keyed to AgentCore feature names so checks map 1:1 to the surface they audit:

- AgentCore Runtime — inbound auth, public exposure / VPC endpoint
- AgentCore Memory — TTL, customer-managed KMS key, PII auto-masking
- AgentCore Gateway — authorization type, tool-target sprawl
- AgentCore Identity — workload identity scope (no wildcard resources)
- AgentCore Policy — Cedar rule coverage on write-capable tools, no condition-less `permit` rules
- AgentCore Browser — egress allowlist (no `*`)
- AgentCore Code Interpreter — approval flow, sandbox egress
- AgentCore Observability — CloudTrail data events, log encryption with CMK, Application Signals / X-Ray wiring
- Bedrock Agents (legacy) — Guardrail attachment + filter strengths, Action Group `requireConfirmation`, Action Group Lambda role IAM scope, Knowledge Base S3 ACL, Prompt Override safety-instruction drift

**Vulnerabilities (dynamic)** — confirmed by black-box probing of the agent endpoint:

- Direct prompt injection (safety override, system-prompt leak, jailbreak)
- Indirect prompt injection (via Knowledge Base content, via AgentCore Browser-fetched web content)
- Tool abuse (Action Group / Gateway tool target invoked outside intended scope)
- Privilege boundary violation (operating beyond workload identity / Lambda role scope)
- Multi-agent chained attacks (trust-boundary leakage between agents / sub-agents)

## Architecture

Two pipelines run over a shared substrate:

```
                 ┌────────────────────────────────────────┐
                 │       Shared Substrate                 │
                 │   Findings KG / Episodic Memory        │
                 │   4-axis Verifier                      │
                 └──────────────┬─────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                                               ▼
 ┌──────────────────┐   cross-validate          ┌──────────────────┐
 │ External Probe   │ ←──────────────────────→  │ Internal Audit   │
 │ (dynamic, black) │                           │ (static, white)  │
 └──────────────────┘                           └──────────────────┘
```

### 4-axis Verifier (inherited from clearwing)

- **REAL** — did the harmful behavior actually occur?
- **TRIGGERABLE** — reachable from an external attacker? (uses static input-path info)
- **IMPACTFUL** — what is the blast radius (tools, data, downstream)?
- **GENERAL** — one-off finding vs systemic class?

### Findings KG

Static and dynamic findings live on the **same graph** and can compound. Example:
- Static finding: "tool X has no HITL configured"
- Dynamic finding: "tool X is invokable via indirect prompt injection"
- Linked → escalated to Critical.

### Design lineage

- **promptmap** (8vana) — TargetAdapter / BaseAttack / Converter / Scorer layering; ATLAS-tagged YAML signatures.
- **clearwing** (Lazarus-AI) — dual-pipeline topology, shared substrate, 4-axis Verifier, Ranker → Hunter → Verifier → Exploiter flow.

### Competitive landscape (2026-05)

- Commercial AI-SPM SaaS: Microsoft Defender, Zenity, Wiz, Prisma Cloud, Orca, CrowdStrike, Zscaler — all closed-source, none with JP regulation focus.
- OSS comparator: **SplxAI Agentic Radar** — source-code static analysis of framework workflows (LangGraph, CrewAI, etc.); does not cover platform configuration.
- AgenticMap differentiates as: **OSS + AgentCore-first + active dynamic probing + cross-validated compound findings + JP regulation mapping**.

When refactoring, preserve the promptmap-style layer names and the clearwing 4-axis verdict structure unless the user explicitly says otherwise.

## Repository layout

```
agenticmap/
├── core/                  # orchestrator, Verifier, Findings KG, data models
├── external/              # dynamic red-teaming
│   └── adapters/          # BedrockAgentCoreAdapter (InvokeAgent), HTTP, ...
├── internal/              # static audit
│   └── bedrock/           # AgentCore + legacy Bedrock Agents config audit (first target)
├── compliance/            # JP / international regulation mappings (YAML, one file per framework)
└── datasets/
    └── signatures.yaml    # ATLAS-tagged attack signatures (promptmap-compatible)
tests/
└── fixtures/              # vulnerable AgentCore Terraform fixtures for end-to-end demo
```

## Tech stack

- Python 3.12+
- `uv` for environment and dependency management
- `boto3` for AWS API access (`bedrock-agent`, `bedrock-agentcore-control`, `bedrock-agent-runtime`). Never bundle AWS credentials — rely on the caller's AWS profile / role.
- Multi-provider LLM support (OpenAI, Anthropic, Bedrock, Ollama) is for the **attack-side** LLM (judge / payload synthesis), not for the target. Targets are Bedrock-only initially. Provider-agnostic wrapper — never hard-code a single SDK in core/external/internal.

## Conventions

- Core data models live in [agenticmap/core/models.py](agenticmap/core/models.py): `Finding`, `AgentNode`, `ToolEdge`, `Verdict`.
- New attack signatures go in [agenticmap/datasets/signatures.yaml](agenticmap/datasets/signatures.yaml) with ATLAS tags.
- Target adapters subclass `TargetAdapter` in [agenticmap/external/target_adapter.py](agenticmap/external/target_adapter.py). The Bedrock-specific adapter lives at `agenticmap/external/adapters/bedrock_agentcore.py` (planned).
- Attacks subclass `BaseAttack` in [agenticmap/external/base_attack.py](agenticmap/external/base_attack.py).
- AgentCore static checks live in `agenticmap/internal/bedrock/`, one module per concept (`guardrail.py`, `action_group.py`, `memory.py`, `gateway.py`, `identity.py`, `network.py`, `observability.py`). Check definitions are declared in [agenticmap/internal/bedrock/checks.yaml](agenticmap/internal/bedrock/checks.yaml).
- Compliance mappings live in `agenticmap/compliance/` as YAML — one file per framework (`jp_meti.yaml`, `jp_fsa.yaml`, `jp_appi.yaml`, `jp_ai_promotion_act.yaml`, `nist_ai_rmf.yaml`, `iso_42001.yaml`, `eu_ai_act.yaml`, `mitre_atlas.yaml`). Each `Finding` may carry tags from multiple frameworks.
- Static checks emit `Finding` objects into the shared KG; they do not print or assert directly.

## Development commands

```bash
uv sync                                                          # install / sync dependencies
uv run pytest                                                    # run tests
uv run agenticmap --help                                         # CLI entrypoint (planned)
uv run agenticmap audit-bedrock --region us-east-1 --agent-id X  # first-target subcommand (planned)
```

## Status

Early scaffolding. AgentCore-first roadmap:

1. ✓ Repo skeleton + `pyproject.toml` + this CLAUDE.md
2. ✓ Core data models (`Finding`, `AgentNode`, `ToolEdge`, `Verdict`)
3. Internal audit — AgentCore static checks (Guardrail attachment, Action Group `requireConfirmation`, IAM scope, Memory KMS/TTL, Gateway auth, Observability wiring)
4. External probe — `BedrockAgentCoreAdapter` invoking the agent endpoint + single-shot direct PI signature
5. Compound Finding wiring — link static + dynamic findings on the KG and surface in 4-axis Verdict
6. JP regulation mapping — `compliance/jp_*.yaml` tables for METI / 金融庁 / 個人情報保護法 / AI 推進法
7. CLI: `agenticmap audit-bedrock --region <r> --agent-id <id>` with JSON / HTML report
8. Vulnerable AgentCore fixture (Terraform) under `tests/fixtures/` for end-to-end demo
9. v0.1 OSS release
