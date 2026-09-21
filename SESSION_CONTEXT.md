# SESSION_CONTEXT.md

## Purpose

この文書は、ChatGPT / Codex セッション切替時の引き継ぎ文書である。

新しいセッションでは、いきなり設計・実装を開始せず、まず以下を確認して現在地点を復元すること。

1. `SpecFlow_Constitution_v1.0.md`
2. `constitution/constitution.md`
3. `constitution/principles.md`
4. `constitution/implementation_guidelines.md`
5. `SESSION_CONTEXT.md`
6. `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
7. `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`
8. Gitの現在状態

本書は現在地点の要約であり、新しいSpecification、Implementation Plan、設計決定、Human Approvalを追加する場所ではない。

---

# Current State

## Repository Baseline

現在のリポジトリでは、`main`、`developer`、`origin/main`、`origin/developer` が同一Commitを指している。

確認済みCommit:

```text
7f37fad Merge pull request #37 from assistviara/developer
```

Pull Request #37により、Application Layer Phase 3のCodex実行traceから、Phase 4のTest State取得までの経路は`main`へMerge済みである。

`main`、`developer`、`origin/main`、`origin/developer`は、上記Commitを指していることを確認済みである。

正式Artifact本文のStatus表記は、この引き継ぎ更新では変更していない。

---

## Completed Work

完了済み:

- Constitution Version 1.0
- Project Rulesとしての`constitution/constitution.md`
- Principles
- Implementation Guidelines
- Architecture
- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator
- AI Runner Foundation
- AI Runner Foundation Specification / Implementation Plan / Decision / Implementation / Review
- Application Layer Specification v0.2.0-draftの設計作業
- Application Layer Specification v0.2.0-draftの横断監査
- Application Layer Implementation Plan v0.1.0-draftの作成
- Application Layer Implementation PlanのPhase 1からPhase 7までの定義
- Phase 7のPurpose、Scope、Implementation Targets 1-8、Tests 1-8、Completion Conditions 1-8の最終横断監査
- Technical Retry、Correction、Human Approval、Evidence、Review、Final Approval、Merge、completedの責務境界の横断確認
- Pull Request #32によるApplication Layer設計ベースラインの`main`へのMerge
- Application Layer Phase 1の実装と`main`へのMerge
- Application Layer Phase 2の実装と`main`へのMerge
- Application Layer Phase 3のImplementation実行基盤
- Application Layer Phase 4のImplementation Evidence収集基盤
- UC-08 `Collect Implementation Evidence`のApplication Layerオーケストレーション
- Git Repository State Provider
- Implementation Evidenceの構造、比較、Serialization、create-only永続化
- Test Execution Recordのモデル、Serialization、create-only永続化
- JsonTestStateProviderによるcommand traceの存在確認およびSHA-256検証
- `codex exec --json`によるJSONL execution traceの取得・解析
- Codex最終メッセージとcommand execution eventの分離
- Initial、Target、Fullを明示するTest phase wrapper
- normalized command traceの機密情報redact、保存、SHA-256算出
- Test Execution Record構築・保存のPhase 3への接続
- Implementation IDのPhase 3からPhase 4への一貫した引き継ぎ
- trace取得不能、保存失敗、取得不能Evidence、No-TDD理由不足の安全な記録・停止
- Codex PromptへのTest phase wrapper契約追加と生成Prompt検証
- Phase 3からPhase 4 TestStateまでのE2Eテスト
- Pull Request #36によるPhase 4 Implementation Evidence収集基盤の`main`へのMerge
- Pull Request #37によるPhase 3からPhase 4へのTest Evidence経路の`main`へのMerge

最新のFull Test Suite確認結果:

```text
425 passed
```

---

# Formal Artifacts

Application Layer実装開始時の基準文書は以下である。

- Specification: `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
- Implementation Plan: `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`

これらは正式Artifactとして扱い、引き継ぎ要約の都合で本文を書き換えてはならない。

Implementation中にSpecificationまたはImplementation Planから一意に決められない事項を発見した場合、AIが補完せず、停止してHumanへ確認する。

---

# Important Design Principles

## 1. Specification First

- 実装はSpecificationおよび承認済みImplementation Planに従う。
- Specificationから一意に決められない事項をAIが独自に補完しない。

## 2. Human Approval Boundary

- Human Approvalを必要とする判断はHumanのみが行う。
- AI、Application Layer、Core、Repository、Adapter等がHuman Decisionを生成、推測、補完、代替しない。

## 3. Dependency Direction

- Application LayerはCoreを利用できる。
- CoreからApplication Layerへの逆依存を導入しない。
- Infrastructureの具体実装へApplication/Coreが直接依存しない。

## 4. State / History / Approval / Evidence Separation

以下を異なる正式情報・責務として扱う。

- Current State
- State Transition History
- Human Approval Record
- Implementation Evidence
- Review Result
- Git Operation Result

## 5. TDD

- 振る舞いを変更するImplementationでは原則TDDを行う。
- Expected Initial Test FailureはImplementation Failureではない。

## 6. Technical Retry

- Technical Retryは、Technical Retryの前提となるArtifactまたは対象範囲を変更せず、新しい設計判断を伴わない同一の技術操作の安全な再実行に限定する。
- Technical RetryはCorrectionではない。
- Technical RetryはCorrection Countを増加させない。

## 7. Correction / Evidence

- Correction後はTestを再実行する。
- Correction後は新しいImplementation Evidenceを生成する。
- 古いEvidenceを変更後のImplementationのEvidenceとして再利用しない。
- 新しいEvidenceなしにRe-Reviewへ直接進まない。

## 8. Final Approval / Merge

- Review APPROVEDとHuman Final Approvalを混同しない。
- Human Final ApprovalだけではMergeしない。
- Human Final Approvalだけではcompletedにしない。
- Final Approval Validation、Merge Readiness、Merge Execution、Merge Result Verification、completedを分離する。
- Merge成功だけではcompletedにしない。
- HumanがFinal Approvalした対象Implementationが`developer`へ正しく取り込まれたことを確認して初めてcompletedとする。
- Merge FailureとFinal Approval Failureを混同しない。

## 9. Stop / Human Handoff

- 必須Artifact、Approval、Evidence、Review Input等が不足する場合、推測で補完せず停止またはHumanへ返す。
- Handoff時には少なくとも、reason、current state、impact、next Human action、resumable stageを識別可能にする。

## 10. MVP Boundary

- Version 1 MVPのために、Specificationで定義されていない新しいUseCase、Human Decision、Approval Rule、State、Review Result、Correction Rule等を追加しない。

---

# Current Task

次の主要作業は、承認済みImplementation Planに基づくApplication Layer Phase 5 `Review & Correction`の実装開始である。

ただし、新しいセッションでは直ちにImplementationを開始しない。まずConstitution / Project Rules、最新のSession Context、Application Layer Specification、Application Layer Implementation PlanのPhase 5、Gitの現在状態を確認する。

確認後、Humanへ現在地点を簡潔に報告し、Application Layer Phase 5 Implementationを開始できる状態から再開する。

Phase 3およびPhase 4について、新しいDecisionや補助機能を追加して完成範囲を拡張しない。Phase 5開始前に重大な欠落が確認された場合だけ、既存Specification、Implementation Plan、Decision 39から53の範囲で扱う。

---

# Next Session Resume

次セッションで最初に行うこと:

1. 上記の必読文書を順番に読む。
2. `git status --short --branch`でWorking Treeと現在Branchを確認する。
3. `git log --oneline --decorate -n 5`でPR #37 merge commit `7f37fad`を確認する。
4. Application Layer Implementation PlanのPhase 5を読み、Purpose、Scope、Implementation Targets、Tests、Completion Conditionsを抽出する。
5. Phase 4で構築されたImplementation Evidence、Git Diff、Test StateをPhase 5が確認できる現在の境界を確認する。
6. Humanへ「Application Layer Phase 5 Review & Correctionを開始する」地点であることを報告する。
7. 実装に入る場合は、Phase 5の最初の振る舞いからTDDで開始する。

---

# Do Not Do

- SpecificationまたはImplementation Planを推測で変更しない。
- Human ApprovalをAIが生成、推測、補完、代替しない。
- Phase 5開始前にPhase 6以降の業務処理を先行実装しない。
- 完了済みのPhase 3およびPhase 4を、追加Decisionや不要な抽象化によって再拡張しない。
- Application LayerからInfrastructure具体実装へ直接依存しない。
- CoreからApplication Layerへの逆依存を導入しない。
- Evidence、Review、Approval、Git Result、State Historyを同一情報として扱わない。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同しない。
