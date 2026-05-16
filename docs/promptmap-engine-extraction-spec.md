# PromptMap Engine Extraction — Refactor Spec

**Target repo**: [`8vana/promptmap`](https://github.com/8vana/promptmap)
**Requested by**: AgenticMap (separate OSS project, same owner)
**Spec date**: 2026-05-15
**Reader**: a coding agent working inside the PromptMap repo. You will NOT have access to AgenticMap's source. This spec is self-contained.

---

## 1. Background

### 1.1 What is AgenticMap

AgenticMap is an open-source **AI Security Posture Management (AI-SPM)** tool for Amazon Bedrock AgentCore, developed by the same author as PromptMap. It runs a dual-pipeline architecture:

- **Internal Audit (static)** — boto3-based configuration checks against AgentCore Runtime / Memory / Gateway / Identity / Policy / Browser / Code Interpreter / Observability and legacy Bedrock Agents.
- **External Probe (dynamic)** — black-box red-teaming against a live agent endpoint (direct prompt injection, indirect PI, tool abuse, multi-agent chained attacks).

AgenticMap's value proposition is the **cross-validation** of these two pipelines on a shared Findings Knowledge Graph — e.g. *"static finding: tool X has no HITL"* + *"dynamic finding: tool X is invokable via indirect PI"* compound-escalates to Critical.

### 1.2 Why PromptMap

PromptMap already implements ~70% of what AgenticMap's External Probe needs: a clean `TargetAdapter` / `BaseAttack` / `Scorer` / `Converter` layered architecture, 6 attack methods (Single PI, Crescendo, PAIR, TAP, Chunked Request, autonomous Agent), 24 stdlib converters, an LLM-as-Judge scorer, and ATLAS-tagged YAML signatures. AgenticMap's CLAUDE.md already names PromptMap as its design lineage source.

**Reimplementing this in AgenticMap is duplicate work.** The goal of this refactor is to make PromptMap's engine layer pip-installable so AgenticMap can depend on it.

### 1.3 The blocker

PromptMap today is structured as a **monolithic Textual TUI application**. There is no `pyproject.toml` declaring it as a library, no public API contract, and no headless entry point. AgenticMap cannot `pip install promptmap` and `from promptmap.engine.base_target import TargetAdapter` today.

The good news: the `engine/` subdirectory is *already* cleanly factored from `tui/` at the source level. The remaining work is primarily packaging and a small amount of polish.

---

## 2. Goal

After this refactor:

1. **`pip install promptmap`** works (from PyPI, or at minimum from the repo via `pip install git+...`).
2. **The engine subset is importable** without pulling Textual or any other TUI dependency:
   ```python
   from promptmap.engine.base_target import TargetAdapter
   from promptmap.engine.base_attack import BaseAttack
   from promptmap.engine.tool_call import ToolCall, ToolCallResponse
   from promptmap.engine.models import AttackResult
   from promptmap.engine.context import AttackContext
   from promptmap.attacks.single_pi_attack import SinglePIAttack
   from promptmap.attacks.multi_crescendo_attack import CrescendoAttack
   from promptmap.scorers.llm_judge import LLMJudgeScorer
   from promptmap.targets.bedrock_target import BedrockTargetAdapter
   # ...etc
   ```
3. **The existing TUI still works**: `promptmap` (or `python -m promptmap`) launches the Textual TUI as before.
4. **A headless mode exists** so CI / external tools / AgenticMap can drive PromptMap without a TUI.
5. **The interface contracts are documented and stable** — AgenticMap will pin against them.

---

## 3. Non-goals

Do **not** change any of the following in this refactor:

- The behavior of the TUI.
- The format of `datasets/signatures.yaml` (AgenticMap consumes this file directly).
- The signature of `TargetAdapter.send()` or `BaseAttack.run()` or `Scorer` — these are the public contracts AgenticMap relies on.
- The attack logic, converter logic, or scorer logic (no algorithmic changes).
- Adding new adapters. AgenticMap-specific adapters (`BedrockAgentRuntimeAdapter` for legacy Bedrock Agents, `BedrockAgentCoreRuntimeAdapter` for the new AgentCore Runtime) stay in AgenticMap for now and may be upstreamed in a later PR.

---

## 4. Required changes

### 4.1 Add `pyproject.toml` declaring `promptmap` as a package

Use `hatchling` for the build backend (matches AgenticMap's choice; lightweight). Single distribution named **`promptmap`**, with the TUI as an **optional extra**:

```toml
[project]
name = "promptmap"
version = "0.1.0"  # bump from current unversioned state
description = "Automated red-teaming framework for AI systems"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "TBD" }  # match what's currently in the repo

dependencies = [
    # Engine-only runtime deps. Audit current top-level imports to populate.
    # Likely: pyyaml, httpx (or aiohttp), boto3 (for BedrockTargetAdapter),
    # openai, anthropic, google-genai. KEEP these accurate — anything that
    # only the TUI needs goes in the [tui] extra below.
]

[project.optional-dependencies]
tui = [
    "textual>=0.50",  # match current pin
    # any other TUI-only deps
]
playwright = ["playwright>=1.40"]
all = ["promptmap[tui,playwright]"]

[project.scripts]
promptmap = "promptmap.cli:main"        # current TUI entrypoint (see §4.4)
promptmap-run = "promptmap.cli:run"     # NEW: headless entrypoint (see §4.5)

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["promptmap"]
```

**This requires moving the top-level layout** — see §4.2.

### 4.2 Make the source tree importable as a package

Current state (top-level files like `promptmap.py`, `proverb.py`, `utils.py`):

```
promptmap/                  ← git repo root
├── promptmap.py
├── proverb.py
├── utils.py
├── engine/
├── attacks/
├── converters/
├── datasets/
├── scorers/
├── targets/
├── memory/
├── config/
└── tui/
```

Target state (a proper Python package):

```
promptmap/                  ← git repo root (unchanged name)
├── pyproject.toml          ← NEW
├── README.md
├── promptmap/              ← NEW package root (move existing dirs here)
│   ├── __init__.py         ← NEW; re-exports public API (see §4.3)
│   ├── cli.py              ← NEW; main() + run() entry points (see §4.4, §4.5)
│   ├── engine/             ← moved
│   │   └── __init__.py
│   ├── attacks/            ← moved
│   ├── converters/         ← moved
│   ├── datasets/           ← moved (signatures.yaml ships with the package)
│   ├── scorers/            ← moved
│   ├── targets/            ← moved
│   ├── memory/             ← moved
│   ├── config/             ← moved (atlas_catalog.yaml etc. ship with the package)
│   └── tui/                ← moved
└── tests/                  ← if any exist
```

**Important**: the top-level `promptmap.py` / `proverb.py` / `utils.py` need to be folded into the new `promptmap/` package. Recommended placements:

- `promptmap.py` (top-level TUI entry) → fold into `promptmap/cli.py` as the `main()` function.
- `proverb.py` → if it's part of TUI, move to `promptmap/tui/proverb.py`; if it's a utility, `promptmap/utils.py`.
- `utils.py` → `promptmap/utils.py`.

**Update all internal imports** to use the new package path (`from promptmap.engine.base_target import ...` instead of `from engine.base_target import ...`). The current `bedrock_target.py` for example uses `from engine.base_target import TargetAdapter` — this becomes `from promptmap.engine.base_target import TargetAdapter`.

### 4.3 Define the public API in `promptmap/__init__.py`

Re-export the surface AgenticMap (and other downstream consumers) will rely on:

```python
"""PromptMap — automated AI red-teaming framework."""

from promptmap.engine.base_target import TargetAdapter
from promptmap.engine.base_attack import BaseAttack
from promptmap.engine.context import AttackContext
from promptmap.engine.models import AttackResult
from promptmap.engine.tool_call import (
    ToolCall, ToolCallFunction, ToolCallMessage,
    ToolCallChoice, ToolCallResponse,
)

__all__ = [
    "TargetAdapter", "BaseAttack", "AttackContext", "AttackResult",
    "ToolCall", "ToolCallFunction", "ToolCallMessage",
    "ToolCallChoice", "ToolCallResponse",
]

__version__ = "0.1.0"
```

This means consumers can `from promptmap import TargetAdapter` for convenience. Deeper imports (`promptmap.attacks.single_pi_attack`, `promptmap.targets.bedrock_target`, etc.) remain available.

### 4.4 Keep the TUI entry point working

The current `promptmap.py` top-level script that launches the TUI should be preserved as the `promptmap` console script. Move its body to `promptmap/cli.py::main()`:

```python
# promptmap/cli.py
def main() -> None:
    """Launch the Textual TUI (existing behavior)."""
    try:
        from promptmap.tui.app import PromptMapApp  # or whatever the current entry is
    except ImportError as e:
        raise SystemExit(
            "TUI dependencies not installed. Run: pip install 'promptmap[tui]'"
        ) from e
    PromptMapApp().run()
```

The lazy import + helpful error message lets engine-only installs avoid pulling Textual.

### 4.5 Add a headless run entry point (NEW capability)

Add `promptmap/cli.py::run()` exposed as `promptmap-run`. It must:

- Take a **target configuration** (JSON or YAML file describing which `TargetAdapter` subclass to instantiate and with what arguments).
- Take an **attack name** (one of: `single_pi`, `crescendo`, `pair`, `tap`, `chunked_request`, `agent`).
- Take a **signature identifier or objective string**.
- Optionally take a **scorer configuration** (model, API key env var).
- Optionally take a **converter chain** (comma-separated).
- Run the attack, **emit one JSON line per `AttackResult` to stdout**, and exit:
  - `exit 0` if no signature scored ≥0.7 (no successful attacks)
  - `exit 1` if at least one ≥0.7 (used by CI to fail builds)

Suggested CLI:

```bash
promptmap-run \
    --target-config target.yaml \
    --attack single_pi \
    --signature simple-instruction-attack \
    --scorer-model gpt-4 \
    --converters base64,rot13 \
    --language ja
```

`target.yaml` example:

```yaml
adapter: BedrockTargetAdapter
init:
  model: anthropic.claude-3-5-sonnet-20240620-v1:0
  region: us-east-1
```

JSONL output line (per attack result):

```json
{"attack": "single_pi", "signature_id": "simple-instruction-attack", "score": 8, "success": true, "response": "...", "tool_calls": [], "timestamp": "2026-05-15T..."}
```

If the existing `engine/conversation_log.py` or `~/.promptmap/runs/*.jsonl` already produces a comparable format, **reuse that schema** — do not invent a new one. The goal is for downstream consumers to parse the same shape PromptMap already writes.

### 4.6 Audit and enforce "engine has no TUI imports"

Verify (and fix if needed) that nothing under `promptmap/engine/`, `promptmap/attacks/`, `promptmap/converters/`, `promptmap/scorers/`, `promptmap/targets/`, `promptmap/datasets/`, `promptmap/memory/`, `promptmap/config/` imports from `promptmap.tui` or `textual` or any TUI-only dep.

Verification command (run in repo root after moving):

```bash
# Should produce no output:
grep -RIl --include='*.py' -E '^\s*(from|import)\s+(textual|promptmap\.tui)' \
    promptmap/engine promptmap/attacks promptmap/converters \
    promptmap/scorers promptmap/targets promptmap/memory promptmap/config
```

If matches are found, refactor to remove the upward dependency (move the offending logic into `tui/`, or invert the dependency via dependency injection).

For long-term enforcement, add `import-linter` to dev dependencies with a contract preventing engine→TUI imports, but this is **optional** — a one-time audit is acceptable for this PR.

### 4.7 Document the public interface contracts

In `promptmap/engine/base_target.py` and `promptmap/engine/base_attack.py`, add a **module-level docstring** noting:

> This is part of the PromptMap public API. Downstream consumers (e.g. AgenticMap) depend on the signatures below; changing them is a breaking change and requires a major version bump.

Same for `AttackContext`, `AttackResult`, `ToolCallResponse`.

### 4.8 (Optional but recommended) Make `AttackResult` a Pydantic model

If `AttackResult` is currently a dataclass with un-typed `Any` fields, consider promoting it to a Pydantic v2 model so downstream consumers get validation and JSON serialization for free. This is **not blocking** — only do it if it does not delay the rest of the refactor.

---

## 5. Acceptance criteria

A reviewer (or automated CI) must be able to confirm all of the following:

1. **Build**: `python -m build` produces a wheel without errors.
2. **Engine install**: in a clean venv, `pip install <wheel>` (no extras) succeeds and:
   ```python
   from promptmap.engine.base_target import TargetAdapter
   from promptmap.attacks.single_pi_attack import SinglePIAttack
   from promptmap.scorers.llm_judge import LLMJudgeScorer
   from promptmap.targets.bedrock_target import BedrockTargetAdapter
   ```
   all succeed.
3. **TUI install**: `pip install <wheel>[tui]` succeeds and `promptmap` launches the Textual TUI as before.
4. **Engine has no TUI imports**: the grep in §4.6 produces no output.
5. **Headless mode works**: `promptmap-run --target-config <fixture> --attack single_pi --signature <id>` exits cleanly and produces at least one JSON line on stdout.
6. **TUI behavior unchanged**: smoke-test the existing TUI flows (Manual Scan wizard, Agent Scan, Results screen) — no regressions.
7. **Internal imports updated**: no remaining `from engine.X import Y` style — all use `from promptmap.engine.X import Y`.

---

## 6. Suggested PR sequence

To keep diffs reviewable, split into 3 PRs:

1. **PR 1 — Restructure**: move directories into `promptmap/` package, update internal imports, add minimal `pyproject.toml`, verify TUI still launches. No new features.
2. **PR 2 — Headless mode**: add `promptmap/cli.py::run()` + `promptmap-run` console script + tests.
3. **PR 3 — Polish**: public API re-exports in `promptmap/__init__.py`, docstrings on contract classes, optional `AttackResult` Pydantic migration, optional `import-linter` contract.

This sequence lets you ship PR 1 early (unblocking AgenticMap) while PR 2 / PR 3 land independently.

---

## 7. Reference: how AgenticMap will use PromptMap after this refactor

For context — this is **not** code you need to write; it just illustrates what AgenticMap will do once the refactor lands.

```python
# In agenticmap/external/adapters/bedrock_agentcore.py
from promptmap.engine.base_target import TargetAdapter  # ← the import that unblocks us

class BedrockAgentCoreRuntimeAdapter(TargetAdapter):
    """Invokes a Bedrock AgentCore agent via bedrock-agentcore:invoke_agent_runtime."""
    # ...implementation...


# In agenticmap/external/runner.py
from promptmap.engine.context import AttackContext
from promptmap.attacks.single_pi_attack import SinglePIAttack
from promptmap.attacks.multi_crescendo_attack import CrescendoAttack
from promptmap.scorers.llm_judge import LLMJudgeScorer

async def run_dynamic_probes(target: TargetAdapter, kg: "FindingsKG") -> None:
    ctx = AttackContext(target=target, scorer=LLMJudgeScorer(...), ...)
    for attack_cls in (SinglePIAttack, CrescendoAttack):
        attack = attack_cls()
        result = await attack.run(ctx, objective="leak the system prompt")
        finding = _attack_result_to_finding(result)  # AgenticMap-side mapping
        kg.add_finding(finding)
```

AgenticMap pins `promptmap = "~=0.1"` (or whatever your initial version is) and treats every public symbol listed in §4.3 as a stability contract.

---

## 8. Out-of-scope items that AgenticMap will handle on its own side

So you know what is **NOT** being asked of you:

- AgentCore-specific adapters (`BedrockAgentRuntimeAdapter`, `BedrockAgentCoreRuntimeAdapter`) — live in AgenticMap.
- Indirect-PI payload injection (Knowledge Base S3 write, Browser web seeding) — AgenticMap.
- Tool-abuse structured detection (parsing Action Group invocations from the response trace) — AgenticMap.
- Conversion of `AttackResult` → AgenticMap `Finding` object — AgenticMap.
- 4-axis Verdict assembly (REAL from scorer, TRIGGERABLE / IMPACTFUL / GENERAL from static context) — AgenticMap.

If any of the above would benefit PromptMap users in general, they can be upstreamed in a separate PR after this one ships.

---

## 9. Questions to flag back if you hit ambiguity

If during implementation you encounter any of the following, **pause and ask** rather than guessing:

- The current `BedrockTargetAdapter` already imports `from engine.base_target import TargetAdapter`. Confirm that's the only style of internal import being used (vs absolute paths or sys.path manipulation).
- If `proverb.py` or `utils.py` contain a mix of TUI and engine code, splitting them may require judgment calls — surface them.
- If `signatures.yaml` lookup is currently done with a hard-coded path relative to the repo root, that needs to become a package-relative path (`importlib.resources` or `Path(__file__).parent`).
- Whether to keep `~/.promptmap/runs/<timestamp>.jsonl` as the run log location, or switch to stdout-only for `promptmap-run`. Recommended: **both** — `promptmap-run` writes JSONL to stdout AND appends to the existing file location, so existing users' workflows don't break.

---

## 10. Done definition

When all of §5's acceptance criteria pass on a green CI run, this refactor is complete. Tag the result as `v0.1.0` and AgenticMap will pin against it.
