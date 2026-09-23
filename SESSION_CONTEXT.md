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

Phase 5 Completion Audit時点の確認済み状態:

- Branch: `developer`
- HEAD / `origin/developer`: `a4766c4`
- Working tree: clean（本書更新前の監査基準点）
- Application Layer Phase 5: **COMPLETE**
- Target 1〜9: Complete
- Final Completion Audit: **PHASE_5_COMPLETE**
- Phase 6: **未着手**

確認済みCommit:

```text
a4766c4 feat: Phase 5 レビューハンドオフを追加
```

このCommitをPhase 5 Completion Baselineとする。

以前の基準点は`7f37fad`（Pull Request #37）であり、Phase 3のCodex実行traceからPhase 4のTest State取得までの経路を`main`へMerge済みである。これは過去の履歴であり、現在の`main`との一致を示すものではない。

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

- Phase 4 Implementation Gap修復（`83eff2f`）
- Application Layer Phase 5 Target 1〜9の実装・Commit・Push
- Phase 5 Final Completion Audit: `PHASE_5_COMPLETE`

### Phase 5 Completed Targets

| Target | 完了内容 | Commit |
|---|---|---|
| 1 | Review Input / Artifact Consistency | `6fb8139` |
| 2 | Five-aspect Review | `ae71b36` |
| 3 | Semantic Staged Review | `76d680d` |
| 4 | Review Result | `4bee88b` |
| 5 | Technical Retry | `97528bb` |
| 6 | Correction Routing / Correction Instruction | `451d422` |
| 7 | Correction → Re-Test → New Evidence → Re-Review | `aa15a61` |
| 8 | Correction Limit / Early Stop / Continuation Decision | `fa1c9f6` |
| 9 | Human Review / Critical Change Approval / Phase 6 Handoff | `a4766c4` |

Completion Baselineに対する最新のTest確認結果:

```text
Target 1〜9 related tests: 534 passed
Full Test Suite: 960 passed
```

---

# Formal Artifacts

Application Layer実装開始時の基準文書は以下である。

- Specification: `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
- Implementation Plan: `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`
- Decision 39〜53: `projects/specflow/docs/decision_implementation_evidence.md`
- Phase 5 Target 1〜9で確定・承認済みのHuman Decision

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

## 11. Phase 5 Confirmed Boundaries

- Test FAILとTechnical Retry、Technical RetryとCorrection、CorrectionとRe-Reviewを区別する。
- Review ResultとHuman Approval、APPROVEDとHuman Final Approvalを区別する。
- Phase 6 HandoffとPhase 6実行を区別する。
- Human DecisionおよびCritical Change ApprovalをAIが生成しない。
- 停止理由に合わせてReview Resultを書き換えない。
- Correction後は旧Evidenceを上書きせずNew Evidenceを生成する。
- saved implementation identityとobserved repository stateを分離する。
- Final Approval / Merge / completedはPhase 5では実行しない。

Phase 5 implementationがCOMPLETEであることと、個別WorkflowがPhase 6 readyであることは別である。Human判断待ちで停止するWorkflowもPhase 5の正常な経路である。

---

# Current Task

現在の再開地点は、**Phase 5 COMPLETE / Phase 6未着手**である。次の作業はApplication Layer Phase 6 `Final Approval & Merge`の仕様確認である。

新しいセッションでは直ちに設計・Implementationを開始しない。まずConstitution / Project Rules、最新のSession Context、Application Layer Specification、Application Layer Implementation PlanのPhase 6、Gitの現在状態を確認する。

確認後、Humanへ現在地点と既存Artifactに定義されたPhase 6の範囲を簡潔に報告する。本書はPhase 6の新しい設計判断や実装承認を追加しない。

Phase 5へ戻って追加実装・改善・Refactorを行わない。完了済みのPhase 3・4も再拡張しない。

## Responsibilities Remaining for Phase 6

- Final Approval Target Artifactの確定
- 最終Repository状態／現在HEADの取得・確認
- Human Final Approval
- Final Approval Record
- Final Approvalの検証
- Merge前検証
- Merge
- Merge成功確認
- completedへの遷移

これらはPhase 6の責務であり、Phase 5の未完成事項として扱わない。

---

# Next Session Resume

次セッションで最初に行うこと:

1. 上記の必読文書を順番に読む。
2. `git status --short --branch`でWorking Treeと現在Branchを確認する。
3. Git履歴でPhase 5 Completion Baseline `a4766c4`と現在のHEADとの差を確認する。本書更新後のCommitが存在してもCompletion Baselineとは区別する。
4. Phase 5 Target 1〜9完了、534 related tests / 960 full suite passed、`PHASE_5_COMPLETE`監査済みであることを確認する。
5. SpecificationとImplementation PlanのPhase 6を読み、Purpose、Scope、Implementation Targets、Tests、Completion Conditionsを抽出する。
6. Phase 5 HandoffとPhase 6実行の境界を維持し、既存Artifactから一意に決まらない業務判断は推測で補完しない。
7. Humanへ「Phase 5完了・Phase 6未着手、Phase 6仕様確認から再開する」地点であることを報告する。Phase 5の再実装・改善へ戻らない。

---

# Do Not Do

- SpecificationまたはImplementation Planを推測で変更しない。
- Human ApprovalをAIが生成、推測、補完、代替しない。
- Phase 6の仕様確認を飛ばして設計・実装を開始しない。
- 完了済みのPhase 5へ戻って追加実装・改善・Refactorを行わない。
- 完了済みのPhase 3およびPhase 4を、追加Decisionや不要な抽象化によって再拡張しない。
- Application LayerからInfrastructure具体実装へ直接依存しない。
- CoreからApplication Layerへの逆依存を導入しない。
- Evidence、Review、Approval、Git Result、State Historyを同一情報として扱わない。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同しない。
