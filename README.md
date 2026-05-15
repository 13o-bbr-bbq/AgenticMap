# AgenticMap

**English** | [日本語](README.ja.md)

> AgenticMap is an open-source AI Security Posture Management (AI-SPM) tool for **Amazon Bedrock AgentCore**. It combines static configuration audit with dynamic red-teaming on a shared findings graph and cross-validates the two to surface compound risks that static-only AI-SPM cannot detect — with built-in mapping to Japanese AI regulations.

AgenticMap targets the class of vulnerabilities and governance gaps that traditional CSPM and application-security tools miss in AI / agentic systems.

> Status: early scaffolding. First target platform is Amazon Bedrock AgentCore. Other platforms (Azure AI Foundry, Vertex AI) are out of scope until AgentCore coverage is real.

## Positioning

- **OSS** — the AI-SPM space in 2026 is dominated by commercial SaaS (Microsoft Defender, Zenity, Wiz, Prisma Cloud, Orca, CrowdStrike, Zscaler). AgenticMap stays open-source so it is auditable, air-gappable, and extensible by researchers.
- **Dual-pipeline + cross-validation** — most AI-SPM is static-config-only. AgenticMap adds active dynamic red-teaming and links findings on a shared graph, so a configuration weakness can be verified by an actual exploit attempt.
- **Japan-market focus** — built-in mapping to Japanese AI regulations (METI AI 事業者ガイドライン, AI 推進法, 金融庁 AI ディスカッションペーパー, 個人情報保護法) alongside NIST AI RMF, ISO/IEC 42001, EU AI Act.
- **Bedrock AgentCore first** — depth over breadth. AgentCore Runtime / Memory / Identity / Gateway / Policy / Browser / Code Interpreter / Observability (all GA), plus legacy Bedrock Agents (Action Groups, Knowledge Bases, Guardrails, Prompt Override). Evaluations / Payments / Registry and any preview-stage features are out of scope for v0.1.

## What it detects

Two top-level categories: **misconfigurations (static)** and **vulnerabilities (dynamic)**.

### Misconfigurations

Static checks against AgentCore and legacy Bedrock Agents configuration, organized by feature name.

| Target feature | Example misconfigurations |
|---|---|
| **AgentCore Runtime** | Inbound auth not configured (OAuth / Cognito missing), public endpoint without VPC endpoint |
| **AgentCore Memory** | No TTL, customer-managed KMS key absent, PII auto-masking disabled |
| **AgentCore Gateway** | Authorization type set to NONE (anonymous), tool targets sprawling across one agent |
| **AgentCore Identity** | Workload identity over-privileged, wildcard resources permitted |
| **AgentCore Policy** | No Policy applied to write-capable tools, broad Cedar `permit` rules without conditions, bypass paths around Gateway |
| **AgentCore Browser** | No egress allowlist (arbitrary URL fetches) — direct path for indirect prompt injection |
| **AgentCore Code Interpreter** | No approval flow, sandbox egress unrestricted |
| **AgentCore Observability** | CloudTrail data events off, log groups unencrypted (no customer KMS), Application Signals / X-Ray not wired |
| **Bedrock Agents: Guardrail** | Agent without a Guardrail, content / PII / prompt-attack filters off |
| **Bedrock Agents: Action Group** | `requireConfirmation` unset (no HITL), Lambda execution role with `*` or `AdministratorAccess` |
| **Bedrock Agents: Knowledge Base** | S3 source allows public access, broad write scope on the ingestion bucket |
| **Bedrock Agents: Prompt Override** | Safety-relevant default instructions removed or weakened |

### Vulnerabilities

Dynamic red-teaming probes that confirm whether a configuration weakness translates into an actual exploit.

| Category | Examples |
|---|---|
| **Direct prompt injection** | Override of safety instructions on the agent endpoint, system-prompt leakage, jailbreak success |
| **Indirect prompt injection** | Context contamination via retrieved Knowledge Base documents or AgentCore Browser-fetched web content |
| **Tool abuse** | Adversarial prompt invokes an Action Group / Gateway tool target outside its intended scope |
| **Privilege boundary violation** | Agent operates beyond the intended scope of its workload identity or Lambda execution role |
| **Multi-agent chained attacks** | Trust-boundary leakage between agent and sub-agents, chained exploits across collaborating agents |

## How it works

Two pipelines run over a shared substrate and cross-validate each other:

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
 │ - AgentCore      │                           │ - bedrock-agent  │
 │   InvokeAgent    │                           │   API ingest     │
 │ - PI / jailbreak │                           │ - Guardrail chk  │
 │ - Indirect PI    │                           │ - HITL detector  │
 │   via KB content │                           │ - IAM scope chk  │
 │ - Tool abuse     │                           │ - Memory/KMS chk │
 │ - Multi-agent    │                           │ - Network chk    │
 │   probes         │                           │ - Observability  │
 │                  │                           │   wiring chk     │
 └──────────────────┘                           └──────────────────┘
```

### 4-axis Verifier

Every finding is scored on four axes before becoming a verdict:

- **REAL** — did the harmful behavior actually occur?
- **TRIGGERABLE** — is it reachable from an external attacker? (uses static input-path information)
- **IMPACTFUL** — blast radius across tools, data, and downstream systems
- **GENERAL** — one-off vs systemic class of issue

### Findings KG and compound risks

Static and dynamic findings live on one graph and can compound. Example:

- Static: *Action Group X has no `requireConfirmation`*
- Dynamic: *Action Group X is invokable via indirect PI from Knowledge Base content*
- Linked → escalated to **Critical**.

This compound detection is the core differentiation from static-only AI-SPM.

## Related tools and differentiation

| Tool | Type | Static | Dynamic† | Cross-validate | OSS | JP regulation | First-class target |
|---|---|---|---|---|---|---|---|
| Microsoft Defender (AI-SPM) | Commercial SaaS | ✓ | partial (runtime monitor) | partial | ✗ | ✗ | Copilot Studio / Foundry / Bedrock / Vertex |
| Zenity AI-SPM | Commercial SaaS | ✓ | partial (inline enforce) | ✓ | ✗ | ✗ | Foundry / AgentCore / Vertex |
| Wiz / Prisma / Orca / CrowdStrike / Zscaler | Commercial SaaS | ✓ | ✗ | ✗ | ✗ | ✗ | major-cloud AI services |
| SplxAI Agentic Radar | **OSS** | ✓ (source code) | partial | ✗ | ✓ | ✗ | LangGraph / CrewAI / framework source |
| **AgenticMap** ‡ | **OSS** | ✓ (API) | **✓ (active red-team)** | **✓** | **✓** | **✓** | **Bedrock AgentCore** |

† "Dynamic" here means **active black-box probing** (sending crafted payloads). Commercial AI-SPM tools observe runtime behavior but do not actively red-team the target.
‡ The AgenticMap row reflects design intent for v0.1 — see [Status](#status).

## Compliance mapping

Findings are tagged against:

- **Japan**
  - 経済産業省 AI 事業者ガイドライン
  - AI 推進法
  - 金融庁 AI ディスカッションペーパー
  - 個人情報保護法（プロファイリング・自動意思決定）
- **International**
  - NIST AI RMF 1.0
  - ISO/IEC 42001
  - EU AI Act
  - MITRE ATLAS

## Repository layout

```
agenticmap/
├── core/                 # orchestrator, Verifier, Findings KG, data models
├── external/             # dynamic red-teaming
│   └── adapters/         # BedrockAgentCoreAdapter (InvokeAgent), ...
├── internal/             # static audit
│   └── bedrock/          # AgentCore + legacy Bedrock Agents config audit
├── compliance/           # JP / international regulation mappings (YAML)
└── datasets/
    └── signatures.yaml   # ATLAS-tagged attack signatures
tests/
└── fixtures/             # vulnerable AgentCore Terraform fixtures for E2E demo
```

## Quick start

> Not yet runnable — placeholder for the upcoming CLI.

```bash
uv sync
uv run agenticmap audit-bedrock --region us-east-1 --agent-id <agent-id>
```

## Status

Early scaffolding. AgentCore-first roadmap:

1. ✓ Repo skeleton + `pyproject.toml`
2. ✓ Core data models (`Finding`, `AgentNode`, `ToolEdge`, `Verdict`)
3. Internal audit — AgentCore static checks (Guardrail, Action Group `requireConfirmation`, IAM scope, Memory KMS/TTL, Gateway auth, Observability wiring)
4. External probe — `BedrockAgentCoreAdapter` + single-shot direct PI signature
5. Compound Finding wiring — link static + dynamic findings on the KG via the 4-axis Verdict
6. JP regulation mapping — `compliance/jp_*.yaml` tables
7. CLI `audit-bedrock` subcommand with JSON / HTML report
8. Vulnerable AgentCore fixture (Terraform) under `tests/fixtures/`
9. v0.1 OSS release

## Design lineage

- **[promptmap](https://github.com/8vana/promptmap)** — TargetAdapter / BaseAttack / Converter / Scorer layering and ATLAS-tagged YAML signatures.
- **[clearwing](https://github.com/Lazarus-AI/clearwing)** — dual-pipeline topology, shared substrate, 4-axis Verifier, Ranker → Hunter → Verifier → Exploiter flow.
- Surveyed: garak, PyRIT, promptfoo, Giskard, DeepEval, HarmBench, AgentDojo, InjecAgent, AgentHarm, Rebuff, Vigil, ModelScan.

## Why "AgenticMap"

1. *Agentic* covers single-shot LLM + tools through full multi-agent systems.
2. *Map* expresses the dual output: an **attack-surface map** and a **structural map**.
3. Natural lineage from `promptmap`.
4. Multi-agent systems are graphs — and you map graphs.

## License

TBD.
