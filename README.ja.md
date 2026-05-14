# AgenticMap

[English](README.md) | **日本語**

> AgenticMap は、エージェント型 AI システムの「実行時の振る舞い」と「構造的な設定」の両方をマッピングします。動的レッドチーミングと静的アーキテクチャ監査を組み合わせ、両者の所見を相互検証することで、片方だけでは見えない複合的なリスクを浮かび上がらせます。

AgenticMap は **AI / エージェント型システム**（LLM チャットボット、ツールを使う単体エージェント、マルチエージェントシステム）向けのセキュリティ監査ツールです。従来のアプリケーションセキュリティツールでは捉えられない、AI 特有の脆弱性および統制不備にフォーカスしています。

> ステータス: 初期スケルトン段階。インターフェースおよび CLI は固まっていないため、破壊的変更が発生する可能性があります。

## 検出対象

| カテゴリ | 例 |
|---|---|
| **統制不備（ガバナンスギャップ）** | ガードレール未実装、システムプロンプトにセキュリティルールが組み込まれていない、HITL チェックポイント欠如、Steering ポリシー未実装、Observability 配線の欠如 |
| **敵対的入力** | 直接プロンプトインジェクション、間接プロンプトインジェクション（ツール出力・検索結果・Web コンテンツ経由） |
| **ツール表面** | ツール濫用、過剰権限ツール、権限境界違反 |
| **マルチエージェント** | エージェント間連鎖攻撃、サブエージェント間の信頼境界漏洩 |

## 動作原理

AgenticMap は **2 つのパイプライン** を **共通基盤（Shared Substrate）** 上で動作させ、相互検証します。

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
 │ - TargetAdapter  │                          │ - エージェント   │
 │ - BaseAttack     │                          │   グラフ解析     │
 │ - Converter      │                          │ - ツール/MCP監査 │
 │ - 間接 PI         │                          │ - ガードレール  │
 │ - ツール呼出フック │                          │   検査          │
 │ - マルチエージェ  │                          │ - HITL 検出      │
 │   ント探索        │                          │ - Observability  │
 │                  │                          │   配線検査       │
 │                  │                          │ - Steering 検査  │
 └──────────────────┘                          └──────────────────┘
```

### 4-axis Verifier（4 軸検証器）

すべての所見は、判定（Verdict）になる前に以下の 4 軸で評価されます。

- **REAL** — 実際に有害な挙動が発生したか？
- **TRIGGERABLE** — 外部攻撃者から到達可能か？（静的解析の入力経路情報を活用）
- **IMPACTFUL** — 影響範囲はどこまで広がるか？（ツール、データ、下流システム）
- **GENERAL** — 単発の事象か、系統的なクラスの問題か？

### Findings KG（所見ナレッジグラフ）

静的所見と動的所見を **同一のグラフ上に保存** することで、両者を連結し複合化できます。例:

- 静的所見: *ツール X に HITL が設定されていない*
- 動的所見: *ツール X は検索された Web コンテンツ経由の間接プロンプトインジェクションで呼び出し可能*
- 連結 → **Critical** に昇格

この複合リスク検出が、SplxAI Agentic Radar などの「静的解析専用」ツールとの本質的な差別化ポイントです。

## ディレクトリ構成

```
agenticmap/
├── core/         # オーケストレータ、Verifier、Findings KG、データモデル
├── external/     # 動的レッドチーミング（PI / jailbreak / 間接インジェクション / ツール濫用 / マルチエージェント）
├── internal/     # 静的監査（グラフ解析 / ツール棚卸 / ガードレール・HITL・Observability・Steering 検査）
├── adapters/     # HTTP / MCP / LangGraph / AutoGen / CrewAI トレース取込
└── datasets/
    └── signatures.yaml  # ATLAS タグ付き攻撃署名
```

## クイックスタート

> まだ実行可能ではありません。将来の CLI のプレースホルダーです。

```bash
uv sync
uv run agenticmap audit --target http://localhost:8000/chat
```

## 設計系譜

AgenticMap は以下の先行ツールから設計パターンを継承しています。

- **[promptmap](https://github.com/8vana/promptmap)** — TargetAdapter / BaseAttack / Converter / Scorer の階層化と、ATLAS タグ付き YAML 署名。AgenticMap はこれを単発 LLM の範囲を超え、マルチエージェントおよびツール呼び出し介入まで拡張します。
- **[clearwing](https://github.com/Lazarus-AI/clearwing)** — Dual-pipeline トポロジ、共通基盤、4-axis Verifier、Ranker → Hunter → Verifier → Exploiter フロー。clearwing のドメイン（AI で従来システムを攻撃）とは異なりますが、AgenticMap はその **パターン** を再利用しています。
- 調査済みの関連ツール: garak、PyRIT、promptfoo、Giskard、DeepEval、HarmBench、AgentDojo、InjecAgent、AgentHarm、Rebuff、Vigil、ModelScan
- 最も近い既存ツール: **SplxAI Agentic Radar**（静的解析のみ）。AgenticMap は動的側と相互検証の追加で差別化します。

## "AgenticMap" という命名の根拠

1. *Agentic* が「単発 LLM + ツール使用」から「フルマルチエージェントシステム」までを包摂する
2. *Map* が「攻撃面マップ」と「構造マップ」の二重出力を表現する
3. `promptmap` からの自然な系譜
4. マルチエージェントシステムはグラフ構造そのもの。グラフは "map" する対象

## ライセンス

未定（TBD）
