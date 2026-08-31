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
d7df90d Merge pull request #32 from assistviara/developer
```

Pull Request #32により、Application Layer SpecificationおよびApplication Layer Implementation Planは`main`へMerge済みである。

この`main`へのMergeを、Application Layer実装開始前の正式な設計ベースラインとして扱う。

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

次の主要作業は、承認済みImplementation Planに基づくApplication Layer Phase 1の実装開始である。

ただし、新しいセッションでは直ちにImplementationを開始しない。まずConstitution / Project Rules、最新のSession Context、Application Layer Specification、Application Layer Implementation Plan、Gitの現在状態を確認する。

確認後、Humanへ現在地点を簡潔に報告し、Application Layer Phase 1 Implementationを開始できる状態から再開する。

---

# Next Session Resume

次セッションで最初に行うこと:

1. 上記の必読文書を順番に読む。
2. `git status --short --branch`でWorking Treeと現在Branchを確認する。
3. `git log --oneline --decorate -n 5`でPR #32 merge commitを確認する。
4. Application Layer Implementation PlanのPhase 1を読み、Phase 1のPurpose、Scope、Implementation Targets、Tests、Completion Conditionsを抽出する。
5. Humanへ「Application Layer Phase 1 Implementationを開始する」地点であることを報告する。
6. 実装に入る場合は、Phase 1の最初の振る舞いからTDDで開始する。

---

# Do Not Do

- SpecificationまたはImplementation Planを推測で変更しない。
- Human ApprovalをAIが生成、推測、補完、代替しない。
- Phase 1開始前にPhase 2以降の業務処理を先行実装しない。
- Application LayerからInfrastructure具体実装へ直接依存しない。
- CoreからApplication Layerへの逆依存を導入しない。
- Evidence、Review、Approval、Git Result、State Historyを同一情報として扱わない。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同しない。
