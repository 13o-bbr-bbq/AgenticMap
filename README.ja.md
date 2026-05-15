# AgenticMap

[English](README.md) | **日本語**

> AgenticMap は **Amazon Bedrock AgentCore** を対象とした OSS の AI セキュリティポスチャー管理（AI-SPM）ツールです。AgentCore の設定監査（静的）と動的レッドチーミングを組み合わせ、従来の静的解析ツールでは検出不能な複合リスクを検出します。また、日本国内の AI 関連規制に準拠しています。

AgenticMap は AIエージェントシステム（単体AIエージェント、マルチエージェントシステム）固有の脆弱性および設定不備にフォーカスし、従来の CSPM やAIレッドチーミングツールでは捉えられない領域を対象とします。

> ステータス: 初期スケルトン段階。最初の対象基盤は Amazon Bedrock AgentCore です。Azure AI Foundry や Vertex AI への拡張は AgentCore のカバレッジが充実するまでスコープ外とします。

## ポジショニング

- **OSS** — 2026 年時点の AI-SPM 市場は商用 SaaS（Microsoft Defender、Zenity、Wiz、Prisma Cloud、Orca、CrowdStrike、Zscaler）が主流。AgenticMap は OSS を維持し、監査可能性・エアギャップ運用・研究者による拡張性を確保します。
- **Dual-pipeline + 相互検証** — 多くの AI-SPM は静的設定監査のみ。AgenticMap はこれに能動的な動的レッドチーミングを組み合わせ、共通グラフ上で所見を連結することで、設定上の脆弱性を実際の攻撃成立で裏付けます。
- **日本市場特化** — 経済産業省 AI 事業者ガイドライン、AI 推進法、金融庁 AI ディスカッションペーパー、個人情報保護法など国内規制へのマッピングを内蔵。NIST AI RMF、ISO/IEC 42001、EU AI Act にも対応。
- **Bedrock AgentCore 専注** — 広く浅くではなく、AgentCore Runtime / Memory / Identity / Gateway / Policy / Browser / Code Interpreter / Observability（いずれも GA）と、レガシーの Bedrock Agents（Action Groups、Knowledge Bases、Guardrails、Prompt Override）を深く掘ります。Evaluations / Payments / Registry および preview 段階の機能は v0.1 スコープ外。

## 検出対象

検出対象は **設定不備（静的）** と **脆弱性（動的）** の 2 つに分かれます。

### 設定不備

AgentCore および Bedrock Agents（legacy）の機能ごとに、コンソール / API 上の設定を静的にチェックします。

| 対象機能 | 設定不備の例 |
|---|---|
| **AgentCore Runtime** | Inbound に OAuth / Cognito 未適用、Public endpoint で VPC endpoint 未経由 |
| **AgentCore Memory** | TTL 未設定、KMS CMK なし、PII 自動マスキング無効 |
| **AgentCore Gateway** | 認証方式が NONE（anonymous 許可）、Tool target が単一エージェントに過剰露出 |
| **AgentCore Identity** | workload identity の権限過剰、wildcard リソース許可 |
| **AgentCore Policy** | 書き込み系ツールに Policy 未適用、Cedar ルールが broad（条件なし `permit`）、Gateway 経由のバイパス経路 |
| **AgentCore Browser** | egress allowlist 未設定（任意 URL 取得可）→ 間接 PI の温床 |
| **AgentCore Code Interpreter** | 承認フロー欠如、sandbox の egress 無制限 |
| **AgentCore Observability** | CloudTrail データイベント OFF、ログが平文（KMS CMK なし）、Application Signals / X-Ray 未配線 |
| **Bedrock Agents: Guardrail** | Agent に Guardrail 未アタッチ、コンテンツフィルタ / PII フィルタ / プロンプト攻撃フィルタが OFF |
| **Bedrock Agents: Action Group** | `requireConfirmation` 未設定（HITL 欠如）、Lambda 実行ロールが `*` / AdministratorAccess |
| **Bedrock Agents: Knowledge Base** | S3 ソースに Public Access 許可、書き込み権の broad scope |
| **Bedrock Agents: Prompt Override** | デフォルトテンプレートの安全指示を削除・弱体化 |

### 脆弱性

動的レッドチーミングで実際に攻撃を仕掛け、設定だけでは判断できない実害の成立を確認します。

| カテゴリ | 例 |
|---|---|
| **直接プロンプトインジェクション** | エージェントエンドポイントへの PI で安全指示の上書き、システムプロンプト漏洩、jailbreak 成立 |
| **間接プロンプトインジェクション** | Knowledge Base 取り込み文書経由、AgentCore Browser 取得 Web 内容経由でコンテキストが汚染される |
| **ツール濫用** | 敵対的プロンプトにより Action Group / Gateway tool target が意図外スコープで呼び出される |
| **権限境界違反** | エージェントが workload identity / Lambda 実行ロールの本来スコープを超えて操作する |
| **マルチエージェント連鎖攻撃** | サブエージェント間の信頼境界漏洩、連携エージェント間の連鎖攻撃 |

## 動作原理

2 つのパイプラインを共通基盤上で走らせ、相互検証します。

```
                 ┌────────────────────────────────────────┐
                 │       Shared Substrate                  │
                 │   Findings KG / Episodic Memory         │
                 │   4-axis Verifier                       │
                 └──────────────┬─────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                                               ▼
 ┌──────────────────┐   cross-validate          ┌──────────────────┐
 │ External Probe   │ ←──────────────────────→  │ Internal Audit   │
 │ (動的・ブラック   │                          │ (静的・ホワイト  │
 │  ボックス)        │                          │  ボックス)        │
 │                  │                          │                  │
 │ - AgentCore      │                          │ - bedrock-agent  │
 │   InvokeAgent    │                          │   API 取り込み   │
 │ - PI / jailbreak │                          │ - ガードレール   │
 │ - KB 経由の      │                          │   検査           │
 │   間接 PI        │                          │ - HITL 検出       │
 │ - ツール濫用     │                          │ - IAM 権限検査    │
 │ - マルチエージ   │                          │ - Memory/KMS 検査 │
 │   ェント探索     │                          │ - ネットワーク検査│
 │                  │                          │ - Observability   │
 │                  │                          │   配線検査        │
 └──────────────────┘                          └──────────────────┘
```

### 4-axis Verifier（4 軸検証器）

すべての所見は判定（Verdict）になる前に以下の 4 軸で評価されます。

- **REAL** — 実際に有害な挙動が発生したか？
- **TRIGGERABLE** — 外部攻撃者から到達可能か？（静的解析の入力経路情報を活用）
- **IMPACTFUL** — 影響範囲はどこまで広がるか？（ツール、データ、下流システム）
- **GENERAL** — 単発の事象か、系統的なクラスの問題か？

### Findings KG と複合リスク

静的所見と動的所見を **同一のグラフ上に保存** し連結することで、複合リスクを検出可能です。例:

- 静的: *Action Group X に `requireConfirmation` が未設定*
- 動的: *Action Group X は Knowledge Base の取り込み内容経由の間接 PI で呼び出し可能*
- 連結 → **Critical** に昇格

この複合検出が静的解析専用 AI-SPM との本質的な差別化ポイントです。

## 類似ツールとの位置づけ

| ツール | 種別 | 静的 | 動的† | 相互検証 | OSS | JP 規制 | 主要対象 |
|---|---|---|---|---|---|---|---|
| Microsoft Defender (AI-SPM) | 商用 SaaS | ✓ | 一部（runtime 監視） | 一部 | ✗ | ✗ | Copilot Studio / Foundry / Bedrock / Vertex |
| Zenity AI-SPM | 商用 SaaS | ✓ | 一部（inline 強制） | ✓ | ✗ | ✗ | Foundry / AgentCore / Vertex |
| Wiz / Prisma / Orca / CrowdStrike / Zscaler | 商用 SaaS | ✓ | ✗ | ✗ | ✗ | ✗ | 主要クラウドの AI サービス |
| SplxAI Agentic Radar | **OSS** | ✓（ソース） | 一部 | ✗ | ✓ | ✗ | LangGraph / CrewAI 等のフレームワークソース |
| **AgenticMap** ‡ | **OSS** | ✓（API） | **✓（能動的 red-team）** | **✓** | **✓** | **✓** | **Bedrock AgentCore** |

† ここで「動的」は **能動的なブラックボックス探索**（細工した payload の送信）を指します。商用 AI-SPM は実行時の挙動監視は行いますが、対象に対して能動的にレッドチーミングは行いません。
‡ AgenticMap の行は v0.1 の設計意図を示します（[ステータス](#ステータス) を参照）。

## 準拠マッピング

所見は以下の規制・標準にタグ付けされます。

- **日本国内**
  - 経済産業省 AI 事業者ガイドライン
  - AI 推進法
  - 金融庁 AI ディスカッションペーパー
  - 個人情報保護法（プロファイリング・自動意思決定）
- **国際**
  - NIST AI RMF 1.0
  - ISO/IEC 42001
  - EU AI Act
  - MITRE ATLAS

## ディレクトリ構成

```
agenticmap/
├── core/                 # オーケストレータ、Verifier、Findings KG、データモデル
├── external/             # 動的レッドチーミング
│   └── adapters/         # BedrockAgentCoreAdapter (InvokeAgent) など
├── internal/             # 静的監査
│   └── bedrock/          # AgentCore + Bedrock Agents の設定監査（初期対象）
├── compliance/           # 国内 / 国際 規制マッピング（YAML）
└── datasets/
    └── signatures.yaml   # ATLAS タグ付き攻撃シグネチャ
tests/
└── fixtures/             # E2E デモ用の脆弱 AgentCore Terraform フィクスチャ
```

## クイックスタート

> まだ実行可能ではありません。将来の CLI のプレースホルダーです。

```bash
uv sync
uv run agenticmap audit-bedrock --region us-east-1 --agent-id <agent-id>
```

## ステータス

初期スケルトン段階。AgentCore 優先のロードマップ:

1. ✓ リポジトリスケルトン + `pyproject.toml`
2. ✓ コアデータモデル（`Finding`、`AgentNode`、`ToolEdge`、`Verdict`）
3. Internal Audit — AgentCore 静的チェック（Guardrail、Action Group `requireConfirmation`、IAM スコープ、Memory KMS/TTL、Gateway 認証、Observability 配線）
4. External Probe — `BedrockAgentCoreAdapter` + 単発の直接 PI シグネチャ
5. Compound Finding 配線 — 静的と動的の所見を KG 上で連結し 4-axis Verdict に反映
6. JP 規制マッピング — `compliance/jp_*.yaml` テーブル
7. CLI `audit-bedrock` サブコマンド + JSON / HTML レポート
8. 脆弱 AgentCore フィクスチャ（Terraform）を `tests/fixtures/` 配下に整備
9. v0.1 OSS リリース

## 設計系譜

- **[promptmap](https://github.com/8vana/promptmap)** — TargetAdapter / BaseAttack / Converter / Scorer の階層化、ATLAS タグ付き YAML 署名
- **[clearwing](https://github.com/Lazarus-AI/clearwing)** — Dual-pipeline トポロジ、共通基盤、4-axis Verifier、Ranker → Hunter → Verifier → Exploiter フロー
- 調査済みの関連ツール: garak、PyRIT、promptfoo、Giskard、DeepEval、HarmBench、AgentDojo、InjecAgent、AgentHarm、Rebuff、Vigil、ModelScan

## "AgenticMap" という命名の根拠

1. *Agentic* が「単発 LLM + ツール使用」から「フルマルチエージェントシステム」までを包摂する
2. *Map* が「攻撃面マップ」と「構造マップ」の二重出力を表現する
3. `promptmap` からの自然な系譜
4. マルチエージェントシステムはグラフ構造そのもの。グラフは "map" する対象

## ライセンス

未定（TBD）
