# AgenticMap

**English** | [日本語](README.ja.md)

> AgenticMap maps both runtime behaviors and structural configurations of agentic AI systems — combining dynamic red-teaming with static architecture audit, then cross-validating findings to surface compound risks invisible to either approach alone.

AgenticMap is a security audit tool for **AI / agentic systems** — LLM chatbots, single-agent tool users, and multi-agent systems. It targets the class of vulnerabilities and governance gaps that traditional application security tools miss.

> Status: early scaffolding. Interfaces and CLI are still landing — expect breaking changes.

## What it detects

| Category | Examples |
|---|---|
| **Governance gaps** | Missing guardrails, system prompts without security rules, absent HITL checkpoints, missing steering policy, observability wiring gaps |
| **Adversarial inputs** | Direct prompt injection, indirect prompt injection (via tool output, retrieved docs, web content) |
| **Tool surface** | Tool abuse, over-privileged tools, privilege-boundary violations |
| **Multi-agent** | Chained attacks across agents, trust-boundary leakage between subagents |

## How it works

AgenticMap runs **two pipelines** over a **shared substrate** and cross-validates between them:

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
 │                  │                           │                  │
 │ - TargetAdapter  │                           │ - Agent graph    │
 │ - BaseAttack     │                           │   parser         │
 │ - Converter      │                           │ - Tool/MCP audit │
 │ - Indirect PI    │                           │ - Guardrail chk  │
 │ - Tool-call hook │                           │ - HITL detector  │
 │ - Multi-agent    │                           │ - Observability  │
 │   probes         │                           │   wiring chk     │
 │                  │                           │ - Steering chk   │
 └──────────────────┘                           └──────────────────┘
```

### 4-axis Verifier

Every finding is scored along four axes before it becomes a verdict:

- **REAL** — did harmful behavior actually occur?
- **TRIGGERABLE** — is it reachable from an external attacker? (uses static input-path information)
- **IMPACTFUL** — what is the blast radius across tools, data, and downstream systems?
- **GENERAL** — is this one-off, or a systemic class of issue?

### Findings KG

Static and dynamic findings are stored on a **single graph**, so they can compound. For example:

- Static finding: *tool X has no HITL configured*
- Dynamic finding: *tool X is invokable via indirect prompt injection from retrieved web content*
- Linked → escalated to **Critical**.

This compound-risk detection is the core differentiation from static-only tools like SplxAI's Agentic Radar.

## Repository layout

```
agenticmap/
├── core/         # orchestrator, Verifier, Findings KG, data models
├── external/     # dynamic red-teaming (PI / jailbreak / indirect injection / tool abuse / multi-agent)
├── internal/     # static audit (graph parser / tool inventory / guardrail / HITL / observability / steering)
├── adapters/     # HTTP / MCP / LangGraph / AutoGen / CrewAI ingest
└── datasets/
    └── signatures.yaml  # ATLAS-tagged attack signatures
```

## Quick start

> Not yet runnable — placeholder for the upcoming CLI.

```bash
uv sync
uv run agenticmap audit --target http://localhost:8000/chat
```

## Design lineage

AgenticMap draws design patterns from prior work:

- **[promptmap](https://github.com/8vana/promptmap)** — TargetAdapter / BaseAttack / Converter / Scorer layering and ATLAS-tagged YAML signatures. AgenticMap extends this beyond single-shot LLMs into multi-agent and tool-call interception.
- **[clearwing](https://github.com/Lazarus-AI/clearwing)** — dual-pipeline topology, shared substrate, 4-axis Verifier, and Ranker → Hunter → Verifier → Exploiter flow. The domain differs (clearwing uses AI to attack legacy systems); AgenticMap reuses the patterns.
- Surveyed: garak, PyRIT, promptfoo, Giskard, DeepEval, HarmBench, AgentDojo, InjecAgent, AgentHarm, Rebuff, Vigil, ModelScan.
- Closest competitor: **SplxAI Agentic Radar** (static-only). AgenticMap differentiates with the dynamic side and cross-validation.

## Why "AgenticMap"

1. *Agentic* covers single-shot LLM + tools through full multi-agent systems.
2. *Map* expresses the dual output: an **attack-surface map** and a **structural map**.
3. Natural lineage from `promptmap`.
4. Multi-agent systems are graphs — and you map graphs.

## License

TBD.
