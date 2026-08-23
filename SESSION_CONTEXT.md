# SESSION_CONTEXT.md

## Purpose

この文書は、ChatGPTセッション切替時の引継ぎ文書である。

新しいセッションでは、

1. SpecFlow_Constitution_v1.0.md
2. constitution.md
3. SESSION_CONTEXT.md

の順に読み込み、

現在の開発コンテキストを復元すること。

本書は、
現在の開発状況・思考状態・次工程を引き継ぐことを目的とする。

---

# Current State

## Constitution

SpecFlow Constitution Version 1.0 は完成している。

ConstitutionはSpecFlowにおける最高規範であり、
すべての設計・実装・レビューは
Constitutionを最優先として行う。

constitution.mdは、
Constitutionを運用するための
実装ルールとして扱う。

---

## Current Phase

Project Foundation は完了した。

AI Runner Foundationまでの

Specification
↓
Implementation Plan
↓
Decision
↓
Implementation
↓
Review

は完了している。

現在は、

Application Layer Specification

の設計および横断監査を完了し、
次工程へ移行する段階にある。

---

## Current Position

完了

- Constitution Version 1.0
- constitution.md
- Architecture
- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator
- AI Runner Foundation
- AI Runner Foundation Implementation Plan
- AI Runner Foundation Decision
- AI Runner Foundation Implementation
- AI Runner Foundation Review
- Application Layer Specification Draft v0.2.0
- Application Layer Specification 横断監査

AI Runner Foundationについては、

Specification
↓
Implementation Plan
↓
Decision
↓
Implementation
↓
Review

まで完了している。

Application Layerについては、

Application Layer Specification Draft v0.2.0

を作成し、

State Transition
Approval
Approval Validation
Implementation
Implementation Failure
Review
Review Failure
Correction
Technical Retry
Critical Change
Implementation Evidence
Final Approval
Merge
Human Escalation

等の主要な横断関係について監査を実施した。

横断監査では、
実装時に判断を誤らせる可能性のある
State、Result、Approval、Failure、Retry、Correction等の
責務境界および遷移関係を重点的に確認した。

横断監査は第1号から第12号まで実施し、
重大な設計上の不整合について修正を行った。

---

# Application Layer Specification

## Current Status

Application Layer Specification v0.2.0-draftは、
主要設計および横断監査を完了した。

現時点では、

「実装判断を誤らせる重大な不整合が残っているか」

を監査終了基準とし、
横断監査を終了する判断を行った。

文章表現上の軽微な差異を
無制限に探索することは行わない。

今後、新たな重大な矛盾が発見された場合は、
通常のSpecification変更手続きに従って扱う。

---

# Important Decisions

## 1. Human Sovereignty

SpecFlowではHumanが最終的な意思決定主体である。

AI Runner、Application Layer、Review等が
Human Approvalを独自に生成または代替してはならない。

---

## 2. Specification as Source of Truth

Specificationを唯一の正本とする。

Implementation Pipelineでは、
Specificationへの忠実性を最優先する。

Specificationに不足、矛盾、不明確さが存在する場合、
AIが推測によって補完してはならない。

Humanへ判断を返す。

---

## 3. Approval and Approval Validation

Human ApprovalとApproval Validationは別責務とする。

HumanがApproval Decisionを行い、
Application LayerはApproval Recordと
現在の対象Artifactとの同一性・有効性を検証する。

Approval Validationがinvalidの場合、
そのApprovalを前提として後続工程へ進んではならない。

対応するApproval Pending Stateを維持し、
Humanへ判断を返す。

主な対応関係は以下とする。

Implementation Plan Approval
→ plan_approval_pending

Critical Change Approval
→ critical_approval_pending

Final Approval
→ final_approval_pending

---

## 4. Implementation State

Implementation正常系は概念的に、

plan_approved
↓
implementation_prompt_generating
↓
implementation_ready
↓
implementing
↓
implementation_completed

とする。

UC-05では、
Codex Prompt生成開始時に
implementation_prompt_generatingへ遷移する。

Codex Promptが正常に生成され、
SpecificationおよびApproved Implementation Planとの
対応関係が確認され、
Implementationへ利用可能となった場合に
implementation_readyへ遷移する。

UC-06では、
Implementation開始時に

implementation_ready
↓
implementing

へ遷移する。

Implementationが承認Scope内で正常に完了し、
必要なTest実行および
Implementation Evidence構築に必要な実行結果の取得が
完了した場合に

implementation_completed

へ遷移する。

---

## 5. Implementation Failure

implementation_failedは、
TDDにおける期待されたTest失敗を意味しない。

以下を区別する。

Test Result = FAIL
≠
Test Execution Error
≠
implementation_failed

Implementation工程そのものを
技術的理由により正常に継続または完了できない場合に、
Implementation Failure Transitionを使用する。

安全なTechnical Retryによって回復可能な場合は、
定められた範囲で同一技術操作を再実行できる。

回復できない場合は、
implementation_failedへ遷移してHumanへ判断を返す。

---

## 6. Review

Review Resultは、

APPROVED
REVISION_REQUIRED
HUMAN_REVIEW_REQUIRED

とする。

これらはWorkflow Stateとは区別する。

Reviewは、
Implementation Evidenceだけを根拠としてはならない。

少なくとも、

Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Code
Test Result

を相互に比較する。

Reviewが技術的理由により実行不能となった場合と、
Review結果としてImplementation上の問題を発見した場合を
混同してはならない。

---

## 7. Correction

Correctionは、
承認済みHuman Approval Scope内で
成果物を変更する修正である。

REVISION_REQUIREDの場合でも、
Human Approval Scope内で安全にCorrectionできない場合は、

HUMAN_REVIEW_REQUIRED

としてHumanへ判断を返す。

Correction後は、
以前のImplementation Evidenceを書き換えず、
新しいImplementation Evidenceを生成する。

---

## 8. Correction Loop

Initial ImplementationはCorrection Countに含めない。

自動Correctionの最大回数は原則3回とする。

ただし、
Maximum Correction Countだけで制御しない。

以下を組み合わせる。

Maximum Correction Count
+
Early Stop Conditions
+
Convergence Detection
+
Human Escalation

異常、悪化、非収束、
Human Approval Scope外変更等を検出した場合は、
最大回数到達前でも自動Correctionを停止する。

---

## 9. Technical Retry

Technical Retryは、
成果物または承認対象Artifactを変更せず、
同一の技術操作を再実行する処理である。

Technical RetryはCorrectionではない。

Technical RetryはCorrection Countに含めない。

Technical Retryによって成果物を変更してはならない。

成果物変更が必要な場合は、
Correction、Critical Change、
または上位Artifactの再検討として扱う。

---

## 10. Critical Change

Human Approval Scopeを超える変更が必要な場合、
AI RunnerまたはApplication Layerが
独自に変更を実行してはならない。

Critical Changeに該当する場合は、

critical_approval_pending

へ遷移し、
Human Approvalを要求する。

Approval Validationがinvalidの場合は、

implementingへ戻らず、
critical_approval_pendingを維持し、
Humanへ判断を返す。

---

## 11. Implementation Evidence

Implementation Evidenceは、
Codex Runnerが自己確定するものではない。

Codex Runnerは、
Evidence構築に必要な実行結果を返す。

Application Layerが、

Source Code
Git Status
Git Diff
Test Result
Runner Result

等を収集してImplementation Evidenceを構築する。

Correction後は、
過去のImplementation Evidenceを更新・上書きせず、
新しいImplementation Evidenceを生成する。

これにより、
Correction HistoryおよびReview Historyを追跡可能にする。

---

## 12. Final Approval and Merge

Review ResultがAPPROVEDとなっただけでは、
Implementationはcompletedではない。

概念的には、

APPROVED
↓
final_approval_pending
↓
Human Final Approval
↓
Final Approval Validation
↓
UC-12 Merge Approved Implementation
↓
developerへmerge
↓
Merge Result Verification
↓
completed

とする。

Final Approval Validationがinvalidの場合は、

mergeを実行せず、
final_approval_pendingを維持し、
Humanへ判断を返す。

mergeに失敗した場合も、

completedへ遷移せず、
final_approval_pendingを維持し、
Humanへ判断を返す。

Version 1では、
merge専用Failure Stateは新設しない。

---

# Current Thinking

## 1

SpecFlowは、

仕様書を唯一の正本とする
Human Centered AI Development Platformである。

Humanが意思決定を行い、

AIは

- 設計
- 実装
- レビュー

を担当する。

---

## 2

Implementation Pipelineでは、
創造性よりSpecificationへの忠実性を優先する。

AIが実装工程で
「より良いと思われる設計」を独自に追加することは、
改善ではなくSpecification逸脱となり得る。

改善提案は可能だが、
採用判断はHumanが行う。

---

## 3

Application Layerは、
単なるEngine呼び出し層ではない。

Application Layerは、

- Workflow State
- Approval Validation
- Runner Result
- Failure
- Retry
- Correction
- Critical Change
- Evidence
- Review
- Human Escalation

を統合し、

「次に何をしてよいか」

を制御する責務を持つ。

---

## 4

StateとResultを混同しない。

例：

reviewing
= State

APPROVED
REVISION_REQUIRED
HUMAN_REVIEW_REQUIRED
= Review Result

同様に、

Test Result = FAIL

と

Technical Error

を混同しない。

---

## 5

Humanへ判断を返す場合でも、
その直前のWorkflow StateまたはResultを明確にする。

Human Escalation自体を、
曖昧な万能Stateとして使用しない。

---

# Current Task

## Next Step

Application Layer Specification v0.2.0-draftの
横断監査は完了した。

次工程へ進む前に、

1. Git Status確認
2. Specification変更をCommit
3. pytest実行
4. developer branchへpush
5. Working Tree Clean確認

を行う。

その後、

Application Layer Specificationを基準として、
次のImplementation Pipeline工程へ進む。

具体的な次工程を開始する際は、
Constitution、
constitution.md、
Application Layer Specification
との整合性を確認し、

SpecFlow自身の

Specification
↓
Implementation Plan
↓
Decision
↓
Implementation
↓
Review

の開発プロセスを維持する。

---

# Pending Reviews

Application Layer Specificationについて、
重大な横断的不整合を対象とした監査は完了した。

現時点では、
軽微な文章表現の差異のみを目的として
横断監査を継続しない。

ただし、
Implementation Plan作成または実装時に
Specification上の不足・矛盾・不明確さが発見された場合は、
推測で補完しない。

Humanへ返し、
必要なSpecification再検討を行う。

---

# Constraints

以下を守ること。

- Constitutionを最優先とする。
- constitution.mdを運用ルールとする。
- Specificationを唯一の正本として扱う。
- 日本語で議論する。
- 推測で仕様変更しない。
- 不明点はHumanへ確認する。
- 創造性と忠実性を混在させない。
- 実装前にImplementation Planを作成する。
- Human ApprovalをAIが代替しない。
- ApprovalとApproval Validationを混同しない。
- Technical RetryとCorrectionを混同しない。
- Test FAILとTest Execution Errorを混同しない。
- Review ResultとWorkflow Stateを混同しない。
- Implementation Evidenceを上書きしない。
- Reviewなしに完了としない。
- 有効なFinal Approvalおよびmerge成功なしにcompletedとしない。

---

# Session Resume

この文書を読み終えたら、

現在の状況を簡潔に要約し、
Humanへ確認を求めること。

Humanの確認前に、

- 新しい設計
- Implementation Planの確定
- 実装
- Specification変更

を開始してはならない。

Humanの確認後、

Current Taskに記載された位置から
SpecFlow開発を再開すること。

既存EngineまたはApplication Layerの仕様変更は
推測で行わず、

Constitution
constitution.md
Specification
Implementation Plan
Decision
Review

との整合性を確認しながら進めること。