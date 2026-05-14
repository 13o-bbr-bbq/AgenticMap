# CLAUDE.md

This file orients future Claude Code sessions working in this repository.

## Project

**AgenticMap** is a security audit tool for AI / agentic systems. It surfaces vulnerabilities and governance gaps specific to LLM chatbots, single-agent tool users, and multi-agent systems.

Tagline:
> AgenticMap maps both runtime behaviors and structural configurations of agentic AI systems — combining dynamic red-teaming with static architecture audit, then cross-validating findings to surface compound risks invisible to either approach alone.

### What it detects

- Missing guardrails
- System prompts that omit security rules
- Absent Human-in-the-Loop (HITL) checkpoints
- Missing steering policies (runaway-agent risk)
- Observability wiring gaps
- Direct and indirect prompt injection
- Tool abuse and privilege-boundary violations
- Multi-agent chained attacks

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
- Closest existing competitor: **SplxAI Agentic Radar** (static-only). AgenticMap differentiates by adding dynamic probing and cross-validation.

When refactoring, preserve the promptmap-style layer names and the clearwing 4-axis verdict structure unless the user explicitly says otherwise.

## Repository layout

```
agenticmap/
├── core/         # orchestrator, Verifier, Findings KG, data models
├── external/     # dynamic red-teaming (PI / jailbreak / indirect injection / tool abuse / multi-agent)
├── internal/     # static audit (graph parser / tool inventory / guardrail / HITL / observability / steering)
├── adapters/     # HTTP / MCP / LangGraph / AutoGen / CrewAI ingest
└── datasets/
    └── signatures.yaml  # ATLAS-tagged attack signatures (promptmap-compatible)
tests/
```

## Tech stack

- Python 3.12+
- `uv` for environment and dependency management
- Multi-provider LLM support: OpenAI, Anthropic, Bedrock, Ollama. Provider-agnostic client wrapper — never hard-code a single SDK in core/external/internal.

## Conventions

- Core data models live in [agenticmap/core/models.py](agenticmap/core/models.py): `Finding`, `AgentNode`, `ToolEdge`, `Verdict`.
- New attack signatures go in [agenticmap/datasets/signatures.yaml](agenticmap/datasets/signatures.yaml) with ATLAS tags.
- Target adapters subclass `TargetAdapter` in [agenticmap/external/target_adapter.py](agenticmap/external/target_adapter.py).
- Attacks subclass `BaseAttack` in [agenticmap/external/base_attack.py](agenticmap/external/base_attack.py).
- Static checks emit `Finding` objects into the shared KG; they do not print or assert directly.

## Development commands

```bash
uv sync                     # install / sync dependencies
uv run pytest               # run tests
uv run agenticmap --help    # CLI entrypoint (once implemented)
```

## Status

Early scaffolding. Initial milestones:

1. Repo skeleton + `pyproject.toml` + this CLAUDE.md
2. Core data models (`Finding`, `AgentNode`, `ToolEdge`, `Verdict`)
3. Minimal HTTP `TargetAdapter` + single-shot PI `BaseAttack`
4. Minimal static check: MCP config parser
5. Wire both sides into the unified Findings KG
6. End-to-end demo against a toy agent
