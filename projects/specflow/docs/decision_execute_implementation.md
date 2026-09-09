# Decisions

## DEC-007 UC-06 Execute Implementation設計Decision

- 決定日：2026-09-09
- 決定者：たけしゃん
- 対象UseCase：UC-06 Execute Implementation
- 根拠Specification：application_layer_specification_v0.2.0-draft.md
- 根拠Implementation Plan：application_layer_implementation_plan_v0.1.0-draft.md
- 判定：APPROVED

### Decisionの目的

UC-06の実装にあたり、
Specificationおよび承認済みImplementation Planから
一意に決定できない実装設計事項について、
Human Decisionとして以下を確定する。

本DecisionはSpecificationまたはImplementation Planの
要求を変更・拡張するものではない。

---

### Decision 1：Codex Implementation Resultの構造化

Codex Runnerの実行結果は、
規定されたSection形式のtextとして受け取る。

Application LayerにImplementation Result Parserを配置し、
Codex Runnerから返されたraw textを
構造化されたImplementation Resultへ変換する。

Codex RunnerおよびParserは、
State Transition、Technical Retry、
Implementation Failure、Correction、
Critical Change等のWorkflow判断を行わない。

これらの判断はExecuteImplementationUseCaseが担当する。

---

### Decision 2：Implementation Resultの必須10 Section

Codex Runnerの実行結果は、
以下の10 Sectionを必須とする。

1. Implementation Summary
2. Changed Files
3. Executed Commands
4. Test Execution Status
5. Test Result
6. Test Execution Error
7. Errors
8. Warnings
9. Incomplete Items
10. Human Approval Required

Parserは少なくとも、
必須Sectionの存在、順序、および必要な値の妥当性を
決定論的に検証する。

---

### Decision 3：Test関連の固定値

Test Execution Statusは、
以下の値のみを使用する。

- COMPLETED
- ERROR
- NOT_RUN

Test Resultは、
以下の値のみを使用する。

- PASS
- FAIL
- NONE

Parserはこれらを固定値として検証する。

Test ResultがFAILであることのみを理由として、
Technical Error、
implementation_failed、
または自動Correctionとして扱ってはならない。

---

### Decision 4：Technical Retryの判断境界

Technical Error発生時、
CodexはTechnical Retryに関する候補情報として、
少なくとも以下に相当する情報を報告できる。

- technical_retry_safe
- technical_retry_operation

これらはCodexによる候補情報であり、
Technical Retryを実行する最終判断ではない。

Application LayerはSpecification 15.22の条件に基づき、
Technical Retryとして安全に処理可能かを判断する。

Artifact、Source Code、Test Code、
Specification、Approved Implementation Plan、
Human Approval Scope等の変更が必要な処理は
Technical Retryとして扱わない。

条件を確認できない場合、
Application Layerは自動Technical Retryを許可しない。

---

### Decision 5：Critical Changeの検出と引き渡し

既存10 Sectionの
Human Approval Requiredを、
承認済みScopeを超える変更または
Critical Change候補の報告経路として使用する。

Codex RunnerはCritical ChangeのWorkflow判断を行わない。

Human Approval Requiredに
実質的な承認要求が報告された場合、
Application LayerはFail Safe側で処理し、
implementation_completedへ遷移させない。

Application LayerはImplementationを停止し、
critical_approval_pendingへ遷移させ、
UC-07へ処理を渡す。

Version 1では、
自然言語によるScope適合性を完全自動判定する
Semantic Validatorは追加しない。

---

### Decision 6：CodexRunner Integration

既存CodexRunnerの以下の契約は変更しない。

run(
    *,
    prompt: str,
    working_directory: Path,
) -> str

UC-06では、
ExecuteImplementationUseCaseとCodexRunnerの間に
Codex Implementation Adapterを配置する。

AdapterはCodex PromptおよびWorking Directoryを
既存CodexRunnerへ渡し、
Codex Runnerから返されたraw textを
Application Layerへ返す。

AdapterおよびCodexRunnerには、
Parser、Approval判断、State Transition、
Technical Retry判断、Critical Change判断等の
Workflow責務を持たせない。

---

### Decision 7：UC-06 Input / Output DTO契約

ExecuteImplementationInputは、
以下のフィールドを基本契約とする。

- specification_path: Path
- specification_approval_id: str
- implementation_plan_path: Path
- implementation_plan_approval_id: str
- codex_prompt: str
- codex_prompt_specification_path: Path
- codex_prompt_implementation_plan_path: Path
- implementation_branch: str
- base_commit: str
- working_directory: Path
- state_file: Path
- state_history_dir: Path

ExecuteImplementationOutputは、
以下のフィールドを基本契約とする。

- success: bool
- implementation_result: ImplementationResult | None
- specification_path: Path
- implementation_plan_path: Path
- implementation_branch: str
- base_commit: str
- specification_approval_validation_result: ApprovalValidationResult
- implementation_plan_approval_validation_result: ApprovalValidationResult
- current_state: str
- technical_retry_required: bool
- critical_change_required: bool
- stop_reason: str | None = None
- error_message: str | None = None

ImplementationResultはParserが生成する構造化結果とし、
少なくとも10 Sectionに対応する情報に加え、
Technical Retry候補情報を保持できるものとする。

DTO自身はWorkflow判断を行わない。

---

### Decision 8：Version 1のTechnical Retry上限

Version 1では、
Application LayerがSpecification 15.22の
Technical Retry条件を満たすと確認できた場合、
同一Technical Operationの自動Retryを最大1回許可する。

1回のRetryで復旧した場合は通常処理を継続する。

Retry後もTechnical Errorが継続する場合は、
追加の自動Retryを行わず、
implementation_failedへ遷移して
Human判断へ処理を返す。

最大1回という制限は、
Technical Retryそのものの一般原則ではなく、
Version 1 MVPの実装上の上限とする。

---

### Decision 9：Test Applicabilityの構造化

10 Section構成は変更しない。

Implementation Summary内に、
以下の固定メタデータのいずれかを必須とする。

TEST_REQUIRED: YES

または

TEST_REQUIRED: NO

Parserはこの値を解析し、
test_required: boolとして構造化する。

TEST_REQUIRED: NOの場合のみ、
Test Execution Status = NOT_RUNを
正常完了候補として認める。

TEST_REQUIRED: YESであるにもかかわらず
Test Execution Status = NOT_RUNの場合は、
implementation_completedへ遷移してはならない。

---

### Decision 10：UC-06 Completion判定

Test Execution Status = COMPLETEDであり、
Test Result = PASSの場合は正常完了候補とする。

Test Execution Status = COMPLETEDであり、
Test Result = FAILの場合も、
FAILであることのみを理由として
Technical Errorまたはimplementation_failedとはせず、
正常なTest Resultとして後続工程へ渡す。

Test Execution Status = ERRORの場合は、
Technical ErrorとしてTechnical Retry判定へ進む。

Test Execution Status = NOT_RUNの場合は、
TEST_REQUIRED: NOの場合のみ正常完了候補とする。

Human Approval Requiredに実質的内容がある場合は、
implementation_completedへ遷移せず、
critical_approval_pendingへ遷移する。

Incomplete Itemsに実質的内容がある場合は、
implementation_completedへ遷移しない。

Errorsに実質的内容がある場合は、
implementation_completedへ遷移しない。

Warningsのみが存在することは、
それだけではimplementation_completedへの遷移を妨げない。

UC-06のsuccessは、
Test ResultがPASSであることそのものではなく、
UC-06のImplementation実行工程が
SpecificationおよびApproved Scopeに従って
正常に完了したことを表す。

---

### 設計原則

責務分離は以下とする。

Human
  ↓
Specification / Approved Implementation Plan
  ↓
Application Layer
  - Approval Validation
  - Input / Prompt Correspondence Validation
  - Workflow / State Control
  - Technical Retry判断
  - Critical Change Gate
  ↓
Codex Implementation Adapter
  ↓
CodexRunner
  ↓
CommandExecutor / Codex CLI
  ↓
raw Implementation Result
  ↓
Implementation Result Parser
  ↓
Application Layer
  ↓
State Transition / downstream workflow

CodexはImplementationおよびTestを実行し、
実行結果と必要な候補情報を報告する。

Codex自身に、
Workflow State、
Technical Retry、
Implementation Failure、
Correction、
Critical Change、
Human Approvalの最終決定権を与えない。

---

### Decision 11：Technical Retry Metadata形式

Technical Retryに関する候補情報は、
既存10 Sectionのうち
Test Execution Error Section内に
固定Metadataとして記録する。

Technical Error時に
安全なTechnical Retry候補である場合は、
以下の形式を使用する。

TECHNICAL_RETRY_SAFE: YES
TECHNICAL_RETRY_OPERATION: <operation>

Technical Retryとして安全か判断できない場合は、
以下の形式を使用する。

TECHNICAL_RETRY_SAFE: UNKNOWN
TECHNICAL_RETRY_OPERATION: NONE

Technical Retry対象ではない場合は、
以下の形式を使用する。

TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE

ParserはTECHNICAL_RETRY_SAFEを
以下のように構造化する。

- YES → True
- NO → False
- UNKNOWN → None

TECHNICAL_RETRY_OPERATIONは、
具体的なOperationが存在する場合はその文字列を保持し、
NONEの場合はNoneとして扱う。

このMetadataはCodexによる候補情報であり、
Technical Retry実行の最終判断ではない。

Technical Retryの実行可否は、
ExecuteImplementationUseCaseが
Specification 15.22およびDEC-007 Decision 4に基づいて判断する。

---

### Decision 12：Technical RetryのV1安全確認

Technical Retryに関するCodexのMetadataは、
Retry実行の候補情報として扱い、
それだけを根拠にTechnical Retryを許可しない。

V1では、
ExecuteImplementationUseCaseが
以下の条件をすべて確認できた場合に限り、
Technical Retryを最大1回許可する。

- TECHNICAL_RETRY_SAFEがYESである
- TECHNICAL_RETRY_OPERATIONが具体的に存在する
- Codex ResultのChanged FilesがNONEである
- Applicationが実際のGit working treeを確認し、
  artifact変更がないことを確認できる

CodexはTechnical Retryの候補を報告するが、
Technical Retry実行の最終決定は行わない。

Applicationが実際のGit状態を確認できない場合、
またはartifact変更の有無を確認できない場合は、
Technical Retryとして自動継続しない。

Technical Retryは最大1回とし、
そのRetry自体がRunner Error、
Parser Error、
Test Execution Error等で完了できなかった場合、
追加のTechnical Retryは行わない。

この境界により、

Codex = Technical Retry候補の報告者
Application = 実状態を確認する決定者

という責任分離を維持する。

これはSpecification 15.22の
Technical Retry条件をV1で実行可能な形に具体化するものであり、
Codexの自己申告のみでWorkflowを進行させない。

---

# Closing

本Decisionにより、
UC-06 Execute Implementationの実装に必要な
上記設計事項をHuman Decisionとして承認する。

Implementationは、
Specification、承認済みImplementation Plan、
および本Decisionの範囲内でTDDにより進める。
