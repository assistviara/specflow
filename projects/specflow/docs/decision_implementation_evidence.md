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


## Decision 35 — Basis acquisition errors in final Evidence

**Human Decision #60**

`ImplementationEvidenceBasisBuilder` が返すBasis取得エラーは、
最終 `ImplementationEvidence` の
`EvidenceVerification.errors` に統合する。

V1では、Basis取得エラー専用のトップレベルブロックや
`EvidenceBasis.errors` は追加しない。

`EvidenceBasisBuildResult.missing_evidence` は、
Reviewに必要なEvidenceのうち何が取得できなかったかを表す。

`EvidenceBasisBuildResult.errors` は、
Evidence取得・検証処理で実際に発生した失敗事実を表す。

UC-08はBasis取得エラーを
`EvidenceVerification.errors` に統合する。

`TestState.errors` 等の他のVerification Errorと併存する場合は、
双方を保持する。

同一Errorが複数経路から得られた場合は、
重複のみ除去する。

`missing_evidence` と `verification.errors` は
別の意味を持つため、一方を他方の代用にはしない。

Specification hashを取得できなかった場合の例:

    missing_evidence:
      - specification hash unavailable

    verification.errors:
      - failed to read specification for hashing

Basis取得エラーから、
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断してはならない。

このDecisionのためだけに8番目のEvidence blockは追加しない。
既存の7-block V1 Evidence structureを維持する。


## Decision 36 — Branch and base commit mismatch

**Human Decision #61**

UC-08 Inputで指定された期待Repository Stateと、
実際に取得したRepository Stateの
branch / base commitが一致するかを機械的に比較する。

比較対象は以下とする。

- expected branch:
  `CollectImplementationEvidenceInput.implementation_branch`
- actual branch:
  `RepositoryState.branch`
- expected base commit:
  `CollectImplementationEvidenceInput.base_commit`
- actual base commit:
  `RepositoryState.base_commit`

branchまたはbase commitが一致しない場合は、
`inconsistencies` に記録する。

これはEvidence不足ではなく、
取得済みの2つの事実が同一対象について
食い違っている状態であるため、
`missing_evidence` には記録しない。

また、Approved Scopeからの変更逸脱そのものではないため、
`deviations` にも分類しない。

記録例:

    implementation branch mismatch:
      expected=developer
      actual=main

    base commit mismatch:
      expected=abc123
      actual=def456

branch / base commit mismatchのみを理由として、
`human_approval_required` を自動設定しない。

Phase 4は、この不一致から
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

これらの意味評価はPhase 5へ委ねる。


## Decision 37 — Reported and actual test command comparison

**Human Decision #62**

Phase 4は、
Codex Runner Reportである `ImplementationResult` と、
独立取得した実際の `TestState` のうち、
機械的に対応関係を確認できるTest Commandを比較する。

比較対象は以下とする。

- reported:
  `ImplementationResult.executed_commands`
- actual:
  `TestState.test_commands`

`ImplementationResult.executed_commands` は、
1行ごとのCommandとして扱う。

各行について前後の空白を除去し、
空行は無視する。

Phase 4は、
reported commandsとactual test commandsの
集合的な対応を機械的に比較する。

reported側に存在するTest Commandが
actual側に存在しない場合、
`inconsistencies` に記録する。

actual側に存在するTest Commandが
reported側に存在しない場合も、
`inconsistencies` に記録する。

V1では、
`ImplementationResult.test_execution_status`
および `ImplementationResult.test_result` と、

- `TestState.initial_test_status / result`
- `TestState.target_test_status / result`
- `TestState.full_test_status / result`

との意味的な対応関係を推測して比較しない。

Phase 3側は単一の総括値であり、
Phase 4側はinitial / target / fullの
複数段階Evidenceであるため、
Specificationで一意に対応関係が定義されていない状態では
Phase 4が対応関係を補完してはならない。

同様に、
`ImplementationResult.test_execution_error` と
`TestState.errors` の意味的同一性も推測しない。

これらはそれぞれ独立したEvidenceとして保持する。

Test Commandの不一致は
`inconsistencies` として記録する。

この不一致のみを理由として、
`human_approval_required` を自動設定しない。

Phase 4は、この不一致から
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。


## Decision 38 — V1 test command comparison direction

**Human Decision #63**

Decision 37をV1で実装可能な機械比較として補足する。

`ImplementationResult.executed_commands` には、
Test Command以外のCommandも含まれ得る。

例:

- `git status`
- `python script.py`
- `cat file.txt`
- Test Command

Phase 4は、
Command文字列の内容から、
どのCommandがTest Commandであるかを意味的に推測しない。

特に、
`pytest` 等の特定文字列を含むかどうかによって
Test Commandを判定するルールをV1では導入しない。

したがってV1では、
Test Command比較を次の一方向に限定する。

- actual:
  `TestState.test_commands`
- reported:
  `ImplementationResult.executed_commands` の各非空行

各actual Test Commandについて、
前後空白を除去した完全一致Commandが
reported commandsに存在するかを確認する。

actual Test Commandがreported commandsに存在しない場合、
`inconsistencies` に記録する。

一方、
reported commandsに存在するCommandが
actual `TestState.test_commands` に存在しないことだけでは、
`inconsistencies` としない。

これは、
reported commandがTest Commandではない可能性があり、
Phase 4がその意味を推測してはならないためである。

Decision 37で定義した
reported側からactual側への比較については、
V1では構造化されたreported Test Commandsが存在しないため、
実施しない。

将来、
Phase 3がreported Test Commandsを
独立した構造化フィールドとして提供する場合には、
双方向比較を再検討できる。

この一方向比較の不一致のみを理由として、
`human_approval_required` を自動設定しない。

Phase 4は、
この不一致からImplementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。


## Decision 39 — Evidence Verification command sources

**Human Decision #64**

`EvidenceVerification.commands` と
`EvidenceVerification.test_commands` のSourceを明確に分離する。

### commands

`EvidenceVerification.commands` は、
Phase 3 Codex Runner Reportである
`ImplementationResult.executed_commands` をSourceとする。

`executed_commands` は1行ごとのCommandとして扱う。

各行について前後の空白を除去し、
空行を無視して、
順序を保持したtupleとして格納する。

Phase 4はCommandの意味を解釈せず、
Test Commandか否かによって分類しない。

### test_commands

`EvidenceVerification.test_commands` は、
Phase 4で独立取得した
`TestState.test_commands` をSourceとする。

したがって、

- `commands`
  = Codex Runner Report由来
- `test_commands`
  = actual Test State由来

として区別する。

両者を混同または統合しない。

### Implementation Result unavailable

`ImplementationResult` が取得不能または確認不能の場合、
`EvidenceVerification.commands` は空tuple `()` とする。

この場合、
Commandが存在しなかったと推測するのではなく、
既存ルールに従って

`implementation result unavailable`

を `missing_evidence` に記録する。

`commands=()` だけを理由として、
追加のmissing evidenceを生成しない。

Phase 4は、
Command内容からImplementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。


## Decision 40 — Unfinished items source and normalization

**Human Decision #65**

`EvidenceDeviations.unfinished_items` のSourceは、
Phase 3 Codex Runner Reportである
`ImplementationResult.incomplete_items` とする。

`incomplete_items` は1行ごとの項目として扱う。

各行について前後の空白を除去し、
空行を無視して、
順序を保持したtupleとして格納する。

### NONE normalization

Phase 3で明示的に使用される `NONE` は、
未完了項目が存在しないことを表す。

したがって、

`ImplementationResult.incomplete_items == "NONE"`

の場合、

`EvidenceDeviations.unfinished_items`

は空tuple `()` とする。

`NONE` を `("NONE",)` として
unfinished itemそのものとして保持しない。

### Implementation Result unavailable

`ImplementationResult` が取得不能または確認不能の場合も、
`EvidenceDeviations.unfinished_items` は空tuple `()` とする。

ただし、この空tupleは
「未完了項目が存在しないことを確認した」
という意味ではない。

取得不能であることは既存ルールに従って、

`implementation result unavailable`

を `missing_evidence` に記録することで区別する。

Phase 4は、
`incomplete_items` の記載内容から
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。


## Decision 41 — Verification errors and warnings sources

**Human Decision #66**

`EvidenceVerification.errors` と
`EvidenceVerification.warnings` は、
Phase 4で独立取得・検証したEvidence側の事実を保持する。

Codex Runner Reportの自己申告とは混同しない。

### Verification errors

`EvidenceVerification.errors` のSourceは、

1. `ImplementationEvidenceBasisBuilder.errors`
2. `TestState.errors`

とする。

両Sourceをこの順序で結合し、
同一文字列が複数存在する場合は、
最初の出現順を保持して重複を除去する。

### Verification warnings

`EvidenceVerification.warnings` のSourceは、

`TestState.warnings`

とする。

同一文字列が複数存在する場合は、
最初の出現順を保持して重複を除去する。

### Codex Runner Reportとの分離

以下のPhase 3 Codex Runner Report由来の値は、

- `ImplementationResult.errors`
- `ImplementationResult.warnings`
- `ImplementationResult.test_execution_error`

`EvidenceVerification.errors` または
`EvidenceVerification.warnings` へ統合しない。

これらは、

`EvidenceCodexSummary.implementation_result`

の中にRunner Reportの自己申告としてそのまま保持する。

したがってV1では、

- `EvidenceVerification.errors / warnings`
  = Phase 4で独立取得・検証したEvidence
- `EvidenceCodexSummary.implementation_result`
  = Phase 3 Codex Runner Reportの自己申告

として区別する。

Phase 4は両者の内容から
Implementationの適合性、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。


## Decision 42 — Codex Prompt correspondence by traceability

**Human Decision #67**

V1のPhase 4では、
Codex PromptとSpecification /
Human-approved Implementation Planとの対応を、
意味的な再評価ではなくtraceabilityによって確認する。

### Phase 4 responsibility

Phase 4は、

- Specification
- Human-approved Implementation Plan
- 実際にCodexへ渡されたPrompt

を、それぞれ識別可能かつ追跡可能なEvidenceとして保持する。

V1では、既存のBasis情報である、

- Specification path / hash / Approval ID
- Implementation Plan path / hash / Approval ID
- Codex Prompt path / hash

を用いてtraceabilityを確保する。

Codex Prompt hashは既存Decisionに従い、
Phase 4へ入力された実際のPrompt bodyを
UTF-8でSHA-256した値とする。

### No semantic re-evaluation in Phase 4

Phase 4自身はAIを追加実行して、

「Codex PromptがSpecificationまたは
Approved Implementation Planを
意味的に正しく反映しているか」

を判定しない。

Phase 4はEvidenceの収集・識別・固定を担当し、
意味的適合性のReviewを担当しない。

### Missing traceability evidence

必要なtraceability Evidenceを取得または確認できない場合、
Phase 4は他のEvidenceから推測して補完しない。

既存ルールに従って
該当項目を `missing_evidence` に記録し、
Evidenceは `PARTIAL` になり得る。

### Phase 5 responsibility

Codex Promptの内容が
Specificationおよび
Human-approved Implementation Planを
意味的に適切に反映しているかの評価は、
Phase 5 Reviewの責務とする。

したがってV1では、

Phase 4
= Prompt correspondenceのtraceability確保

Phase 5
= Prompt correspondenceの意味的評価

として責務を分離する。


## Decision 43 — Git Diff acquisition and persistence failure

**Human Decision #68**

V1では、
Git Diffの取得不能と、
取得済みGit Diffの永続化失敗を区別する。

### Git Diff unavailable

`RepositoryState.git_diff` を取得または確認できない場合は、
Evidence acquisition failureとして扱う。

この場合、

- 該当する取得不能を `missing_evidence` に記録する
- `EvidenceChanges.git_diff_path` は `None` とする
- Evidenceは既存のstatus ruleに従って `PARTIAL` になり得る

Phase 4は、
他のRepository情報やCodex Runner Reportから
Git Diffの内容を推測して補完しない。

### Git Diff persistence failure

Git Diff自体は取得できているが、

`ImplementationEvidenceRepository.save_diff()`

による永続化に失敗した場合は、
Evidence persistence failureとして扱う。

この場合、
UC-08は `success=False` で終了する。

保存されていないDiffについて、
架空の `git_diff_path` を生成または返却しない。

### Empty Git Diff

Git Diffを正常に取得でき、
その内容が空文字列 `""` である場合は、
取得不能とは扱わない。

空文字列は、

「Git Diffを取得した結果、差分が存在しなかった」

という取得済みEvidenceとして扱う。

したがって、
正常に取得された空のGit Diffも
`.diff` Evidenceとして保存する。

Phase 4は、
Git Diffが空であることから
Implementationの適合性、
実装未実施、
Review Result、
Correction / Reimplementation要否を判断しない。

意味評価はPhase 5へ委ねる。

### Responsibility boundary

V1では、

- Git Diff取得不能
  = Evidence acquisition failure
- 取得済みGit Diffの保存失敗
  = Evidence persistence failure / UC-08 failure
- 正常取得された空Git Diff
  = 有効な取得済みEvidence

として明確に区別する。


## Decision 44 — Implementation generation traceability

**Human Decision #69**

V1では、
`implementation_kind` と
`previous_evidence_id` の組み合わせについて、
Evidence世代関係の機械的整合性を要求する。

### INITIAL

`implementation_kind == "INITIAL"` の場合、

`previous_evidence_id`

は必ず `None` とする。

INITIAL Evidenceは、
先行するImplementation Evidenceを持たない。

### CORRECTION

`implementation_kind == "CORRECTION"` の場合、

`previous_evidence_id`

を必須とする。

指定された `previous_evidence_id` は、
既存のImplementation Evidenceを参照しなければならない。

### REIMPLEMENTATION

`implementation_kind == "REIMPLEMENTATION"` の場合も、

`previous_evidence_id`

を必須とする。

指定された `previous_evidence_id` は、
既存のImplementation Evidenceを参照しなければならない。

### Previous Evidence existence

`previous_evidence_id` が指定された場合、
UC-08は `ImplementationEvidenceRepository` を通じて、
参照先Evidenceが存在することを確認する。

参照先Evidenceが存在しない場合、
Evidence世代関係のtraceabilityを成立させられないため、
UC-08は `success=False` で終了する。

この状態を `PARTIAL` Evidenceとして補完しない。

### Self-reference

新たに発行された `evidence_id` と
`previous_evidence_id` が同一であることを許可しない。

同一である場合、
世代関係が成立しないため、
UC-08は `success=False` で終了する。

### Responsibility boundary

Phase 4は、

- `INITIAL`
- `CORRECTION`
- `REIMPLEMENTATION`

のどのkindが意味的に妥当であるかを判断しない。

Humanまたは前段Workflowによって指定された
`implementation_kind` を前提として、
Phase 4は世代関係の機械的整合性だけを確認する。

したがって、

- INITIAL + previous Evidenceあり
- CORRECTION + previous Evidenceなし
- REIMPLEMENTATION + previous Evidenceなし
- previous Evidence不存在
- current Evidenceへのself-reference

はUC-08 failureとする。

これらをImplementationの適合性、
Review Result、
Correction / Reimplementation要否の判断として扱わない。


## Decision 45 — Evidence persistence order and partial persistence failure

**Human Decision #70**

V1では、
Git Diff EvidenceとImplementation Evidence JSONの保存を
原子的Transactionとして扱わない。

Phase 4は、
実際に成立したArtifactと成立していないArtifactを区別して保持する。

### Persistence order

UC-08は、原則として次の順序で処理する。

1. `evidence_id` を発行する
2. Repository / Test / Basis等のEvidenceを収集する
3. Evidenceを機械的に比較する
4. 取得済みGit Diffがある場合は `save_diff()` で保存する
5. 返された実在するDiff pathを
   `EvidenceChanges.git_diff_path` に設定する
6. `ImplementationEvidence` を構築する
7. `ImplementationEvidenceRepository.save()` で
   JSON Evidenceを保存する

### save_diff failure

取得済みGit Diffについて、

`ImplementationEvidenceRepository.save_diff()`

が失敗した場合は、
既存Decision 43に従い、
Evidence persistence failureとして
UC-08を `success=False` で終了する。

保存されていないDiffについて、
架空の `git_diff_path` を返さない。

### JSON persistence failure after Diff persistence

`save_diff()` が成功した後に、

`ImplementationEvidenceRepository.save()`

によるJSON Evidenceの保存が失敗した場合も、
UC-08は `success=False` で終了する。

ただしV1では、
保存済み `.diff` に対する
rollback / delete / transaction処理を要求しない。

そのため、
JSON Evidenceが保存されず、
`.diff` のみが孤立Artifactとして残ることを許容する。

孤立した `.diff` が存在することを理由として、
UC-08成功とは扱わない。

### Failure output

JSON Evidence保存失敗時のOutputは、
Decision 34の
「実際に成立したArtifactだけを返す」
というルールに従う。

したがって、

- `evidence_id`
  = UC-08開始時に発行したID
- `implementation_id`
  = InputのImplementation ID
- `implementation_evidence`
  = すでに構築済みであれば、そのobject
- `git_diff_path`
  = Diffが実際に保存済みであれば、そのpath
- `evidence_path`
  = `None`
- `status`
  = Evidence objectが構築済みであれば
    その `COLLECTED` または `PARTIAL`
  = Evidence object構築前であれば `None`
- `success`
  = `False`
- `error_message`
  = JSON Evidence persistence failureの事実

とする。

Phase 4は、
孤立Artifactに対する自動cleanupやrollbackを実行しない。

### Responsibility boundary

V1では、

- Artifact persistenceの成否を正確に記録する
- 成立していないArtifactのpathを捏造しない
- 部分的に成立したArtifactを隠さない
- Persistence failureをReview Resultへ変換しない

ことを責務とする。

Transaction / rollback機構は、
V1 UC-08のCompletion Conditionには含めない。


## Decision 46 — Provider failure boundary

**Human Decision #71**

V1では、
RepositoryおよびTestの個別Evidenceを取得できない状態と、
Provider処理そのものが例外によって成立しない状態を区別する。

### State with unavailable evidence

`RepositoryStateProvider`または
`TestStateProvider`が、
取得できた事実と取得不能項目を含む
有効なStateを返した場合、
UC-08はEvidence構築を継続する。

Providerが返した

`unavailable_evidence`

は、
既存Decisionに従って
`missing_evidence`へ反映する。

`missing_evidence`が存在する場合、
Decision 27に従い、
Evidence statusを `PARTIAL` とする。

この状態は、
Evidence収集処理そのものの失敗とは扱わない。

### Provider exception

以下のProvider呼び出しが
Stateを返さず例外を送出した場合、

- `RepositoryStateProvider.get_state(base_commit)`
- `TestStateProvider.get_state()`

UC-08は、
欠損したRepositoryStateまたはTestStateを
生成、推測、または補完しない。

UC-08は通常の `Exception` を捕捉し、
`BaseException` までは捕捉しない。

Provider例外が発生した場合、
Evidence収集処理そのものが成立していないため、
UC-08は `success=False` で終了する。

Provider例外を、
`PARTIAL` Implementation Evidenceとして保存しない。

### Failure output

Provider例外は、
Evidence persistence前に発生するものとして扱う。

Outputは、実際に成立した情報だけを返す。

- `evidence_id`
  - UC-08開始時に発行済みのID
- `implementation_id`
  - InputのImplementation ID
- `implementation_evidence`
  - `None`
- `evidence_path`
  - `None`
- `git_diff_path`
  - `None`
- `status`
  - `None`
- `missing_evidence`
  - `()`
- `inconsistencies`
  - `()`
- `human_approval_required`
  - `()`
- `success`
  - `False`
- `error_message`
  - 失敗したProviderと例外内容を識別可能な文字列

有効なStateが成立していないため、
Provider例外を特定の
`missing_evidence`項目へ変換しない。

### Responsibility boundary

想定される個別Evidence取得不能を、
有効なStateと `unavailable_evidence` によって
構造化する責務はProviderに置く。

UC-08は、
Provider例外から空または仮のStateを生成しない。

Provider例外を、

- Implementationの不適合
- Review Result
- CorrectionまたはReimplementationの要否
- Human Approvalの代替判断

へ変換しない。

Technical Retryは、
V1 UC-08の責務へ追加しない。

したがってV1では、

- Evidenceの一部が取得不能であり、
  Providerが有効なStateを返せる場合
  → `PARTIAL` Evidence
- Provider処理そのものが成立せず、
  Stateを返せない場合
  → UC-08 failure

とする。


## Decision 47 — Pre-Evidence persistence failure diagnostics

**Human Decision #72**

V1では、
取得済みGit Diffの永続化に失敗した場合も、
永続化処理より前に実際に成立した
機械的比較結果を失わずOutputへ保持する。

### Git Diff persistence failure

Git Diff自体を取得できているが、

`ImplementationEvidenceRepository.save_diff()`

が例外によって失敗した場合、
Decision 43に従い、
UC-08は `success=False` で終了する。

保存されていないGit Diffについて、
架空の `git_diff_path` を生成または返してはならない。

### Artifact fields

`save_diff()` は
Implementation Evidence object構築前に実行される。

したがって、
`save_diff()`失敗時は次の値とする。

- `implementation_evidence`
  - `None`
- `evidence_path`
  - `None`
- `git_diff_path`
  - `None`
- `status`
  - `None`

この状態を、
Implementation Evidenceが成立した状態として扱わない。

### Established diagnostics

`save_diff()`実行前に、
Evidence収集および機械的比較が完了している場合、
その時点で実際に確定した以下の診断情報を
Outputへ保持する。

- `missing_evidence`
- `inconsistencies`
- `human_approval_required`

これらの値を、
永続化失敗を理由として空値へ置き換えたり、
隠したりしてはならない。

一方、
比較処理そのものが完了していない場合は、
未成立の比較結果を生成または推測してはならない。

### Failure output

取得済みGit Diffの
`save_diff()`失敗時は、
少なくとも以下を返す。

- `evidence_id`
  - UC-08開始時に発行したID
- `implementation_id`
  - InputのImplementation ID
- `implementation_evidence`
  - `None`
- `evidence_path`
  - `None`
- `git_diff_path`
  - `None`
- `status`
  - `None`
- `missing_evidence`
  - 比較完了時点で確定済みの値
- `inconsistencies`
  - 比較完了時点で確定済みの値
- `human_approval_required`
  - 比較完了時点で確定済みの値
- `success`
  - `False`
- `error_message`
  - `Git Diff persistence failed: <例外内容>`

### Responsibility boundary

`save_diff()`失敗前に成立した診断情報を返すことを、

- Implementation Evidenceの成立
- Evidence statusの確定
- Persistence成功
- Phase 5 Reviewへの進行可能
- Implementationの適合性
- Review Result

の意味として扱わない。

V1では、
成立済みの診断情報と、
成立していないEvidence Artifactを
明確に区別してOutputへ保持する。


## Decision 48 — Generation validation and previous Evidence lookup failure

**Human Decision #73**

V1では、
Implementation Evidenceの世代関係を成立させるため、
`implementation_kind` の有効性と
previous Evidence参照可否を、
Evidence収集および永続化より前に検証する。

### Valid implementation kinds

V1で有効な `implementation_kind` は、
以下の3種類に限定する。

- `INITIAL`
- `CORRECTION`
- `REIMPLEMENTATION`

これら以外の値が指定された場合、
Evidence世代関係を成立させられないため、
UC-08は `success=False` で終了する。

この検証は、少なくとも以下より前に行う。

- previous Evidenceの存在確認
- RepositoryStateProviderの呼び出し
- TestStateProviderの呼び出し
- Git Diffの保存
- Implementation Evidenceの構築
- Evidence JSONの保存

### Invalid kind failure output

不正な `implementation_kind` の場合、
実際に成立した情報だけをOutputへ返す。

- `evidence_id`
  - UC-08開始時に発行したID
- `implementation_id`
  - InputのImplementation ID
- `implementation_evidence`
  - `None`
- `evidence_path`
  - `None`
- `git_diff_path`
  - `None`
- `status`
  - `None`
- `missing_evidence`
  - `()`
- `inconsistencies`
  - `()`
- `human_approval_required`
  - `()`
- `success`
  - `False`
- `error_message`
  - `invalid implementation_kind: <入力値>`

不正なkindを、
既知のkindへ推測または変換してはならない。

### Previous Evidence lookup failure

`CORRECTION`または`REIMPLEMENTATION`で、
指定された `previous_evidence_id` の存在を、

`ImplementationEvidenceRepository.exists()`

によって確認する。

`exists()` が `False` を返した場合は、
Decision 44に従い、
previous Evidence不存在として
UC-08を `success=False` で終了する。

一方、
`exists()` が通常の `Exception` を送出した場合は、
previous Evidenceの存在・不存在を確認できていない状態として扱う。

この場合、
previous Evidenceが存在しないと推測せず、
UC-08を `success=False` で終了する。

UC-08は通常の `Exception` を捕捉するが、
`BaseException` までは捕捉しない。

### Lookup failure output

Previous Evidence lookup failure時は、
以下を返す。

- `evidence_id`
  - UC-08開始時に発行したID
- `implementation_id`
  - InputのImplementation ID
- `implementation_evidence`
  - `None`
- `evidence_path`
  - `None`
- `git_diff_path`
  - `None`
- `status`
  - `None`
- `missing_evidence`
  - `()`
- `inconsistencies`
  - `()`
- `human_approval_required`
  - `()`
- `success`
  - `False`
- `error_message`
  - `Previous Evidence lookup failed: <例外内容>`

### Responsibility boundary

不正な `implementation_kind` および
Previous Evidence lookup failureを、

- `PARTIAL` Implementation Evidence
- Implementationの不適合
- Review Result
- CorrectionまたはReimplementationの要否
- Human Approvalの代替判断

へ変換しない。

これらは、
Evidence収集開始前の
入力およびtraceability検証失敗として扱う。

UC-08は、
これらの失敗時に
Repository／Testの実状態取得、
Diff保存、
Evidence構築、
JSON保存を実行しない。
