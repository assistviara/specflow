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


---

## Decision 10 — EvidenceScope の表現

EvidenceScope は以下の3項目を持つ。

- target_paths
- allowed_changes
- forbidden_changes

各項目は immutable な tuple[str, ...] とする。

Path型ではなく文字列とすることで、
実ファイルパスだけでなく、
application/** や tests/** のような
glob・パターン表現も保持できるようにする。

Human Decision #35:
EvidenceScope の3項目を
tuple[str, ...] とする方式を承認する。

---

## Decision 11 — EvidenceChanges の表現

EvidenceChanges は以下を持つ。

- created_files: tuple[str, ...]
- modified_files: tuple[str, ...]
- deleted_files: tuple[str, ...]
- git_diff_path: Path | None
- change_summary: str

git_diff_path は None を許可する。

Git Diffを取得できない場合でも、
Evidence自体をPARTIALとして構築・保存できるようにするためである。

Human Decision #36:
EvidenceChanges を上記構造とし、
git_diff_path は Path | None とする方式を承認する。

---

## Decision 12 — EvidenceVerification のテスト表現

EvidenceVerification は、
Phase 3で使用しているTest Status / Test Resultの語彙を再利用する。

Test Status:

- COMPLETED
- ERROR
- NOT_RUN

Test Result:

- PASS
- FAIL
- NONE

また、以下を保持する。

- commands
- tests_created_or_modified
- test_commands
- initial_test_status
- initial_test_result
- target_test_status
- target_test_result
- full_test_status
- full_test_result
- errors
- warnings
- no_tdd_reason

Human Decision #37:
EvidenceVerificationは上記構造とし、
Phase 3のTest Status / Test Result語彙を再利用する方式を承認する。

---

## Decision 13 — Test Status / Result の組み合わせ制約

EvidenceVerificationでは、
Test StatusとTest Resultの組み合わせを以下に限定する。

- COMPLETED -> PASS または FAIL
- ERROR -> NONE
- NOT_RUN -> NONE

これにより、
テスト失敗、
テスト実行エラー、
未実行をEvidence上で区別する。

Human Decision #38:
EvidenceVerificationに上記組み合わせ制約を適用する方式を承認する。


---

## Decision 14 — EvidenceDeviations の表現

EvidenceDeviations は以下の4項目を持つ。

- out_of_scope_changes: tuple[str, ...]
- unplanned_changes: tuple[str, ...]
- unfinished_items: tuple[str, ...]
- human_approval_required: tuple[str, ...]

各項目は immutable な tuple[str, ...] とし、
該当項目がない場合は空tupleを使用する。

Phase 4ではDeviationを記録するが、
それ自体をImplementation失敗、
REVISION_REQUIRED等のReview結果として評価しない。

Human Decision #39:
EvidenceDeviationsを上記構造とする方式を承認する。


---

## Decision 15 — Codex自己申告の保持方法

Phase 3で構築されたImplementationResultは、
Phase 4で再解釈して別表現へ変換せず、
Codex自己申告として独立して保持する。

構造:

    EvidenceCodexSummary
        implementation_result: ImplementationResult

これにより、
Codex自己申告と、
Repository/Testから取得した実際の状態を
Evidence内で明確に区別する。

Human Decision #40:
ImplementationResultをEvidenceCodexSummaryとして
そのまま保持する方式を承認する。


---

## Decision 16 — RepositoryStateProvider

Repositoryの実状態取得は
Application LayerのPortとして抽象化する。

構造:

    RepositoryState
        branch: str
        base_commit: str
        git_status: str
        git_diff: str
        created_files: tuple[str, ...]
        modified_files: tuple[str, ...]
        deleted_files: tuple[str, ...]

    RepositoryStateProvider
        get_state(base_commit: str) -> RepositoryState

Providerの責務は事実の取得のみとする。

Provider自身は、
Deviation、Review結果、
Implementationの適否を判断しない。

Human Decision #41:
RepositoryStateProviderを上記Application Portとして
定義する方式を承認する。


---

## Decision 17 — TestStateProvider

Testの実状態取得は
Application LayerのPortとして抽象化する。

TestStateは以下を保持する。

- tests_created_or_modified
- test_commands
- initial_test_status
- initial_test_result
- target_test_status
- target_test_result
- full_test_status
- full_test_result
- errors
- warnings

Test Status / Resultは
EvidenceVerificationと同じ組み合わせ制約を使用する。

また、
現在のpytestを再実行した結果を
過去のRED実行記録として扱ってはならない。

過去の実行記録を取得できない場合は、
取得不能として保持し、
推測によって補完しない。

Human Decision #42:
TestStateProviderを上記Application Portとして
定義する方式を承認する。


---

## Decision 18 — Evidence比較結果の機械的分類

Phase 4では以下を機械的に区別する。

### missing_evidence

本来取得すべきEvidenceを取得できない場合。

例:

- Git Diff取得不能
- Test実行記録取得不能
- Specification / Plan / Promptを特定不能

### inconsistencies

同じ事実について、
異なるEvidence sourceが一致しない場合。

例:

- Codexが変更したと報告したファイルが
  実際のGit変更に存在しない
- 実際のGit変更がCodex報告に存在しない

### deviations

実際の状態が、
Approved Scope / Planから
客観的に外れている場合。

例:

- forbidden_changesに該当する変更
- allowed_changes外の変更

### human_approval_required

V1では以下の場合に限定して追加する。

1. Codexが明示的にHuman Approvalを要求している
2. Evidence取得不能により、
   deterministic factsだけでは
   安全に次処理を確定できない

inconsistencyまたはdeviationが存在することだけを理由に、
Human Approvalへ自動昇格してはならない。

Phase 4は事実を検出・分類するが、
PASS、REVISION_REQUIRED、
HUMAN_REVIEW_REQUIRED等の評価は行わない。

Human Decision #43:
上記の機械的分類ルールを承認する。


---

## Decision 19 — 「空」と「取得不能」の区別

RepositoryStateおよびTestStateに、
以下を追加する。

    unavailable_evidence: tuple[str, ...]

これにより、

    git_diff == ""

が、

- 差分取得に成功し、実際に差分がなかった
- Git Diffを取得できなかった

のどちらであるかを区別する。

同様に、
Test Status / ResultがNOT_RUN / NONEであることと、
過去の実行記録そのものを取得できないことを区別する。

Providerのunavailable_evidenceは、
Applicationによってmissing_evidenceへ反映する。

Human Decision #44:
取得結果の空値と取得不能を区別するため、
RepositoryState / TestStateに
unavailable_evidenceを持たせる方式を承認する。


---

## Decision 20 — Codex changed_files のV1解釈

Phase 3のImplementationResult.changed_filesは
strであるため、
Phase 4 V1では以下の規則でのみ構造化する。

- 1行につき1ファイルパスとして扱う
- 行頭・行末の空白を除去する
- 空行を除外する
- それ以上の自然言語解釈は行わない

例:

    application/foo.py
    tests/test_foo.py

は2ファイルとして扱う。

一方、

    application周辺を3ファイル修正しました

のような自然言語から
具体的なファイル名を推測してはならない。

このような記述は原文を保持したまま、
実際のGit変更とのinconsistencyとして記録する。

V1ではCodex報告上の
created / modified / deleted種別までは推測しない。

比較対象は、

    Codexが変更したと報告したファイル集合
    vs
    実際のGit変更ファイル集合

までとする。

Human Decision #45:
changed_filesを上記の限定的規則で解釈し、
自然言語からファイルパスを推測しない方式を承認する。


---

## Decision 21 — Codex Promptの識別とHash

CollectImplementationEvidenceInputは、
Codex Promptについて以下の両方を保持する。

- codex_prompt_path: Path
- codex_prompt: str

codex_prompt_pathは
Promptの出所・identityを示す。

codex_prompt本文は、
Phase 3で実際にCodexへ渡した内容を表す。

EvidenceBasisのhashは以下の規則とする。

- Specification:
  specification_pathの実ファイル内容からSHA-256
- Approved Implementation Plan:
  implementation_plan_pathの実ファイル内容からSHA-256
- Codex Prompt:
  Inputとして渡されたcodex_prompt本文からSHA-256

Codex Promptについては、
後からPath上のファイル内容が変更されても、
実行時にCodexへ渡したPrompt内容を
Evidenceとして識別できるようにする。

SpecificationまたはPlanを取得できない場合は、
内容を推測して補完せず、
missing_evidenceとして扱い、
必要に応じてEvidenceをPARTIALとする。

Human Decision #46:
Codex PromptについてPathと実行時本文の両方を保持し、
上記規則でSHA-256を算出する方式を承認する。

## Decision 22 — EvidenceBasis hash unavailable representation

**Human Decision #47**

EvidenceBasis の各 hash は `str | None` とする。

- SHA-256文字列:
  Phase 4で対象Evidenceを取得し、hashを確定できたことを表す。
- `None`:
  Phase 4で対象hashを取得・確定できなかったことを表す。
- `None` はEvidenceそのものが存在しないことを意味しない。
- 取得不能・検証不能の理由は `missing_evidence` に記録する。
- hashを確定できないEvidenceは `PARTIAL` として保持可能とする。
- `"UNKNOWN"`、`"UNAVAILABLE"` 等の代替文字列で欠損を補完しない。
- 不明なEvidenceを推測によって補完しない。

このDecisionはEvidence取得可否の表現方法のみを定める。
Implementationの適合性、Review Result、Correction要否を判定するものではない。

## Decision 23 — EvidenceBasis acquisition failure handling

**Human Decision #48**

ImplementationEvidenceBasisBuilder は、
Specification / Approved Implementation Plan の取得と
hash算出を担当する。

個別の取得失敗ではBasis構築全体を中断せず、
該当するhashを `None` とする。

Builderは取得結果を
`EvidenceBasisBuildResult` として返し、
少なくとも以下を保持する。

- `basis`
- `missing_evidence`
- `errors`

Builderが扱うのは取得・算出に関する機械的事実のみとする。

Builderは以下を判断しない。

- Evidence全体の `PARTIAL` 判定
- Review Result
- Correction / Reimplementation要否
- Human Approval要否
- Implementationの適合性・完全性

これらはUC-08 Orchestrator以降の責務とする。

Specification / Planの取得不能時に、
内容やhashを推測して補完してはならない。
