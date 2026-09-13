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

## Decision 24 — Approved Scope source

**Human Decision #49**

EvidenceScope の正本は
Approved Implementation Plan とする。

Phase 4はImplementation Plan本文を
AIまたは曖昧な自然言語解析によって独自解釈せず、
UC-08にはHuman承認済みPlanに由来する
構造化Approved Scopeを入力として渡す。

構造化Approved Scopeは少なくとも以下を保持する。

- `target_paths`
- `allowed_changes`
- `forbidden_changes`

構造化Approved Scopeは
Approved Implementation Planを置き換える新たな正本ではなく、
Phase 4で機械比較を行うための表現とする。

Approved Scopeを取得・確定できない場合は、
Codex Prompt、Implementation Result、Git Diff等から
推測または逆算して補完してはならない。

取得・確定できないScopeは `missing_evidence` として記録し、
Evidenceは `PARTIAL` として保持可能とする。

Phase 4はApproved Scopeと実際の変更との差異を
機械的事実として記録するだけであり、
Implementationの適合性、Review Result、
Correction / Reimplementation要否を判断しない。

## Decision 25 — Approved Scope unavailable representation

**Human Decision #50**

`CollectImplementationEvidenceInput` に
`approved_scope: EvidenceScope | None`
を保持する。

`EvidenceScope` が与えられた場合、
それはHuman承認済みApproved Implementation Planに由来する、
Phase 4機械比較用の構造化Approved Scopeを表す。

`approved_scope=None` は、
Approved Scopeを取得・確定できなかったことを表す。

`None` を空の `EvidenceScope` に置き換えてはならない。

`EvidenceScope` 内の空タプルは、
そのScope項目を確認した結果、対象なしであることを表し、
不明を意味しない。

`approved_scope=None` の場合、
UC-08はCodex Prompt、Implementation Result、
Git Diff等からScopeを推測または逆算して補完してはならない。

取得・確定できないScopeは
`missing_evidence` として扱い、
Evidenceは `PARTIAL` として保持可能とする。

`approved_scope=None` 自体は、
Implementationの適合性、Review Result、
Correction / Reimplementation要否を意味しない。

## Decision 26 — ImplementationEvidence scope unavailable representation

**Human Decision #51**

`ImplementationEvidence.scope` は
`EvidenceScope | None` とする。

`EvidenceScope` が保持されている場合、
Human承認済みApproved Implementation Planに由来する
構造化Approved Scopeが取得・確定できていることを表す。

`scope=None` は、
Approved Scopeを取得・確定できなかったことを表す。

`None` を空の `EvidenceScope` に置き換えてはならない。

空の `EvidenceScope` は、
各Scope項目を確認した結果、対象なしであることを表し、
Scope不明を意味しない。

Scope取得不能の理由は `missing_evidence` に記録し、
Evidence全体の収集状態は
`EvidenceIdentity.status` の `COLLECTED` / `PARTIAL`
によって別途表現する。

`scope=None` 自体は、
Implementationの適合性、Review Result、
Correction / Reimplementation要否、
Human Approval要否を意味しない。

将来、Scope取得不能に複数の状態表現が必要になった場合は、
専用型への拡張を別Decisionとして検討する。

## Decision 27 — Evidence collection status rule

**Human Decision #52**

`EvidenceIdentity.status` の判定規則は、
`missing_evidence` の有無のみを基準とする。

- `missing_evidence` が空の場合:
  `COLLECTED`
- `missing_evidence` が1件以上ある場合:
  `PARTIAL`

`errors`、`warnings`、`inconsistencies`、
`deviations` が存在すること自体は、
`PARTIAL` 判定の理由としない。

`COLLECTED` / `PARTIAL` は
Implementationの成功・失敗、
Test Result、
Review Result、
Correction / Reimplementation要否を表さない。

これはPhase 4における
Evidence収集状態のみを表す。

例えば、
Codex Runner Reportと実際のGit Diffに不一致が存在しても、
必要なEvidenceが取得できており
`missing_evidence` が空であれば
statusは `COLLECTED` とする。

一方、
Approved Scope、Git Diff、Test Result等、
収集対象Evidenceの一部を取得・確定できず
`missing_evidence` に記録された場合は
statusを `PARTIAL` とする。

Phase 4はこのstatusから
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

## Decision 28 — Comparator behavior when Approved Scope is unavailable

**Human Decision #53**

`ImplementationEvidenceComparator.compare()` の
`scope` は `EvidenceScope | None` とする。

`scope=None` の場合、
Approved Scopeを取得・確定できなかったことを表す。

この場合もComparatorは、
Scopeを必要としない機械比較を継続する。

継続する処理:

- Repository / Test の unavailable evidence収集
- Codex Runner Reportのchanged filesと
  actual repository changesの比較
- inconsistenciesの記録
- Codexが明示したHuman Approval要求の継承
- missing evidenceに基づくHuman judgment要求の生成

一方、Scopeを必要とする以下の判定は行わない。

- `out_of_scope_changes`
- `unplanned_changes`

`scope=None` の場合は
`"approved scope unavailable"` を
`missing_evidence` に追加する。

この場合の

- `out_of_scope_changes`
- `unplanned_changes`

は空タプルとして保持する。

この空タプルは
「該当変更なし」という意味ではなく、
Approved Scope不明のため判定を行っていないことを表す。

その事実は、

- `scope=None`
- `missing_evidence`
- `EvidenceIdentity.status=PARTIAL`

によって区別する。

Codex Prompt、Implementation Result、Git Diff等から
Scopeを推測または逆算して補完してはならない。

Phase 4はこの状態から
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

## Decision 29 — EvidenceChanges change_summary source

**Human Decision #54**

V1における `EvidenceChanges.change_summary` は、
`ImplementationResult.implementation_summary` を
そのまま使用する。

Phase 4は、
Git Diffやactual repository changesから
独自の文章要約を生成しない。

`change_summary` は
Codex Runner Report由来の情報として扱う。

actual repository changesの事実は、

- `created_files`
- `modified_files`
- `deleted_files`
- `git_diff_path`

によって保持する。

Runner Report由来の説明とactual repository stateは
区別してEvidenceへ保持する。

Phase 4は、
`change_summary` の内容について
Implementationの適合性、完全性、成功を判断しない。

Runner Reportとactual repository stateの不一致は、
既存の機械比較規則に従って
`inconsistencies` または該当するEvidence分類へ記録する。

Phase 4はactual changesから新たな意味解釈を生成せず、
Evidenceの意味評価はPhase 5へ委ねる。

## Decision 30 — Implementation Result unavailable representation

**Human Decision #55**

`EvidenceCodexSummary.implementation_result` は、
`ImplementationResult | None` とする。

`implementation_result=None` は、
Phase 3のImplementation Resultを
取得・確定できなかったことを表す。

この場合は、

`"implementation result unavailable"`

を `missing_evidence` に記録する。

その結果、
Decision 27の規則に従い
`EvidenceIdentity.status` は `PARTIAL` となる。

Implementation Resultが取得不能な場合、
空値やダミーの `ImplementationResult` を生成してはならない。

Codex Prompt、Git Diff、Repository State、
Test State等からImplementation Resultの内容を
推測または逆算して補完してはならない。

Implementation Resultを必要とする
Codex Runner Reportとactual stateの比較は行わない。

ただし、

- Evidence Basisの取得
- Repository Stateの取得
- Test Stateの取得
- その他Implementation Resultを必要としないEvidence収集

は継続する。

Implementation Result取得不能そのものから、
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

Phase 4は取得不能状態をEvidenceとして保持し、
その意味評価をPhase 5へ委ねる。

## Decision 31 — Change Summary unavailable representation

**Human Decision #56**

`EvidenceChanges.change_summary` は、
`str | None` とする。

文字列が存在する場合は、
Decision 29に従い、
Phase 3 `ImplementationResult.implementation_summary`
をそのまま保持する。

`None` は、
Phase 3 Implementation Resultを取得・確定できないため、
`change_summary` も取得できないことを表す。

`change_summary=None` のためだけに、
追加の `missing_evidence` は生成しない。

根本原因はDecision 30に従い、

`"implementation result unavailable"`

として `missing_evidence` に記録する。

Git Diff、Repository State、Test State、
Codex Promptその他のEvidenceから、
`change_summary` を推測、逆算、再生成してはならない。

空文字列、`"UNKNOWN"`、`"NONE"` 等を
取得不能状態の代替表現として使用してはならない。

JSONでは `null` として保存し、
復元時も `None` とする。

`change_summary=None` そのものから、
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

Phase 4は取得不能状態を保持し、
その意味評価をPhase 5へ委ねる。

## Decision 32 — No-TDD Reason source and unavailable representation

**Human Decision #57**

`EvidenceVerification.no_tdd_reason` は、
TDDを実施しなかった理由が明示的に取得できた場合のみ、
その理由を文字列として保持する。

V1では、その情報源を `TestState` とする。

`TestState.no_tdd_reason` は `str | None` とする。

TDDを実施済みの場合は `None` とする。

TDDを実施しておらず、
その理由が明示的に取得できた場合は、
その理由を文字列として保持する。

TDDを実施していないが理由を取得・確認できない場合は、
`None` とし、

`"no TDD reason unavailable"`

を `missing_evidence` に記録する。

`test_required`、Git Diff、Codex Prompt、
Test Resultその他のEvidenceから、
TDDを実施しなかった理由を推測、逆算、生成してはならない。

空文字列、`"UNKNOWN"` 等を
理由取得不能の代替表現として使用してはならない。

`no_tdd_reason=None` そのものから、
TDD実施済みか理由取得不能かを判断しない。

TDD実施有無の判定は、
actual Test Stateとして取得された事実に基づき、
Application Layerが機械的に行う。

`no_tdd_reason=None` または
`"no TDD reason unavailable"` から、
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

Phase 4は取得事実と取得不能状態をEvidenceとして保持し、
その意味評価をPhase 5へ委ねる。

## Decision 33 — Mechanical determination of No-TDD state

**Human Decision #58**

V1では、
actual Test Stateの `initial_test_status` を、
TDD開始Evidenceの機械的判定に使用する。

`initial_test_status != "NOT_RUN"` の場合、
TDD開始Evidenceが存在するものとして扱い、
`no_tdd_reason` を要求しない。

`initial_test_status == "NOT_RUN"` かつ
`no_tdd_reason is not None` の場合、
TDD未実施理由が明示的に取得されているものとして扱い、
No-TDD Reasonに関する `missing_evidence` は追加しない。

`initial_test_status == "NOT_RUN"` かつ
`no_tdd_reason is None` の場合、
TDD未実施理由を取得・確認できないものとして、

`"no TDD reason unavailable"`

を `missing_evidence` に追加する。

`initial_test_status == "ERROR"` は、
TDD開始Evidenceの取得または実行を試みた結果、
Technical Errorが発生した事実として扱う。

したがって `"ERROR"` を
TDD未実施とは扱わず、
No-TDD Reasonを要求しない。

Phase 4は、
この機械的判定からImplementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。

## Decision 34 — UC-08 failure output representation

**Human Decision #59**

UC-08では、
試行の識別子と、
実際に成立したEvidence成果物を区別する。

`evidence_id` と `implementation_id` は、
UC-08の試行を識別するため、
失敗時も保持する。

したがって、

`evidence_id: UUID`
`implementation_id: UUID`

は非Optionalのままとする。

一方、

`implementation_evidence`
`evidence_path`
`git_diff_path`
`status`

は、実際に成立した事実だけを保持する。

型は以下とする。

`implementation_evidence: ImplementationEvidence | None`
`evidence_path: Path | None`
`git_diff_path: Path | None`
`status: str | None`

`implementation_evidence=None` は、
Implementation Evidenceの構築まで到達していないことを表す。

`evidence_path=None` は、
Evidence JSONが永続化されていないことを表す。

`git_diff_path=None` は、
Git Diffが永続化されていないことを表す。

`status=None` は、
Evidence自体が成立しておらず、
Evidence収集状態を確定できないことを表す。

Evidenceが成立した場合の `status` は、
既存Decisionに従い、
`"COLLECTED"` または `"PARTIAL"` とする。

UC-08 failureを表すために、
Evidence statusへ `"ERROR"` を追加しない。

`success=False` の場合も、
実際に成立した成果物だけをOutputへ保持し、
存在しないPathやEvidence statusを生成・推測してはならない。

UC-08の失敗理由は `error_message` に保持する。

これらの `None` そのものから、
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。
