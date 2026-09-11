# Decisions

## DEC-008 UC-08 Implementation Evidence設計Decision

- 決定日：2026-09-11
- 決定者：たけしゃん
- 対象UseCase：UC-08 Collect Implementation Evidence
- 根拠Specification：application_layer_specification_v0.2.0-draft.md
- 根拠Implementation Plan：application_layer_implementation_plan_v0.1.0-draft.md
- 判定：APPROVED

### Decisionの目的

UC-08の実装にあたり、
Specificationおよび承認済みImplementation Planから
一意に決定できない実装設計事項について、
Human Decisionとして以下を確定する。

本DecisionはSpecificationまたはImplementation Planの
要求を変更・拡張するものではない。

---

### Decision 1：Implementation Evidenceの識別子

Implementation Evidenceの一意識別子にはUUIDを使用する。

連番による識別子は使用しない。

UUIDは、
Evidenceを複数回生成する場合、
CorrectionまたはReimplementationによって
新しいEvidenceを生成する場合、
および複数環境でEvidenceを扱う場合にも
一意性を維持するために使用する。

---

### Decision 2：ImplementationとEvidenceの識別子分離

ImplementationとImplementation Evidenceは
異なるEntityとして扱う。

以下の識別子を独立して保持する。

- implementation_id: UUID
- evidence_id: UUID

implementation_idは、
Evidenceの対象となったImplementationを識別する。

evidence_idは、
そのImplementationについて収集・構築された
個々のImplementation Evidenceを識別する。

1つのImplementationに対して
複数のEvidenceが存在し得るため、
両者の識別子を同一視しない。

---

### Decision 3：Evidence Status

Implementation Evidenceのidentity.statusは、
Implementationの成功または失敗、
Test Result、
Review Resultを表さない。

identity.statusは、
Implementation Evidenceの収集成立状態を表し、
Version 1では以下の2値とする。

- COLLECTED
- PARTIAL

COLLECTEDは、
必要なEvidence情報を取得または確認でき、
Evidenceとして構築できた状態を表す。

Test ResultがFAILである場合、
Deviation、Warning、
Human Approval Required等が存在する場合でも、
必要なEvidenceを取得できている場合は
COLLECTEDとなり得る。

PARTIALは、
必要なEvidence情報の一部を
取得または確認できなかった状態を表す。

取得できなかった情報を推測または補完してはならず、
不足しているEvidenceを明示的に記録する。

Evidence persistence自体に失敗し、
Evidenceを成立させられない場合は、
identity.statusへERRORを保存するのではなく、
UC-08自体の実行失敗として扱う。

---

### Decision 4：Evidence間のTraceability

Version 1では、
Evidence間のTraceabilityを
最小限の直線的な関係として表現する。

Implementation Evidenceは、
少なくとも以下を保持する。

- evidence_id: UUID
- implementation_id: UUID
- implementation_kind
- previous_evidence_id

implementation_kindは、
以下のいずれかとする。

- INITIAL
- CORRECTION
- REIMPLEMENTATION

INITIALの場合、
previous_evidence_idはNoneとする。

CORRECTIONまたはREIMPLEMENTATIONの場合、
previous_evidence_idには
直前のImplementation Evidenceのevidence_idを保持する。

Version 1では、
generation、
correction_count、
履歴配列、
Evidence tree等の複雑なVersion管理は導入しない。

---

### Decision 5：Repository / Test状態取得の抽象

Phase 4では、
実RepositoryおよびTest状態を取得するApplication Portを
責務別に分離する。

Version 1では、
以下の2系統を基本とする。

- RepositoryStateProvider
- TestStateProvider

RepositoryStateProviderは、
RepositoryおよびGitに関する実状態を取得する。

少なくとも、
Branch、
Base Commit確認に必要な情報、
Git Status、
Git Diff、
Created / Modified / Deleted Files、
Source CodeおよびTest Code確認に必要な情報を
取得可能とする。

TestStateProviderは、
Test実行およびTest結果に関する実状態を取得する。

少なくとも、
Test Command、
Initial Test Result、
Target Test Result、
Full Test Result、
Test Execution Error等を
取得可能とする。

Providerは事実の取得を担当し、
Runner Reportとの不一致判定、
Evidence構築、
Workflow判断、
Review判断を担当しない。

責務分離は以下とする。

Infrastructure / Provider
  = 実状態を取得する

Application Layer
  = Runner Reportと実状態を比較し、
    Evidenceを構築する

Phase 5 Review
  = Evidenceおよび実Artifactを評価する

Application Layerは、
Git CommandまたはTest実行環境の
具体的実装へ直接依存しない。

---

### Decision 6：不一致・不足の分類

Phase 4における
Error、
Warning、
Deviation、
Human Approval Requiredの分類は、
機械的に確認可能な事実に限定する。

Errorは、
Evidence取得、
検証、
保存等の処理そのものに失敗した事実を表す。

Warningは、
Evidenceは取得できているが、
Review時に注意すべき非致命的な事実を表す。

Deviationは、
Runner Report、
Approved Scope、
Implementation Plan等と、
実際のRepositoryまたはTest状態との
客観的な不一致を表す。

Human Approval Requiredは、
既にPhase 3またはRunner Result等から
明示的に引き継がれたHuman判断事項、
または機械的事実だけでは
安全に次処理を確定できない事項を表す。

これらの分類は排他的である必要はない。

Phase 4は、
Error、
Warning、
Deviation、
Human Approval Requiredの存在から、
Specification適合性、
Implementationの合否、
Review Resultを決定しない。

意味的な適合性評価はPhase 5の責務とする。

---

### Decision 7：UC-08 Input / Output DTO契約

UC-08 Inputは、
Evidence収集対象を特定する情報と、
Phase 3のImplementation Resultを
引き継ぐ情報に限定する。

CollectImplementationEvidenceInputは、
少なくとも以下を保持できるものとする。

- implementation_id
- implementation_kind
- previous_evidence_id
- specification_path
- specification_approval_id
- implementation_plan_path
- implementation_plan_approval_id
- codex_prompt
- implementation_branch
- base_commit
- implementation_result
- 必要なApproval Identifier

Actual Git Diff、
Actual Git Status、
Actual Changed Files、
Actual Test Result等の実状態は、
Input DTOに自己申告情報として混在させず、
RepositoryStateProviderおよび
TestStateProviderから独立に取得する。

CollectImplementationEvidenceOutputは、
少なくとも以下を保持できるものとする。

- success
- evidence_id
- implementation_id
- implementation_evidence
- evidence_path
- git_diff_path
- status
- missing_evidence
- inconsistencies
- human_approval_required
- error_message

successとEvidence statusは独立した概念とする。

Evidenceの一部を取得できず
status = PARTIALであっても、
不足情報を保持したEvidenceを
正常に構築・保存し、
Phase 5へ引き渡せる場合は
success = Trueとする。

Evidence自体を構築できない、
または保存できず、
UC-08としてPhase 5へ引き渡せない場合は
success = Falseとする。

したがって、

success
  = UC-08処理が成立したか

status
  = 必要なEvidenceを収集できたか

Test Result
  = Test実行結果

Deviation
  = 報告と実状態の客観的不一致

Review Result
  = Phase 5による適合性評価

として明確に分離する。

---

### Decision 8：Evidence Repositoryとファイル保存

Implementation Evidenceの正本は、
evidence/配下へJSONとして保存する。

Git Diffは、
Implementation Evidenceに関連付けられた
補助証跡として別ファイルへ保存する。

Version 1では、
以下の命名を基本とする。

evidence/
  implementation_<evidence_id>.json
  implementation_<evidence_id>.diff

Application Layerは、
ImplementationEvidenceRepository抽象を介して
Evidenceを永続化する。

Version 1のRepositoryは、
少なくとも以下に相当する責務を持つ。

- save(evidence)
- load(evidence_id)
- exists(evidence_id)
- save_diff(evidence_id, diff)

既存Evidenceを更新するための
update操作は設けない。

Reviewに使用されたEvidenceを
後から上書きしてはならない。

同一evidence_idが既に存在する場合も、
既存Evidenceを上書きせず、
保存失敗として扱う。

CorrectionまたはReimplementationでは、
新しいevidence_idを発行し、
新しいEvidenceを保存する。

旧Evidenceとの関係は、
previous_evidence_idによって保持する。

---

### 設計原則

Phase 4の責務分離は以下とする。

Phase 3
  ↓
Implementation Result
  ↓
UC-08 Collect Implementation Evidence
  ↓
RepositoryStateProvider / TestStateProvider
  ↓
Actual Repository / Test State
  ↓
Application Layer
  - Evidence対象の識別
  - Runner Reportと実状態の比較
  - Missing Evidenceの記録
  - Deviationの記録
  - Evidence構築
  - Evidence永続化
  ↓
Implementation Evidence
  ↓
Phase 5 Review

Phase 4は、
Codexの自己申告のみをEvidenceとして採用しない。

また、
不足情報を推測によって補完しない。

Phase 4はEvidenceを収集・照合・保存する工程であり、
Specification適合性、
Review Result、
Correction要否、
Final Human Approval等を決定しない。

---

# Closing

本Decisionにより、
UC-08 Collect Implementation Evidenceの実装に必要な
上記設計事項をHuman Decisionとして承認する。

Implementationは、
Specification、
承認済みImplementation Plan、
および本Decisionの範囲内でTDDにより進める。


---

## Decision 9 — created_at の時刻表現

Implementation Evidence の identity に含める created_at は、
Application内部では timezone-aware な datetime として保持する。

timezone 情報を持たない naive datetime は使用しない。

JSONへ永続化する際は、
ISO 8601形式の文字列へ変換する。

例:

    2026-09-12T08:30:00+09:00

これにより、
Evidence がいつ収集・構築されたかを
タイムゾーンを失わずに追跡できるようにする。

Human Decision #34:
created_at は
「timezone-aware datetime を内部保持し、
JSON保存時は ISO 8601 文字列とする」
方式を承認する。
