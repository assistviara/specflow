# PROJECT.md

# ============================================================
# Project Context
# ============================================================

プロジェクト名
SpecFlow

プロジェクトオーナー
Human

主言語
日本語（Japanese）

コミュニケーション方針

- 本プロジェクトの標準言語は日本語とする。
- 仕様書・レビュー・議論・設計書・成果物は、日本語で作成する。
- プログラミング言語、API名、ライブラリ名、クラス名などは、必要に応じて英語表記を用いてよい。
- AIは、ユーザーから明示的な指示がない限り、日本語で応答する。

対象読者

日本語話者

---

# ============================================================
# Project State
# ============================================================

現在バージョン
v0.1.0

ステータス
Application Layer Implementation Ready

現在フェーズ
Application Layer Phase 1 Implementation Ready

最終更新日
2026-08-30

現在の設計ベースライン

```text
d7df90d Merge pull request #32 from assistviara/developer
```

`main`へのMerge済みApplication Layer SpecificationおよびApplication Layer Implementation Planを、Application Layer実装開始前の正式な設計ベースラインとして扱う。

---

# ============================================================
# Project Vision
# ============================================================

目的

SpecFlowは、
「創造（Specification）」と
「実装（Implementation）」を分離し、

仕様を中心としたソフトウェア開発プロセスを実現することを目的とする。

---

# ============================================================
# Current Objective
# ============================================================

現在の目標

承認済みApplication Layer Implementation Planに基づき、Application Layer Phase 1 Implementationを開始する。

ただし、開始前にConstitution / Project Rules、最新のSession Context、Application Layer Specification、Application Layer Implementation Plan、Gitの現在状態を確認する。

---

# ============================================================
# Current Task
# ============================================================

現在のタスク

Application Layer Phase 1 Implementationの開始準備

Human の役割

- SpecificationおよびImplementation Planから一意に決定できない事項の判断
- Human Approvalを必要とする判断
- 実装開始・変更・承認に関する最終判断

AI の役割

- Constitution / Project Rules / Specification / Implementation Planの確認
- Phase 1のPurpose、Scope、Implementation Targets、Tests、Completion Conditionsの抽出
- 承認済みScope内でのTDDによる実装
- 実装中に不明点がある場合の停止とHuman Handoff

完了条件

- Phase 1のImplementation Targetsが実装されている
- Phase 1の対象Testsが成功している
- 既存TestがRegressionなく成功している
- Phase 1のCompletion Conditionsを満たしている
- Phase 2以降の責務へ侵入していない

成果物

- Application Layer Phase 1のSource Code
- Phase 1対象Test
- 実行結果
- 必要に応じたImplementation Evidence / Review入力

---

# ============================================================
# Project Progress
# ============================================================

完了

☑ Constitution Version 1.0

☑ Project Rules

☑ Principles

☑ Implementation Guidelines

☑ Architecture

☑ Document Loader

☑ Template Engine

☑ Prompt Builder

☑ Plan Prompt Generator

☑ AI Runner Foundation

☑ Application Layer Specification v0.2.0-draft

☑ Application Layer Implementation Plan v0.1.0-draft

☐ Application Layer Phase 1 Implementation

☐ Application Layer Phase 2 Implementation

☐ Application Layer Phase 3 Implementation

☐ Application Layer Phase 4 Implementation

☐ Application Layer Phase 5 Implementation

☐ Application Layer Phase 6 Implementation

☐ Application Layer Phase 7 Integration & MVP Completion

---

# ============================================================
# Next Tasks
# ============================================================

1. Constitution / Project Rules / SESSION_CONTEXT / Application Layer Specification / Application Layer Implementation Plan / Git状態を確認する。

2. Application Layer Implementation PlanのPhase 1を読み、Phase 1の実装単位と最初のTestを確定する。

3. Phase 1の最初の振る舞いからTDDで実装を開始する。

---

# ============================================================
# Active Documents
# ============================================================

| 文書 | Version | 状態 |
|------|---------|------|
| SpecFlow Constitution | v1.0 | Approved |
| Project Rules | - | Active |
| Principles | v2.0 | Active |
| Implementation Guidelines | v1.0 | Active |
| Application Layer Specification | v0.2.0-draft | Merged to main by PR #32 |
| Application Layer Implementation Plan | v0.1.0-draft | Merged to main by PR #32 |
| SESSION_CONTEXT | - | Active Handoff |

---

# ============================================================
# Current Decisions
# ============================================================

- Specificationを唯一の正本として扱う。
- 実装は承認済みSpecificationおよびImplementation Planに従う。
- Specificationから一意に決定できない事項をAIが独自に補完しない。
- Human Approvalを必要とする判断はHumanのみが行う。
- Application LayerはCoreを利用できるが、CoreからApplication Layerへの逆依存を導入しない。
- Current State、State Transition History、Human Approval Record、Implementation Evidence、Review Result、Git Operation Resultを分離する。
- Technical RetryはCorrectionではなく、Correction Countを増加させない。
- Correction後はTestを再実行し、新しいImplementation Evidenceを生成する。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同しない。
- Version 1 MVPのためにSpecificationで定義されていない新しいUseCase、Human Decision、Approval Rule、State、Review Result、Correction Rule等を追加しない。

---

# ============================================================
# Open Issues
# ============================================================

- Phase 1実装中にSpecificationまたはImplementation Planから一意に決定できない事項が見つかった場合は、推測で補完せずHumanへ確認する。

---

# ============================================================
# Risks
# ============================================================

- Phase 1実装時に、Phase 2以降の業務処理まで先行実装してしまうこと。
- Human ApprovalをAI、Application Layer、Core、Repository、Adapter等が生成または代替してしまうこと。
- Evidence、Review、Approval、Git Result、State Historyの責務を混同すること。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同すること。
- 正式Artifactを引き継ぎ要約の都合で書き換えてしまうこと。

---

# ============================================================
# Document Hierarchy
# ============================================================

Constitution

↓

Project Rules

↓

Principles

↓

Architecture

↓

Specification

↓

Implementation Plan

↓

Implementation

↓

Test

↓

Review

---

# ============================================================
# References
# ============================================================

最上位文書

`SpecFlow_Constitution_v1.0.md`

Project Rules

- `constitution/constitution.md`
- `constitution/principles.md`
- `constitution/implementation_guidelines.md`

現在状態

- `PROJECT.md`
- `SESSION_CONTEXT.md`
- `projects/specflow/docs/session_bootstrap.md`

正式Artifact

- `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
- `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`

---

# ============================================================
# Next Session
# ============================================================

次のAIは、以下の順序でプロジェクトを理解すること。

1. `SpecFlow_Constitution_v1.0.md`
2. `constitution/constitution.md`
3. `constitution/principles.md`
4. `constitution/implementation_guidelines.md`
5. `SESSION_CONTEXT.md`
6. `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
7. `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`
8. Gitの現在状態

---

# ============================================================
# Session Handover
# ============================================================

次のAIは、以下を前提として再開すること。

- Application Layer Specification v0.2.0-draftの設計作業は完了している。
- Application Layer Implementation Plan v0.1.0-draftの作成は完了している。
- Implementation PlanはPhase 1からPhase 7まで定義済みである。
- Phase 7の最終横断監査は完了している。
- Application Layer SpecificationおよびApplication Layer Implementation PlanはPull Request #32により`main`へMerge済みである。
- 次の主要作業はApplication Layer Phase 1 Implementationの開始である。
- 開始前にGit状態を確認し、Working Treeを把握すること。
- SpecificationまたはImplementation Planから一意に決定できない事項はHumanへ返すこと。

---

# ============================================================
# Notes
# ============================================================

この文書は現在状態の要約であり、Specification、Implementation Plan、Human Approval Recordの代替ではない。
