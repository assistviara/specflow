# Application Layer Implementation Plan

Version: 0.1.0-draft  
Status: Draft / Human Approval Pending

## 1. Purpose

本Implementation Planは、
`application_layer_specification_v0.2.0-draft.md`
で定義されたApplication Layerの要求および設計決定を、
SpecFlow Version 1 MVPとして実装するための実装計画を定める。

本Planでは、Application Layer Specificationを実装上の基準とし、
以下を明確にする。

- 実装を進めるPhaseとその順序
- 各Phaseで実装する責務およびComponent
- Component間の依存関係
- 各Phaseで必要となるTestおよび検証
- 各PhaseのCompletion Conditions
- 後続Phaseへ進むための条件

本Planは、新たな要求または仕様を定義することを目的としない。

Implementation中に、
Application Layer Specificationから一意に決定できない事項、
Specificationとの矛盾、
またはHumanによる判断を必要とする事項が確認された場合、
実装者またはAIが独自に補完してはならない。

その場合は実装を停止し、
必要に応じてSpecificationまたはImplementation Planの
確認・修正・Human Approvalへ戻る。

本Planに基づく実装は、
Humanによって有効に承認されたImplementation Planを
実装根拠として開始する。

## 2. Implementation Principles

Application Layerの実装では、
Application Layer SpecificationおよびSpecFlow Constitutionに従い、
以下の原則を適用する。

### 2.1 Specification Fidelity

実装は、Humanによって承認されたSpecificationおよび
Implementation Planに忠実に行う。

実装上の都合を理由として、
Specificationに定義されていない要求、責務、状態遷移、
または自動判断を追加してはならない。

Specificationから一意に決定できない事項については、
実装者またはAIが推測によって補完せず、
必要に応じてHumanによる確認へ戻る。

### 2.2 Dependency Direction

Application Layerは、
`core`の外側に独立したPython Packageとして配置する。

依存方向は、原則として以下を維持する。

```text
UI / Interface
      ↓
Application
      ↓
Core
```

Application LayerはCoreを利用できるが、
CoreはApplication Layerへ依存してはならない。

Infrastructure / Adapterの具体実装を利用する場合も、
内側のLayerで定義された抽象または契約を通じて利用し、
Application LayerまたはCoreが具体的な永続化方式や
外部実装へ直接依存する構造を避ける。

### 2.3 Human Approval Boundary

Human Approvalを必要とする判断は、
Humanのみが行う。

Application Layer、Core Service、AI Runner、
RepositoryまたはAdapterが、
Human Approvalを推定、補完、生成または代替してはならない。

Application Layerは、
Human Approvalが必要となる工程を制御し、
Humanによる判断結果の記録、検証および
後続工程への進行可否を制御する。

### 2.4 State and Evidence Separation

Current State、State Transition History、
Human Approval Record、およびImplementation Evidenceは、
それぞれ異なる責務を持つ正式情報として扱う。

これらを単一の状態値または単一ファイルへ統合し、
責務境界を失わせてはならない。

### 2.5 Test-Driven and Verifiable Implementation

振る舞いを変更する実装については、
原則としてTDDを適用する。

各Phaseでは、
そのPhaseで追加または変更する責務に対応するTestを作成し、
対象Testおよび必要な既存Testによって
Specificationとの整合性を検証する。

Testの成功のみを実装完了の根拠とはせず、
承認された実装範囲、Source Code、Git Diff、
Test Resultおよび必要なEvidenceとの整合性を確認する。

### 2.6 Incremental Implementation

Application Layerは、
本Planで定義するPhase単位で段階的に実装する。

各Phaseでは、
そのPhaseのCompletion Conditionsを満たしたことを確認してから
後続Phaseへ進む。

後続Phaseで必要となることのみを理由として、
現在のPhaseの承認範囲を超える実装を先行して追加してはならない。

## 3. Implementation Phases

Application Layerの実装は、以下のPhaseに分けて進める。

### Phase 1 Application Layer Foundation
#### Purpose

Phase 1では、
後続のApplication Layer UseCaseを実装するために必要となる
共通基盤を構築する。

本Phaseでは、
Application LayerをCoreの外側に独立したPackageとして成立させ、
UseCase、DTO、State Management、およびHuman Approvalに関する
共通責務を配置できる構造を整える。

Phase 1の目的は、
個別UseCaseの業務フローを実装することではなく、
後続PhaseがSpecificationに定義された責務境界および依存方向を
維持したまま実装可能となるFoundationを確立することである。

#### Scope

Phase 1では、以下を実装対象とする。

* `specflow/application/` Packageの基本構造
* Application Layerで使用するInput / Output DTOの基本構造
* Current Stateの読み書きに必要な基盤
* State Transition Historyの記録に必要な基盤
* Approval Recordの構築に必要な共通責務
* Approval Recordの保存・取得に必要なRepository契約
* Approval RecordをJSONで保存・取得するInfrastructure / Adapter実装
* Approval RecordとCurrent Artifactの整合性を検証する共通責務
* 上記Foundationに対応するTest

本Phaseでは、以下を実装対象外とする。

* Implementation Plan Draft生成の実行フロー
* Codex Prompt生成
* Codex RunnerによるImplementation
* Implementation Evidenceの構築
* ReviewおよびCorrection Loop
* Final Approval処理
* `developer`へのmerge

これらは後続Phaseで実装する。

#### Implementation Targets

##### Application Package Structure
Application Layerは、
Application Layer Specificationで定義された責務分離に従い、
`core`の外側に独立したトップレベルPython Packageとして構築する。

基本配置は、以下とする。

```text
specflow/
├── application/
├── core/
├── projects/
└── tests/
```

##### DTO Foundation

Application LayerのUseCaseで使用するInput / Output DTOは、
Python標準ライブラリの`dataclass`を用いて定義する。

DTOは原則としてimmutableなデータ構造として扱い、
以下の形式を基本とする。

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleInput:
    ...


@dataclass(frozen=True)
class ExampleOutput:
    ...
```

##### State Management Components

Phase 1では、
Application Layerが現在のWorkflow Stateを確認し、
状態遷移を追跡可能な形で記録するための
State Management基盤を実装する。

Current Stateは`state.json`に保存する。

State Transition Historyは、
`state_history/`配下の独立したJSONファイルとして保存する。

State Transition Historyには、
少なくとも以下を保持する。

```text
transition_id
from_state
to_state
occurred_at
reason
```
状態遷移が発生した場合は、
Current Stateの更新とState Transition Historyの記録を行う。

Application Layerは、
後続UseCaseの実行可否を判断する際に
Current Stateを参照できなければならない。

Phase 1では、
個別UseCase固有の状態遷移ロジックまでは実装しない。

State Managementに関する具体的なService、
Repository、Adapter等のComponent分割については、
Application Layer Specificationで明示的に定義されていないため、
本Planでは新たに固定しない。

実装時にSpecificationから一意に決定できない
追加の責務分離または設計判断が必要となった場合は、
実装者またはAIが独自に補完せず、
Humanによる確認へ戻る。

##### Approval Components

Phase 1では、
Human Approvalを後続Workflowで安全に利用するための
Approval基盤を実装する。

Human Approvalにおける承認・却下等の判断はHumanのみが行い、
Application Layer、Core Service、AI Runner、
RepositoryまたはAdapterが、
その判断を生成、推定または代替してはならない。

Coreには、
Humanによる判断結果からApproval Recordを構築する責務と、
Approval Recordが現在のArtifactに対して有効であることを
検証する責務を配置する。

Approval Recordには、
少なくとも以下を保持する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```
Approval Validationでは、
少なくとも以下を確認する。

- Approval Recordが存在すること
- `decision`が承認を示していること
- Approval RecordがCurrent Artifactに対応していること
- Current ArtifactからHashを計算できること
- Approval Recordの`artifact_hash`と
  Current ArtifactのHashが一致すること

これらの条件を満たさないApproval Recordを、
Current Artifactに対する有効なHuman Approvalとして
扱ってはならない。

Approval Validationは、
Humanによる判断内容そのものを再評価するものではなく、
記録されたApprovalとCurrent Artifactとの
同一性および有効性を検証する責務に限定する。

##### Repository Components

Phase 1では、
Approval Recordの永続化方式と
Application Layer / Coreの責務を分離するため、
Approval Record Repositoryの契約を実装する。

Coreには、
Approval Recordを保存・取得するための
Repository契約を配置する。

Repository契約は、
Approval Recordの保存および取得に必要な抽象的な操作を定義し、
JSONファイル等の具体的な永続化方式には依存しない。

Application LayerおよびCoreは、
Approval Recordの永続化を行う際に、
具体的なJSONファイル操作を直接実行してはならない。

具体的な永続化方式は、
Repository契約を実装するInfrastructure / Adapterへ委譲する。

##### Infrastructure / Adapter Components

Phase 1では、
Coreで定義されたApproval Record Repository契約を実装する
Infrastructure / Adapter Componentを用意する。

Version 1では、
Approval Recordの具体的な永続化方式としてJSONファイルを使用する。

`JsonApprovalRecordRepository`は、
Repository契約に従い、
Approval Recordを`approvals/`配下のJSONファイルとして
保存・取得する責務を持つ。

`JsonApprovalRecordRepository`は、
少なくとも以下を担当する。

- Approval RecordをJSON形式へ変換する
- 指定された保存先へ書き込む
- 保存済みJSONを読み込む
- Approval Recordとして復元する
- ファイルが存在しない場合等の永続化上のErrorを返す

`JsonApprovalRecordRepository`は、
Human Approvalの判断、
Approval Recordの有効性判定、
またはApplication LayerのState Transitionを担当してはならない。

##### Tests

Phase 1の実装では、
追加または変更する振る舞いについて原則としてTDDを適用する。

少なくとも以下をTest対象とする。

- Application LayerからCoreを利用できること
- CoreからApplication Layerへの逆依存を導入していないこと
- Input / Output DTOを`dataclass(frozen=True)`として扱えること
- Current Stateを保存・取得できること
- State Transition発生時にCurrent Stateが更新されること
- State Transition Historyが記録されること
- State Transition Historyに必要な情報が保持されること
- Approval Recordを必要な情報から構築できること
- Approval RecordをJSON形式で保存・取得できること
- 保存したApproval Recordを復元できること
- 有効なApproval RecordとCurrent ArtifactのHashが一致する場合、
  Approval Validationが有効と判定すること
- Approval Recordが存在しない場合、
  Approval Validationが無効と判定すること
- `decision`が承認を示していない場合、
  Approval Validationが無効と判定すること
- Current ArtifactのHashと`artifact_hash`が一致しない場合、
  Approval Validationが無効と判定すること
- 永続化対象のファイルが存在しない場合等のErrorを
  適切に扱えること

Phase 1で追加する対象Testに加えて、
既存Test Suiteを実行し、
既存機能にRegressionが発生していないことを確認する。

#### Completion Conditions

Phase 1は、
以下の条件をすべて満たした場合に完了とする。

- `specflow/application/`が独立したApplication Layer Packageとして成立している
- Application LayerとCoreの依存方向がSpecificationに従っている
- Input / Output DTOの基本構造が利用可能である
- Current Stateを保存・取得できる
- State Transition発生時にCurrent Stateの更新と
  State Transition Historyの記録を行える
- Approval Recordを構築できる
- Approval RecordをRepository契約を通じて保存・取得できる
- JSONによるApproval Recordの具体的な永続化実装が利用可能である
- Approval RecordとCurrent Artifactの整合性を
  Approval Validationによって検証できる
- Phase 1で追加または変更した対象Testがすべて成功している
- 既存Test Suiteがすべて成功し、
  既存機能にRegressionが確認されていない
- Phase 1のScope外となる後続UseCaseの業務処理が
  先行実装されていない

上記Completion Conditionsを満たしたことを確認した後、
Phase 2 Plan Generation & Plan Approvalへ進む。

### Phase 2 Plan Generation & Plan Approval
#### Purpose
Phase 2では、
有効に承認されたSpecificationを基にImplementation Plan Draftを生成し、
HumanによるImplementation Planの確認および承認判断を
Workflowとして実行可能にする。

本Phaseでは、
UC-02 `Generate Implementation Plan Draft`、
UC-03 `Request Plan Approval`、
およびUC-04 `Revise Implementation Plan`
に必要なApplication Layerの処理を実装する。

Implementation Plan Draftの生成には、
既存のPlan Prompt生成基盤およびChatGPT Runnerを利用する。

生成されたImplementation PlanはDraftとして扱い、
Humanによる有効なApprovalが確認されるまで、
承認済みImplementation Planとして扱ってはならない。

HumanがImplementation Planを承認した場合は、
Phase 1で構築したApproval基盤を利用して
Approval Recordを構築・保存し、
現在のImplementation Planとの整合性を検証する。

有効なImplementation Plan Approvalが確認された場合にのみ、
後続のCodex Prompt生成工程へ進行可能とする。

Humanが修正を要求した場合は、
Humanの修正理由を基にImplementation Plan Draftを再生成し、
再びHuman Approvalを必要とする状態へ戻す。

Humanが中止を判断した場合は、
後続工程へ進行してはならない。

Phase 2の目的は、
Implementationそのものを開始することではなく、

Specification
        ↓
Implementation Plan Draft
        ↓
Human Decision
        ↓
Approval Validation
        ↓
Approved Implementation Plan

というPlan生成・承認境界を、
Application Layer上で安全に成立させることである。

#### Scope

Phase 2の対象は、Implementation Plan Draftの生成、
HumanによるPlan Approval、
Plan Approvalの有効性検証、
およびHumanから修正依頼を受けた場合の
Implementation Plan Draft再生成に必要なApplication Layer処理とする。

Phase 2では、少なくとも以下を対象とする。

- 有効に承認されたSpecificationをPlan生成Inputとして受け取る
- Specification Approvalの有効性を確認する
- Plan生成開始時に`plan_generating`へ遷移する
- 既存のPlan Prompt生成基盤を利用してPromptを生成する
- `PromptResult`を`PromptAdapter`によって`AIRequest`へ変換する
- ChatGPT RunnerをApplication Layerから呼び出す
- ChatGPT Runnerの実行結果を受け取る
- Implementation Plan Draftを生成結果として扱う
- 使用したSpecificationとの対応関係を保持する
- Plan生成成功後に`plan_approval_pending`へ遷移する
- Implementation Plan DraftをHumanへ提示可能な状態にする
- Humanから承認、修正依頼、または中止のDecisionを受け取る
- Human DecisionからApproval Recordを構築する
- Approval Recordを`ApprovalRecordRepository`を介して保存する
- 現在のImplementation PlanからArtifact Hashを算出する
- Approval Recordと現在のImplementation Planの同一性を検証する
- 有効なApprovalが確認された場合に`plan_approved`へ遷移する
- Approval Validationが失敗した場合に`plan_approval_pending`を維持する
- Humanから修正依頼を受けた場合にImplementation Plan修正工程へ処理を渡す
- Humanの修正理由、現在のImplementation Plan Draft、元のSpecificationを基に修正版Draftを生成する
- 修正版Draft生成後に再びPlan Approvalを必要とする状態へ戻す
- Humanが中止を判断した場合に後続工程への進行を停止する

Phase 2では、以下は実装対象外とする。

- Codex用Implementation Promptの生成
- Codex RunnerによるImplementation
- UC-06で定義されたCodex RunnerによるImplementationとしての
  Source CodeまたはTest Codeの変更
- Implementation Evidenceの構築
- ChatGPTによるImplementation Review
- Correction Loop
- Critical Change Approval
- Final Approval
- `developer`へのmerge

これらは後続Phaseで扱う。

Phase 2では、
Implementation Plan Draftの生成および承認Workflowを成立させるために必要な範囲を超えて、
後続Implementation工程の責務を先行実装してはならない。

#### Implementation Targets

Phase 2では、
UC-02、UC-03、およびUC-04をApplication Layer上で実行するために必要な
Use Case、DTO、既存Coreとの接続、およびPhase 1で構築した
State / Approval基盤との統合を実装する。

主なImplementation Targetは以下とする。

##### Plan Generation

UC-02 `Generate Implementation Plan Draft`を実行する
Application Layer Use Caseを実装する。

このUse Caseは、少なくとも以下を行う。

- 現在のSpecificationおよびSpecification Approval情報をInputとして受け取る
- Specification Approvalが有効であることを確認する
- Plan生成開始時にCurrent Stateを`plan_generating`へ遷移させる
- 既存の`PlanPromptGenerator`を利用して`PromptResult`を取得する
- `PromptAdapter`を利用して`PromptResult`を`AIRequest`へ変換する
- ChatGPT Runnerを呼び出す
- `AIResponse`を受け取る
- Implementation Plan Draftとして利用可能な生成結果を返す
- 使用したSpecificationとの対応情報を保持する
- 正常にPlan Draftを生成できた場合にCurrent Stateを`plan_approval_pending`へ遷移させる
- Plan生成に失敗した場合は、成功Stateへ遷移せずFailure Handlingへ処理を返す

##### Plan Approval

UC-03 `Request Plan Approval`を実行する
Application Layer Use Caseを実装する。

このUse Caseは、少なくとも以下を行う。

- 現在のImplementation Plan DraftをHuman Decisionの対象として扱う
- Humanから承認、修正依頼、または中止のDecisionを受け取る
- Human DecisionをApplication Layer自身が生成または代替しない
- Phase 1で構築した`ApprovalRecordService`を利用してApproval Recordを構築する
- Phase 1で構築した`ApprovalRecordRepository`を介してApproval Recordを保存する
- 現在のImplementation PlanからArtifact Hashを算出する
- Approval Recordと現在のImplementation Planとの同一性およびApprovalの有効性を検証する
- 有効なApprovalが確認された場合に`plan_approved`へ遷移する
- Approval Validationが失敗した場合は`plan_approved`へ遷移せず、`plan_approval_pending`を維持する
- Humanによる修正依頼または中止を、対応する後続処理へ渡す

##### Plan Revision

UC-04 `Revise Implementation Plan`を実行する
Application Layer Use Caseを実装する。

HumanがImplementation Planの修正を要求した場合は、
Current Stateを`plan_revision_requested`へ遷移させ、
Implementation Plan修正工程へ処理を渡す。

修正版Implementation Plan Draftの生成を開始する場合は、
`plan_generating`へ遷移する。

このUse Caseは、少なくとも以下をInputとして扱う。

- 現在のImplementation Plan Draft
- Humanの修正理由
- 元のSpecification
- 必要な関連情報

修正版Implementation Plan Draftを生成した場合は、
前版との対応を識別可能にし、
Current Stateを`plan_approval_pending`へ遷移させ、
再びHumanによるPlan Approvalを必要とする状態へ戻す。

修正版Draftを、
Human Approvalなしに`plan_approved`として扱ってはならない。

##### DTO

Phase 2で追加するInput / Output DTOは、
Phase 1で定めたApplication Layer DTOの規則に従う。

DTOはApplication Layerの境界を表現するために使用し、
CoreまたはInfrastructureの内部表現を
Presentation Layerへ直接公開するために使用してはならない。

##### Integration

Phase 2では、新たなState保存機構またはApproval保存機構を重複実装せず、
Phase 1で構築した以下の基盤を利用する。

- Current State管理
- State Transition History
- Approval Record
- Approval Record Repository
- Artifact HashによるApproval Validation

既存Coreについては、
Phase 2のUse Caseから必要な公開Interfaceを通じて利用し、
CoreからApplication Layerへの逆依存を導入してはならない。

#### Tests

Phase 2の実装では、
追加または変更する振る舞いについて原則としてTDDを適用する。

Testは、単にUse Caseが実行できることだけでなく、
Specificationで定義されたPlan生成、Human Approval、
Approval Validation、Plan Revision、およびState Transitionが
正しく維持されることを検証する。

少なくとも以下をTest対象とする。

##### Plan Generation Tests

- 有効なSpecification Approvalが確認された場合にPlan生成を開始できること
- Plan生成開始時にCurrent Stateが`plan_generating`へ遷移すること
- `PlanPromptGenerator`から`PromptResult`を取得できること
- `PromptAdapter`によって`PromptResult`を`AIRequest`へ変換できること
- Application LayerからChatGPT Runnerを呼び出せること
- ChatGPT Runnerから`AIResponse`を受け取れること
- 正常な生成結果をImplementation Plan Draftとして扱えること
- 生成されたImplementation Plan Draftと使用したSpecificationとの対応関係を保持できること
- Plan Draft生成成功後にCurrent Stateが`plan_approval_pending`へ遷移すること
- Specification Approvalが無効な場合にPlan生成を開始しないこと
- Plan生成に失敗した場合に`plan_approval_pending`へ遷移しないこと

##### Plan Approval Tests

- `plan_approval_pending`のImplementation Plan DraftをHuman Decisionの対象として扱えること
- Humanによる承認Decisionを受け取れること
- Human DecisionからApproval Recordを構築できること
- Approval Recordを`ApprovalRecordRepository`を介して保存できること
- 現在のImplementation PlanからArtifact Hashを算出できること
- Approval RecordのArtifact Hashと現在のImplementation PlanのArtifact Hashを比較できること
- 有効なApprovalが確認された場合にCurrent Stateが`plan_approved`へ遷移すること
- Approval Validationが失敗した場合に`plan_approved`へ遷移しないこと
- Approval Validationが失敗した場合に`plan_approval_pending`を維持すること
- Application LayerがHuman Approvalを独自に生成または代替しないこと

##### Plan Revision Tests

- Humanによる修正要求を受け取れること
- 修正要求を受けた場合にCurrent Stateが`plan_revision_requested`へ遷移すること
- 修正版Implementation Plan Draftの生成開始時に`plan_generating`へ遷移すること
- 現在のImplementation Plan Draft、Humanの修正理由、および元のSpecificationを修正Inputとして扱えること
- 修正版Implementation Plan Draftを生成できること
- 修正版Implementation Plan Draftと前版との対応関係を識別できること
- 修正版Draft生成後にCurrent Stateが`plan_approval_pending`へ遷移すること
- 修正版DraftがHuman Approvalなしに`plan_approved`として扱われないこと

##### State Transition Tests

Phase 2で少なくとも以下のState Transitionを検証する。

```text
specification_ready
        ↓
plan_generating
        ↓
plan_approval_pending
        ↓
plan_approved
```
また、HumanによるPlan Revisionについて、
少なくとも以下のState Transitionを検証する。

```text
plan_approval_pending
        ↓
plan_revision_requested
        ↓
plan_generating
        ↓
plan_approval_pending
```

##### Approval Validation Tests

- Approval対象のArtifact Pathを識別できること
- Approval対象のArtifact Hashを取得できること
- Approval Recordが現在のImplementation Planを対象としていることを確認できること
- Artifact Hashが一致する場合にApprovalを有効として扱えること
- Artifact Hashが一致しない場合にApprovalを無効として扱うこと
- Approval後にImplementation Planが変更された場合、以前のApprovalを有効として扱わないこと
- 無効なApprovalを根拠として後続のCodex Prompt生成工程へ進めないこと

##### Cancellation Tests

- Humanが中止を判断した場合にCurrent Stateが`cancelled`へ遷移すること
- `cancelled`へ遷移した場合に後続のCodex Prompt生成工程へ進まないこと
- Application LayerがHumanの中止判断を変更または無視しないこと
- AI Runnerによって中止後のWorkflowが自動的に再開されないこと

##### Dependency and Regression Tests

- Phase 2のUse Caseから既存Coreの公開Interfaceを利用できること
- CoreからApplication Layerへの逆依存を導入していないこと
- Phase 1で構築したState管理基盤を再利用できること
- Phase 1で構築したApproval RecordおよびApproval Record Repositoryを再利用できること
- Phase 1で構築したApproval Validation基盤を再利用できること
- Phase 2のために重複したState保存機構を追加していないこと
- Phase 2のために重複したApproval保存機構を追加していないこと
- Phase 1までの既存Testが引き続き成功すること
- Phase 2の追加によって既存の正常な振る舞いにRegressionが発生していないこと

#### Completion Conditions

Phase 2は、以下をすべて満たした場合に完了とする。

- 有効なSpecification Approvalを確認した場合にのみImplementation Plan Draft生成を開始できる
- Plan生成開始時にCurrent Stateを`plan_generating`へ遷移できる
- 既存の`PlanPromptGenerator`および`PromptAdapter`を利用してChatGPT Runnerを実行できる
- ChatGPT Runnerの生成結果をImplementation Plan Draftとして扱える
- Implementation Plan Draftと、その生成に使用したSpecificationとの対応関係を保持できる
- Plan Draft生成成功後にCurrent Stateを`plan_approval_pending`へ遷移できる
- Humanによる承認、修正依頼、または中止のDecisionを受け取れる
- Humanによる承認DecisionからApproval Recordを構築・保存できる
- 現在のImplementation PlanとApproval RecordのArtifact Hashを用いてApproval Validationを実行できる
- 有効なApprovalが確認された場合にのみCurrent Stateを`plan_approved`へ遷移できる
- Approval Validationが失敗した場合に`plan_approved`へ遷移せず、`plan_approval_pending`を維持できる
- Humanによる修正要求を受けた場合に`plan_revision_requested`へ遷移できる
- Plan Revision開始時に`plan_generating`へ遷移し、修正版Implementation Plan Draftを生成できる
- 修正版Implementation Plan Draft生成後に`plan_approval_pending`へ戻し、再度Human Approvalを要求できる
- 修正版Implementation Plan DraftをHuman Approvalなしに`plan_approved`として扱わない
- Humanが中止を判断した場合に`cancelled`へ遷移し、後続工程へ進行しない
- Application LayerまたはAI RunnerがHuman ApprovalまたはHumanの中止判断を独自に生成、変更、無視、または代替しない
- Phase 1で構築したState管理、State Transition History、Approval Record、Approval Record Repository、およびApproval Validation基盤を再利用できる
- CoreからApplication Layerへの逆依存を導入していない
- Phase 2のためにState保存機構またはApproval保存機構を重複実装していない
- Phase 2で追加または変更した振る舞いに対するTestが成功する
- Phase 1までの既存Testがすべて成功する
- Phase 2の実装が、Codex RunnerによるImplementation、Implementation Evidence、Review、Correction、Final Approval、Merge等の後続Phaseの責務へ侵入していない

### Phase 3 Implementation Execution Foundation
#### Purpose

Phase 3では、
Humanによって有効に承認されたSpecificationおよびImplementation Planを基に、
Codex Runnerへ渡すImplementation Promptを生成し、
承認されたScope内でImplementationおよびTestを実行できる
Application Layerの実行基盤を構築する。

本Phaseでは、
UC-05 `Generate Codex Implementation Prompt`および
UC-06 `Execute Implementation`
に必要なApplication Layerの処理を実装する。

Codex Prompt生成では、
SpecificationおよびApproved Implementation Planとの対応関係を維持し、
Implementation Scope、許可された変更範囲、TDD要件、
Completion Conditions、Stop Conditions、
およびHuman Approvalを必要とする条件を
Codex Runnerへ明示できる状態を成立させる。

有効なCodex Promptが生成され、
Implementation開始に必要なInputが確認された場合にのみ、
Codex RunnerによるImplementationを開始できる。

Codex Runnerは、
承認されたScope内でImplementationおよびTestを実行し、
その実行結果をApplication Layerへ返す。

Application Layerは、
Codex Runner自身に後続Workflowの判断を委ねず、
Test Result、Test Execution Error、
Human Approvalを必要とする事項、
その他の実行結果を受け取り、
後続工程への進行可否を制御する。

Testが正常に実行された結果としての`PASS`または`FAIL`と、
Test実行処理そのものを正常に完了できなかった
`Test Execution Error`を明確に区別する。

Test Resultが`FAIL`であることのみを理由として、
Technical Error、Implementation Failure、
または自動Correctionとして扱ってはならない。

Technical Errorが発生した場合は、
定められたTechnical RetryおよびImplementation Failureの規則に従う。

Implementation中に、
Specification、Approved Implementation Plan、
Codex Prompt、または既存のHuman Approval Scopeを超える
Critical Changeが必要となった場合は、
Implementationを継続せず、
Human Approvalを必要とする工程へ処理を渡す。

Phase 3の目的は、
Implementation Evidenceそのものを完成させることではなく、

Approved Implementation Plan
        ↓
Codex Prompt
        ↓
Implementation Ready
        ↓
Codex Implementation
        ↓
Test Execution
        ↓
Implementation Result

というImplementation実行境界を、
Application Layer上で安全に成立させることである。

Implementation Evidenceの構築および保存は、
Phase 4で扱う。

#### Scope

Phase 3の対象は、
有効に承認されたSpecificationおよびImplementation Planを基にした
Codex Promptの生成と、
Codex RunnerによるImplementationおよびTest実行に必要な
Application Layer処理とする。

Phase 3では、少なくとも以下を対象とする。

- Specification ApprovalおよびImplementation Plan Approvalの有効性を確認する
- Codex Prompt生成開始時に`implementation_prompt_generating`へ遷移する
- SpecificationおよびApproved Implementation Planを基にCodex Promptを生成する
- 生成されたCodex Promptと、使用したSpecificationおよびApproved Implementation Planとの対応関係を保持する
- Codex Promptが承認済みImplementation Scopeを拡張していないことを確認する
- Codex PromptにImplementation Scope、許可された変更範囲、TDD要件、Completion Conditions、Stop Conditions、およびHuman Approvalを必要とする条件を含める
- Codex PromptをCodex Runnerへ渡すImplementation Promptとして利用可能であることを確認する
- Codex Prompt生成成功後に`implementation_ready`へ遷移する
- Codex Prompt生成に失敗した場合または安全にImplementationへ使用できない場合に`implementation_ready`へ遷移しない
- Implementation開始に必要なInputを確認する
- Implementation開始時に`implementation_ready`から`implementing`へ遷移する
- Codex RunnerをApplication Layerから呼び出す
- Codex Runnerに承認されたScope内でImplementationおよびTestを実行させる
- Codex RunnerからImplementationおよびTestの実行結果を受け取る
- 作成・変更・削除したファイルに関する情報を受け取る
- 実行したCommandに関する情報を受け取る
- Test実行状態およびTest Resultを受け取る
- `PASS`、`FAIL`、および`Test Execution Error`を区別する
- Error、Warning、未完了事項、およびHuman Approvalが必要な事項を受け取る
- Test Resultが`FAIL`であることのみを理由としてTechnical ErrorまたはImplementation Failureとして扱わない
- Test Resultが`FAIL`であることのみを理由としてCodex RunnerにCorrectionを開始させない
- Technical Errorが発生した場合にTechnical RetryまたはImplementation Failureの規則へ処理を渡す
- Implementationが承認されたScope内で正常に完了し、必要なTest実行およびImplementation Evidence構築に必要な実行結果を取得できた場合に`implementation_completed`へ遷移する
- Implementationを正常に継続または完了できない場合に`implementation_completed`へ遷移しない
- Critical Changeが必要となった場合にImplementationを継続せず`critical_approval_pending`へ遷移し、UC-07へ処理を渡す
- Critical Changeに対する有効なHuman Approvalが確認されるまで、当該変更を含むImplementationを再開しない

Phase 3では、以下は実装対象外とする。

- Implementation Evidenceの最終的な構築および保存
- ChatGPT RunnerによるImplementation Review
- Review Resultに基づくCorrection Loop
- Critical Changeに対するHuman Approvalそのものの取得・記録・検証
- Final Approval
- `developer`へのmerge

これらは後続Phaseで扱う。

Phase 3では、
Codex RunnerにApplication LayerのWorkflow判断責務を移してはならない。

Codex RunnerはImplementationおよびTestの実行を担当し、
Application Layerはその実行結果を受けて、
後続Workflowへ進行可能かどうかを制御する。

### Phase 4 Implementation Evidence

### Phase 5 Review & Correction

### Phase 6 Final Approval & Merge

### Phase 7 Integration & MVP Completion