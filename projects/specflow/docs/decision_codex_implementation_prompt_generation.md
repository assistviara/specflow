# Decisions

## DEC-006 UC-05 Codex Implementation Prompt Generation設計Decision

- 決定日：2026-09-09
- 決定者：たけしゃん
- 対象UseCase：UC-05 Generate Codex Implementation Prompt
- 根拠Specification：application_layer_specification_v0.2.0-draft.md
- 根拠Implementation Plan：application_layer_implementation_plan_v0.1.0-draft.md
- 判定：APPROVED

### Decisionの目的

UC-05の実装にあたり、
Specificationおよび承認済みImplementation Planから
一意に決定できない実装設計事項について、
Human Decisionとして以下を確定する。

本DecisionはSpecificationまたはImplementation Planの
要求を変更・拡張するものではない。

---

### Decision 1：Codex Implementation Promptの構造検証

Codex Implementation PromptのAI生成結果は、
以下の8 Sectionを必須とする。

1. Implementation Scope
2. Allowed Changes
3. Forbidden Changes
4. TDD Requirements
5. Completion Conditions
6. Stop Conditions
7. Required Execution Result Reporting
8. Human Approval Required Conditions

Application LayerのParserは、生成結果について以下を
決定論的に検証する。

- 8つの必須Sectionがすべて存在すること
- Sectionが定められた順序で存在すること
- 各Sectionが空でないこと

検証に失敗したPromptはImplementationに使用可能とは扱わず、
implementation_readyへ遷移してはならない。

---

### Decision 2：Approval Recordの指定方法

GenerateCodexPromptInputは、
SpecificationおよびImplementation Planについて、
それぞれ使用するApproval Recordを明示するため、
以下のApproval IDを保持する。

- specification_approval_id: str
- implementation_plan_approval_id: str

UC-05は既存のApprovalRecordRepository.get()を使用して
指定されたApproval Recordを取得し、
現在のArtifactに対してApproval Validationを実行する。

RepositoryにApproval Recordの検索機能や
「最新承認」を自動選択する機能は追加しない。

Approval RepositoryはDTOには含めず、
UseCaseの依存として保持する。

---

### Decision 3：CodexPromptGeneratorの配置と責務

core/codex_prompt_generator.pyを新設する。

CodexPromptGeneratorは、
既存のPlanPromptGeneratorと同じ設計パターンを基本とする。

責務は以下に限定する。

- 必要な文書の読み込み
- Codex Implementation Prompt生成に必要なContextの構築
- Prompt BuilderへのTemplateとContextの引き渡し
- PromptResultの返却

以下の責務はCodexPromptGeneratorに持たせない。

- Approval Validation
- State Transition
- AI Runnerの実行制御
- 8 Sectionの構造検証
- Promptの安全性・使用可否の最終判定
- implementation_readyへの遷移判断

これらはApplication LayerのUseCaseが担当する。

---

### Decision 4：UC-05 Input / Output DTO契約

GenerateCodexPromptInputは、
以下のフィールドを基本契約とする。

- specification_path: Path
- specification_approval_id: str
- implementation_plan_path: Path
- implementation_plan_approval_id: str
- implementation_target_path: Path
- tdd_rules: str
- completion_conditions: str
- stop_conditions: str
- execution_result_reporting_requirements: str
- template_path: Path
- state_file: Path
- state_history_dir: Path

GenerateCodexPromptOutputは、
以下のフィールドを基本契約とする。

- success: bool
- codex_prompt: str | None
- specification_path: Path
- implementation_plan_path: Path
- specification_approval_validation_result: ApprovalValidationResult
- implementation_plan_approval_validation_result: ApprovalValidationResult
- prompt_usable: bool
- current_state: str
- stop_reason: str | None = None
- error_message: str | None = None

successはUC-05の処理全体が正常に完了したかを表す。

prompt_usableは、
生成されたCodex Implementation Promptが
必須構造の検証を通過し、
Implementationへ渡すための最低条件を満たしたかを表す。

Approval Repository、AI Service、Prompt Generator等の
実行依存オブジェクトはDTOに含めない。

Allowed Changes、Forbidden Changes、
Human Approval Required Conditions等については、
承認済みSpecificationおよびImplementation Planを基に
Codex Prompt Generation Roleが生成する対象とし、
独立したInput DTO項目として重複定義しない。

---

### 設計原則

責務分離は以下とする。

Human
  ↓
Specification / Approved Implementation Plan
  ↓
Application Layer
  - Approval Validation
  - Workflow / State Control
  - Safety Gate
  ↓
CodexPromptGenerator
  ↓
PromptBuilder
  ↓
AI
  ↓
Application Parser
  ↓
Validated Codex Implementation Prompt

AIはCodex Implementation Promptの内容を生成するが、
そのPromptをImplementationへ進めてよいかを
AI自身が決定してはならない。

---

# Closing

本Decisionにより、
UC-05 Generate Codex Implementation Promptの実装に必要な
上記設計事項をHuman Decisionとして承認する。

Implementationは、
Specification、承認済みImplementation Plan、
および本Decisionの範囲内でTDDにより進める。
