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

#### Implementation Targets

Phase 3では、
UC-05およびUC-06をApplication Layer上で実行するために必要な
Use Case、DTO、既存CoreおよびAI Runnerとの接続、
ならびにPhase 1およびPhase 2で構築した
State / Approval基盤との統合を実装する。

主なImplementation Targetは以下とする。

##### Codex Prompt Generation

UC-05 `Generate Codex Implementation Prompt`を実行する
Application Layer Use Caseを実装する。

このUse Caseは、少なくとも以下を行う。

- 現在のSpecificationおよびApproved Implementation PlanをInputとして受け取る
- Specification ApprovalおよびImplementation Plan Approvalの有効性を確認する
- Approvalの有効性を、対応するApproval Recordおよび現在のArtifact Hashとの整合性によって確認する
- Codex Prompt生成開始時にCurrent Stateを`implementation_prompt_generating`へ遷移させる
- SpecificationおよびApproved Implementation Planを基にCodex Promptを生成する
- Codex PromptにImplementation Scopeを反映する
- Codex Promptに許可された変更範囲を反映する
- Codex PromptにTDD要件を反映する
- Codex PromptにCompletion ConditionsおよびStop Conditionsを反映する
- 承認範囲を超える変更が必要となる場合にHuman Approvalを要求する条件をCodex Promptへ明示する
- Codex PromptによってSpecificationまたはApproved Implementation Planで承認されたImplementation Scopeを拡張しない
- Codex Runner自身にImplementation Evidenceの正当性を自己確定させない
- Codex RunnerにImplementation Evidence構築に必要な実行結果を報告させる
- 生成されたCodex Promptと、使用したSpecificationおよびApproved Implementation Planとの対応関係を保持する
- 生成されたCodex PromptがCodex Runnerへ渡すImplementation Promptとして利用可能であることを確認する
- Codex Promptが正常に生成され、安全にImplementationへ使用できる場合にCurrent Stateを`implementation_ready`へ遷移させる
- Codex Prompt生成に失敗した場合、または安全にImplementationへ使用できない場合に`implementation_ready`へ遷移しない
- Prompt生成に失敗した場合は、停止理由および現在のStateを保持し、定められたFailure HandlingまたはHuman判断へ処理を返す

##### Implementation Execution

UC-06 `Execute Implementation`を実行する
Application Layer Use Caseを実装する。

このUse Caseは、少なくとも以下を行う。

- 現在のSpecification、Approved Implementation Plan、およびCodex PromptをInputとして受け取る
- Implementation BranchおよびBase CommitをInputとして受け取る
- Codex Promptが現在のSpecificationおよびApproved Implementation Planに対応していることを確認する
- Implementation開始に必要なInputが揃っていることを確認する
- Implementation開始時にCurrent Stateを`implementation_ready`から`implementing`へ遷移させる
- Implementation Roleに割り当てられたCodex RunnerをApplication Layerから呼び出す
- Codex RunnerにSpecification、Approved Implementation Plan、およびCodex Promptで承認されたScope内でImplementationを実行させる
- TDD対象のImplementationについて、定められたTDD適用ルールに従ってTest作成・変更、期待されるTest失敗の確認、必要最小限のImplementation、およびTest実行を行わせる
- TDD対象外のImplementationについても、承認されたScope内で必要なImplementationおよびTest実行を行わせる
- Codex RunnerからImplementationおよびTestの実行結果を受け取る
- 作成・変更・削除したファイルに関する情報を受け取る
- 実行したCommandに関する情報を受け取る
- Test実行状態、Test Result、およびTest Execution Errorを受け取る
- Error、Warning、未完了事項、およびHuman Approvalが必要な事項を受け取る
- Codex RunnerにTest ResultまたはTechnical Errorを根拠とした後続Workflowを独自に判断させない
- Codex RunnerにImplementation Evidenceの正当性を自己確定させない
- Implementation Evidence構築に必要な実行結果をApplication Layerへ返させる
- Implementationが承認されたScope内で正常に完了し、必要なTest実行およびImplementation Evidence構築に必要な実行結果を取得できた場合にCurrent Stateを`implementation_completed`へ遷移させる
- Implementationを正常に継続または完了できない場合に`implementation_completed`へ遷移しない
- Codex Runnerの実行失敗、Test Execution Error、実行環境上の問題、またはその他のTechnical Errorが発生した場合に、定められたFailure Handlingへ処理を渡す
- 承認されたScopeを超える変更が必要となった場合にCodex Runnerへ当該変更を実行させない
- Critical Changeが必要となった場合にCurrent Stateを`critical_approval_pending`へ遷移させ、UC-07へ処理を渡す
- Critical Changeに対する有効なHuman Approvalが確認されるまで、当該変更を含むImplementationを再開しない

##### Test Result Handling

UC-06におけるTest実行結果について、
Application LayerがTest ResultとTechnical Errorを
明確に区別して扱うための処理を実装する。

少なくとも以下を行う。

- Testが正常に実行された結果としての`PASS`をTest Resultとして扱う
- Testが正常に実行された結果としての`FAIL`をTest Resultとして扱う
- Test実行処理そのものを正常に完了できなかった場合を`Test Execution Error`として扱う
- `PASS`または`FAIL`と`Test Execution Error`を同一の状態として扱わない
- Test Resultが`FAIL`であることのみを理由としてTechnical Errorとして扱わない
- Test Resultが`FAIL`であることのみを理由として`implementation_failed`へ遷移しない
- Test Resultが`FAIL`であることのみを理由としてCorrectionを自動的に開始しない
- Test Resultが`FAIL`の場合も、Implementation Evidence構築に必要なTest Resultとして後続工程へ渡す
- `Test Execution Error`が発生した場合はTechnical Errorとして扱い、定められたTechnical RetryまたはImplementation Failureの規則へ処理を渡す
- Test ResultまたはTest Execution Errorを根拠とした後続Workflowの判断をCodex Runner自身に行わせない
- Application LayerがTest実行結果を受け取り、State Transitionおよび後続Workflowを制御する

##### Technical Retry and Implementation Failure

UC-06においてTechnical Errorが発生した場合に、
Application LayerがTechnical Retryの可否を判定し、
Implementationを安全に継続できない場合に
Implementation Failureとして扱うための処理を実装する。

少なくとも以下を行う。

- Codex Runnerの実行失敗、Test Execution Error、実行環境上の問題、その他の技術的理由による失敗をTechnical Errorとして受け取る
- Technical Errorが発生したことのみを理由として直ちに`implementation_failed`へ遷移しない
- Technical Errorについて、安全にTechnical Retryを実行可能かを判定する
- Technical Retryでは承認対象Artifactを変更しない
- Technical RetryではSource CodeまたはTest Codeを変更しない
- Technical RetryではSpecificationを変更しない
- Technical RetryではApproved Implementation Planを変更しない
- Technical RetryではHuman Approval Scopeを変更しない
- Technical Retryによって新たな設計判断を行わない
- Technical Retryによって破壊的変更を発生させない
- 同一入力および同一条件による同一の技術操作を安全に再実行可能な場合にのみTechnical Retryを許可する
- Technical Retryによって成果物または承認対象の内容を変更しない
- Technical RetryをImplementation Correction LoopのCorrection Countに含めない
- Technical Retryによって復旧した場合は`implementing`を維持し、Implementation工程を継続する
- Technical Retryによって復旧できない場合は`implementation_failed`へ遷移する
- Technical Retryとして安全に処理できないTechnical Errorの場合は`implementation_failed`へ遷移する
- `implementation_failed`へ遷移した場合は、自動的に成果物を修正してImplementationを継続せず、Human判断へ処理を返す
- Testが正常に実行された結果としての`FAIL`をTechnical ErrorまたはImplementation Failureとして扱わない
- TDDにおけるExpected Test FailureをTechnical ErrorまたはImplementation Failureとして扱わない

##### Critical Change Detection and Handoff

UC-06によるImplementation中に、
既存のSpecification、Approved Implementation Plan、
Codex Prompt、またはHuman Approval Scopeを超える変更が
必要となった場合に、
Application LayerがImplementationを停止し、
UC-07へ処理を渡すための境界を実装する。

少なくとも以下を行う。

- Codex RunnerからHuman Approvalが必要な事項を受け取る
- Implementation中に必要となった変更が、現在承認されているImplementation Scope内で実行可能かを確認する
- Specificationを超える変更を自動的に実行しない
- Approved Implementation Planを超える変更を自動的に実行しない
- Codex Promptで許可された範囲を超える変更を自動的に実行しない
- Human Approval Scopeを超える変更を自動的に実行しない
- 承認されたScopeを超える変更を通常のCorrectionとして扱わない
- 承認されたScopeを超える変更をTechnical Retryとして扱わない
- Critical Changeが必要となった場合にImplementationを継続しない
- Critical Changeが必要となった場合に`implementation_completed`へ遷移しない
- Critical Changeが必要となった場合にCurrent Stateを`critical_approval_pending`へ遷移させる
- Critical Changeに関する情報をUC-07へ渡す
- Critical Changeに対する有効なHuman Approvalが確認されるまで、当該変更を含むImplementationを再開しない
- Critical Change ApprovalなしにCodex Runnerへ承認範囲外の変更を実行させない
- Critical Change Approval後にImplementationを再開する場合も、Humanによって承認された変更範囲を超えない

##### DTO and Application Layer Interface

Phase 3で実装するUC-05およびUC-06では、
Application Layer Specificationで定義されたDTOの基本方針に従い、
UseCaseの正式なInput / Output契約として
`dataclass(frozen=True)`を基本とするDTOを使用する。

DTOは、
Application Layerと他のLayerまたはInterfaceとの間で
必要なデータを受け渡すための契約として扱い、
DTO自身にWorkflowの進行判断、
AI Runnerの実行、
State Transition、
Human Approvalの判断等の処理を持たせない。

Phase 3では、
SpecificationのDTO命名規則に従い、
UC-05およびUC-06との対応関係が明確になる名称を使用する。

少なくとも以下のInput / Output DTOを実装する。

```text
GenerateCodexPromptInput
GenerateCodexPromptOutput

ExecuteImplementationInput
ExecuteImplementationOutput
```

##### State, Approval, and Runner Integration

Phase 3では、
UC-05およびUC-06を個別の処理として実装するだけでなく、
Phase 1およびPhase 2で構築したState Management、
Approval Validation、
ならびに既存のAI Runner基盤と統合し、
Application LayerがImplementation実行工程を
一貫して制御できる構造を実装する。

Application Layerは、
Current Stateのみを根拠として
SpecificationまたはImplementation Planが
有効に承認されていると判断してはならない。

Codex Prompt生成へ進む前に、
対応するApproval RecordとCurrent Artifactの整合性を
`ApprovalValidationService`によって確認し、
有効なHuman Approvalが確認された場合にのみ
後続工程へ進行する。

少なくとも以下を行う。

- UC-05開始前にSpecification Approvalの有効性を確認する
- UC-05開始前にImplementation Plan Approvalの有効性を確認する
- Approval Validationでは、対応するApproval RecordとCurrent Artifact Hashとの整合性を確認する
- Approval Validationに失敗した場合はCodex Prompt生成またはImplementation実行へ進行しない
- Codex Prompt生成開始時にCurrent Stateを`implementation_prompt_generating`へ遷移させる
- Codex Prompt生成が正常に完了し、安全にImplementationへ使用できる場合にのみ`implementation_ready`へ遷移させる
- UC-06開始時にCurrent StateおよびImplementation開始に必要なInputを確認する
- UC-06開始時に`implementation_ready`から`implementing`へ遷移させる
- Implementationが承認されたScope内で正常に完了し、必要な実行結果を取得できた場合に`implementation_completed`へ遷移させる
- Technical Error、Critical Change、その他Implementationを正常に継続できない状態では、正常系のState Transitionを行わない
- State Transition発生時には、Phase 1で構築したState Management基盤を利用してCurrent Stateを更新する
- State Transition HistoryをPhase 1で定義した方式に従って記録する

AI Runnerとの統合では、
Application LayerがAI製品そのものを
UseCaseの本質的な責務として扱わない構造を維持する。

Application Layerは概念的に、

```text id="6o3eqv"
UseCase
   ↓
Required AI Role
   ↓
Version 1 Runner Assignment
   ↓
AIRequest
   ↓
Assigned Runner
   ↓
AIResponse
   ↓
Application Layer
   ↓
Workflow Control
```

##### Tests

Phase 3の実装では、
追加または変更する振る舞いについて原則としてTDDを適用する。

UC-05およびUC-06について、
正常系だけでなく、
Approval Validation失敗、
Codex Prompt生成失敗、
Test ResultとTest Execution Errorの区別、
Technical Retry、
Implementation Failure、
Critical Change、
および不正なState Transitionを防止する振る舞いをTestする。

少なくとも以下をTest対象とする。

###### Codex Prompt Generation

- 有効に承認されたSpecificationおよびImplementation Planを基にCodex Promptを生成できること
- Specification Approvalが有効でない場合にCodex Prompt生成へ進まないこと
- Implementation Plan Approvalが有効でない場合にCodex Prompt生成へ進まないこと
- Approval ValidationにおいてApproval RecordとCurrent Artifact Hashが一致しない場合にCodex Prompt生成へ進まないこと
- Codex Prompt生成開始時にCurrent Stateが`implementation_prompt_generating`へ遷移すること
- 生成されたCodex PromptにImplementation Scopeを反映できること
- 生成されたCodex PromptにAllowed ChangesおよびForbidden Changesを反映できること
- 生成されたCodex PromptにTDD Requirementsを反映できること
- 生成されたCodex PromptにCompletion ConditionsおよびStop Conditionsを反映できること
- 生成されたCodex PromptにRequired Execution Result Reportingを反映できること
- Human Approvalが必要となる条件をCodex Promptへ反映できること
- Codex PromptがSpecificationおよびApproved Implementation Planで承認されたScopeを拡張しないこと
- 生成されたCodex Promptと、使用したSpecificationおよびApproved Implementation Planとの対応関係を保持できること
- Codex Promptが正常に生成され、安全にImplementationへ使用できる場合に`implementation_ready`へ遷移すること
- Codex Prompt生成に失敗した場合に`implementation_ready`へ遷移しないこと
- Codex Promptを安全にImplementationへ使用できない場合に`implementation_ready`へ遷移しないこと
- Prompt生成失敗時に停止理由および現在のStateを保持できること

###### Implementation Execution

- 有効なCodex Promptおよび必要なInputが揃っている場合にImplementationを開始できること
- Implementation開始時にCurrent Stateが`implementation_ready`から`implementing`へ遷移すること
- 必要なInputが不足している場合にImplementationを開始しないこと
- Codex Promptが現在のSpecificationおよびApproved Implementation Planに対応していない場合にImplementationを開始しないこと
- Implementation Roleに割り当てられたCodex Runnerを呼び出せること
- Codex Runnerへ承認されたImplementation Scopeを渡せること
- TDD対象のImplementationについてTDD適用ルールに従って実行できること
- TDD対象外の変更について承認されたScope内でImplementationを実行できること
- Codex Runnerから作成・変更・削除したファイルに関する情報を受け取れること
- Codex Runnerから実行したCommandに関する情報を受け取れること
- Codex RunnerからTest実行状態およびTest Resultを受け取れること
- Codex RunnerからError、Warning、未完了事項、およびHuman Approvalが必要な事項を受け取れること
- Implementationが承認されたScope内で正常に完了し、必要な実行結果を取得できた場合に`implementation_completed`へ遷移すること
- Implementationを正常に継続または完了できない場合に`implementation_completed`へ遷移しないこと

###### Test Result Handling

- Testが正常に実行され結果が`PASS`の場合にTest Resultとして扱えること
- Testが正常に実行され結果が`FAIL`の場合にTest Resultとして扱えること
- TDDにおけるExpected Test Failureを正常なTDD工程として扱えること
- Expected Test Failureのみを理由として`implementation_failed`へ遷移しないこと
- Implementation後のTest Resultが`FAIL`であることのみを理由としてTechnical Errorとして扱わないこと
- Implementation後のTest Resultが`FAIL`であることのみを理由として`implementation_failed`へ遷移しないこと
- Test Resultが`FAIL`であることのみを理由としてCorrectionを自動的に開始しないこと
- Test Resultが`PASS`または`FAIL`の場合にImplementation Evidence構築に必要な実行結果として後続工程へ渡せること
- Test実行処理そのものを正常に完了できない場合に`Test Execution Error`として扱えること
- `Test Execution Error`とTest Resultとしての`FAIL`を区別できること
- `Test Execution Error`をTechnical ErrorとしてTechnical RetryまたはImplementation Failureの判定へ渡せること

###### Technical Retry and Implementation Failure

- Technical Error発生時に直ちに`implementation_failed`へ遷移せず、Technical Retry可能性を判定すること
- 成果物を変更せず同一の技術操作を安全に再実行可能な場合にTechnical Retryを実行できること
- Technical RetryによってSpecificationを変更しないこと
- Technical RetryによってApproved Implementation Planを変更しないこと
- Technical RetryによってSource CodeまたはTest Codeを変更しないこと
- Technical RetryによってHuman Approval Scopeを変更しないこと
- Technical Retryによって新たな設計判断または破壊的変更を行わないこと
- Technical RetryをCorrection Countに含めないこと
- Technical Retryによって復旧した場合に`implementing`を維持できること
- Technical Retryによって復旧できない場合に`implementation_failed`へ遷移すること
- Technical Retryとして安全に処理できない場合に`implementation_failed`へ遷移すること
- `implementation_failed`への遷移後に自動的に成果物を修正してImplementationを継続しないこと
- `implementation_failed`への遷移後にHuman判断へ処理を返すこと

###### Critical Change

- Specificationを超える変更を自動的に実行しないこと
- Approved Implementation Planを超える変更を自動的に実行しないこと
- Codex Promptで許可された範囲を超える変更を自動的に実行しないこと
- Human Approval Scopeを超える変更を自動的に実行しないこと
- 承認されたScopeを超える変更をTechnical Retryとして扱わないこと
- 承認されたScopeを超える変更を通常のCorrectionとして扱わないこと
- Critical Changeが必要となった場合にImplementationを継続しないこと
- Critical Changeが必要となった場合に`implementation_completed`へ遷移しないこと
- Critical Changeが必要となった場合に`critical_approval_pending`へ遷移すること
- Critical Changeに関する情報をUC-07へ渡せること
- 有効なCritical Change Approvalが確認されるまで当該変更を含むImplementationを再開しないこと

###### DTO and Interface

- `GenerateCodexPromptInput`および`GenerateCodexPromptOutput`を`dataclass(frozen=True)`として扱えること
- `ExecuteImplementationInput`および`ExecuteImplementationOutput`を`dataclass(frozen=True)`として扱えること
- UC-05に必要なInput情報を`GenerateCodexPromptInput`で受け渡せること
- UC-05に必要なOutput情報を`GenerateCodexPromptOutput`で返せること
- UC-06に必要なInput情報を`ExecuteImplementationInput`で受け渡せること
- UC-06に必要なOutput情報を`ExecuteImplementationOutput`で返せること
- Application Layer DTO自身がWorkflow判断またはAI実行処理を担当しないこと
- Application LayerのInput / Output DTOと`AIRequest` / `AIResponse`の責務を分離できていること

###### State, Approval, and Runner Integration

- Application LayerがCurrent Stateのみを根拠としてHuman Approvalを有効と判断しないこと
- Approval Validation成功時のみ承認を前提とした後続工程へ進行できること
- Approval Validation失敗時に承認を前提とした後続工程へ進行しないこと
- State Transition発生時にCurrent Stateが正しく更新されること
- State Transition発生時にState Transition Historyが記録されること
- Codex Prompt Generation RoleにVersion 1で定義されたRunner Assignmentを利用できること
- Implementation RoleにVersion 1で定義されたRunner Assignmentを利用できること
- Application Layerから既存の`AIRequest`および`AIResponse`を利用できること
- Application Layerから既存のAI Runner基盤を利用できること
- Application Layer内に既存Runnerと同等の責務を重複実装していないこと
- AI RunnerがHuman Approvalを独自に確定しないこと
- AI RunnerがState Transitionまたは後続Workflowを独自に確定しないこと
- Application LayerがAIResponseおよび実行結果を受けて後続Workflowを制御できること
- Application LayerがHuman Approvalそのものを生成、推定、補完、または代替しないこと

Phase 3で追加または変更する対象Testに加えて、
既存Test Suiteを実行し、
Phase 1およびPhase 2を含む既存機能に
Regressionが発生していないことを確認する。

#### Completion Conditions

Phase 3は、
UC-05 `Generate Codex Implementation Prompt`および
UC-06 `Execute Implementation`に必要な
Application Layerの実行基盤が成立し、
以下の条件をすべて満たした場合に完了とする。

- 有効に承認されたSpecificationおよびImplementation Planを基にCodex Promptを生成できる
- Specification ApprovalおよびImplementation Plan Approvalの有効性を、対応するApproval RecordとCurrent Artifact Hashとの整合性によって確認できる
- 有効なApprovalを確認できない場合にCodex Prompt生成またはImplementation実行へ進行しない
- Codex PromptにImplementation Scope、Allowed Changes、Forbidden Changes、TDD Requirements、Completion Conditions、Stop Conditions、Required Execution Result Reporting、およびHuman Approval Required Conditionsを反映できる
- Codex PromptがSpecificationおよびApproved Implementation Planで承認されたScopeを拡張しない
- 生成されたCodex Promptと、使用したSpecificationおよびApproved Implementation Planとの対応関係を確認できる
- Codex Prompt生成開始時に`implementation_prompt_generating`へ遷移できる
- Codex Promptが正常に生成され、安全にImplementationへ使用できる場合にのみ`implementation_ready`へ遷移できる
- Codex Prompt生成に失敗した場合または安全にImplementationへ使用できない場合に`implementation_ready`へ遷移しない
- 有効なCodex PromptおよびImplementation開始に必要なInputが確認された場合にのみImplementationを開始できる
- Implementation開始時に`implementation_ready`から`implementing`へ遷移できる
- Implementation Roleに割り当てられたCodex RunnerをApplication Layerから呼び出し、承認されたScope内でImplementationおよびTestを実行できる
- Codex RunnerからImplementationおよびTestの実行結果をApplication Layerへ返すことができる
- 作成・変更・削除したファイル、実行Command、Test実行状態、Test Result、Test Execution Error、Error、Warning、未完了事項、およびHuman Approvalが必要な事項を後続工程で利用可能な実行結果として取得できる
- Testが正常に実行された結果としての`PASS`および`FAIL`と、Test実行処理そのものを正常に完了できなかった`Test Execution Error`を区別できる
- TDDにおけるExpected Test Failureを正常なTDD工程として扱える
- Test Resultが`FAIL`であることのみを理由としてTechnical Error、`implementation_failed`、または自動Correctionとして扱わない
- `Test Execution Error`その他のTechnical Error発生時に、安全なTechnical Retryの可否を判定できる
- Technical Retryでは成果物、Specification、Approved Implementation Plan、およびHuman Approval Scopeを変更せず、Correction Countを増加させない
- Technical Retryによって復旧した場合に`implementing`を維持してImplementationを継続できる
- Technical Retryによって復旧できない場合、またはTechnical Retryとして安全に処理できない場合に`implementation_failed`へ遷移し、自動的に成果物を変更せずHuman判断へ処理を返すことができる
- Implementationが承認されたScope内で正常に完了し、必要なTest実行およびImplementation Evidence構築に必要な実行結果を取得できた場合に`implementation_completed`へ遷移できる
- Implementationを正常に継続または完了できない場合に`implementation_completed`へ遷移しない
- Specification、Approved Implementation Plan、Codex Prompt、またはHuman Approval Scopeを超えるCritical Changeを自動的に実行しない
- Critical Changeが必要となった場合にImplementationを停止し、`critical_approval_pending`へ遷移してUC-07へ処理を渡すことができる
- Critical Changeに対する有効なHuman Approvalが確認されるまで、当該変更を含むImplementationを再開しない
- Application LayerのInput / Output DTOと`AIRequest` / `AIResponse`の責務が分離されている
- Phase 3で必要となるInput / Output DTOを`dataclass(frozen=True)`を基本として扱える
- Application LayerがRole-based Fixed Assignmentを利用して適切なAI Runnerを呼び出せる
- AI RunnerがHuman Approval、State Transition、Technical Retry、Implementation Failure、Correction、Critical Change、またはその他の後続Workflowを独自に確定しない
- Application LayerがAI Runnerから返された結果を基に、Specificationで定義されたState Transitionおよび後続Workflowを制御できる
- State Transition発生時にCurrent StateおよびState Transition Historyを正しく更新・記録できる
- Application LayerまたはAI RunnerがHuman Approvalを生成、推定、補完、または代替しない
- Implementation Evidenceの最終的な構築および保存をPhase 3へ取り込まず、Phase 4との責務境界を維持している
- Phase 3で追加または変更した振る舞いに対するTestがすべて成功する
- Phase 1およびPhase 2を含む既存Test Suiteがすべて成功し、Regressionが発生していない

以上を満たした時点で、
Phase 3 `Implementation Execution Foundation`を完了とする。

Phase 3完了後は、
Phase 4 `Implementation Evidence`へ進み、
Phase 3で取得したImplementationおよびTestの実行結果と、
実際のRepositoryおよびTestの状態を基に、
Review可能なImplementation Evidenceの構築および保存を実装する。

### Phase 4 Implementation Evidence

#### Purpose

Phase 4では、

Phase 3 `Implementation Execution Foundation`によって取得された
Codex RunnerのImplementation実行結果と、
実際のRepositoryおよびTestの状態を収集・照合し、

Review工程で検証可能な
Implementation Evidenceを構築・保存する
Application Layerの基盤を実装する。

本Phaseでは、

UC-08 `Collect Implementation Evidence`

に必要なApplication Layerの処理を実装する。

Implementation Evidenceは、
単なるDebug LogまたはCodex Runnerによる自己申告として扱わず、

- Specification
- Approved Implementation Plan
- Codex Prompt
- Implementation Result
- Source Code
- Git Status
- Git Diff
- Test Code
- Test Result

を相互に関連付け、
Implementationにおいて実際に何が行われたかを
後続のReview工程から検証可能な構造化されたEvidenceとして扱う。

Application Layerは、
Codex Runnerから返されたImplementationおよびTestの実行結果に加え、
可能な範囲で実際のRepositoryおよびTestの状態を取得し、
両者を照合したうえでImplementation Evidenceを構築する。

Codex Runnerから返された情報と、
実際のRepositoryまたはTestの状態に不一致が存在する場合は、
その不一致を無視して正常なEvidenceとして扱わず、

Error、
Warning、
Deviation、
またはHuman Approvalが必要な事項として、
内容に応じて記録できる状態を成立させる。

Version 1では、
Implementation Evidenceの正式フォーマットとしてJSONを使用し、
`evidence/`配下へ保存する。

関連するGit Diffは、
実際のCode変更を検証するための補助Evidenceとして
Implementation Evidenceと対応付けて保存する。

Implementation Evidenceは、
Review開始後に上書きせず、
Correctionまたは再Implementationが行われた場合は、
既存Evidenceを変更するのではなく、
新しいImplementation Evidenceを生成する。

これにより、

Initial Implementation
        ↓
Implementation Evidence
        ↓
Review
        ↓
Correction / Re-Implementation
        ↓
New Implementation Evidence
        ↓
Re-Review

という履歴を追跡可能にする。

Phase 4の目的は、
Implementationの適合性を最終判断することではなく、

Phase 3で得られたImplementation Resultを、
実際のRepositoryおよびTestの状態と結び付け、

Specification
        ↓
Approved Implementation Plan
        ↓
Codex Prompt
        ↓
Implementation Result
        ↓
Repository / Test Verification
        ↓
Implementation Evidence
        ↓
Review Input

という追跡可能なEvidence Chainを
Application Layer上で成立させることである。

Implementationの適合性、
完全性、
および承認範囲からの逸脱に関する最終的なReviewは、
Phase 5で扱う。

#### Scope

Phase 4では、
UC-08 `Collect Implementation Evidence`に必要な
Application LayerのEvidence構築・保存処理を対象とする。

本PhaseのScopeには、少なくとも以下を含む。

- Phase 3で取得されたCodex RunnerのImplementation実行結果を受け取る
- Evidence構築対象となるImplementationを識別する
- 使用したSpecificationを識別する
- 使用したApproved Implementation Planを識別する
- 使用したCodex Promptを識別する
- Implementation BranchおよびBase Commitを識別する
- Codex Promptが対象SpecificationおよびApproved Implementation Planに対応していることを確認する
- Codex Runnerから返された作成・変更・削除ファイルに関する情報を収集する
- Codex Runnerから返されたCommand、Test Result、Error、Warning、未完了事項、およびHuman Approvalが必要な事項を収集する
- 実際のSource Code、Git Status、Git Diff、Test Code、およびTest Resultを可能な範囲で取得する
- Codex Runnerから返された実行結果と、実際のRepositoryおよびTestの状態を照合する
- 作成・変更・削除されたファイルを実際のRepository状態から確認可能にする
- Git Diffを取得または参照可能にする
- 実行したTestおよびその結果を確認可能にする
- TDD対象のImplementationについて、TDD実施状況をEvidenceから確認可能にする
- Codex Runnerから返された情報と実際のRepositoryまたはTestの状態との不一致を検出する
- 検出した不一致を、その内容に応じてError、Warning、Deviation、またはHuman Approvalが必要な事項として記録する
- Specification、Approved Implementation Plan、Codex Prompt、Implementation Result、Repository状態、およびTest状態を相互に関連付ける
- 第9章で定義されたRequired InformationおよびVersion 1 Formatに従ってImplementation Evidenceを構築する
- Implementation EvidenceをJSON形式の正式記録として扱う
- Implementation Evidenceを`evidence/`配下へ保存する
- 関連するGit DiffをImplementation Evidenceに対応する補助Evidenceとして保存する
- 関連するApproval Recordを識別可能な情報によってImplementation Evidenceと関連付ける
- Review開始後のImplementation Evidenceを上書きしない
- Correctionまたは再Implementationが行われた場合に、既存Evidenceを変更せず、新しいImplementation Evidenceを生成できる
- 各Implementation Evidenceが、どのImplementationまたはCorrectionに対応するかを追跡可能にする
- 構築したImplementation EvidenceおよびReviewに必要な関連情報をPhase 5へ渡せる状態にする

Phase 4では、以下は実装対象外とする。

- Implementationそのものの実行
- Codex RunnerによるImplementation Scopeの拡張
- Human Approvalの生成、推定、補完、または代替
- ImplementationのSpecification適合性に関する最終判断
- Implementationの完全性に関する最終判断
- 承認範囲からの逸脱に関するReview結果の確定
- `APPROVED`、`REVISION_REQUIRED`、`HUMAN_REVIEW_REQUIRED`等のReview Resultの決定
- Correction Loopの実行
- Final Approval
- `developer` branchへのMerge

これらのうち、
Implementationの適合性、完全性、および承認範囲からの逸脱に関するReviewは、
Phase 5 `Review & Correction`で扱う。

Phase 4は、

Implementation Result
        ↓
Repository / Test State Collection
        ↓
Result Verification
        ↓
Implementation Evidence Construction
        ↓
Evidence Persistence
        ↓
Review Input

までを責務範囲とする。

Application LayerはImplementation Evidenceを構築するが、
Evidenceの内容からImplementationの適合性を最終判断してはならない。

#### Implementation Targets

##### Implementation Evidence Collection

UC-08 `Collect Implementation Evidence`を実行する
Application Layer Use Caseを実装する。

このUse Caseは、
Phase 3で取得されたImplementation実行結果と、
Implementation Evidence構築に必要な関連情報を収集し、
Review可能なImplementation Evidenceを構築するための
入力情報を成立させる。

少なくとも以下を行う。

- Evidence構築対象となるImplementationを識別する
- Phase 3で取得されたCodex RunnerのImplementation実行結果を受け取る
- 対象Implementationで使用したSpecificationを識別する
- 対象Implementationで使用したApproved Implementation Planを識別する
- 対象Implementationで使用したCodex Promptを識別する
- Implementation Branchを識別する
- Base Commitを識別する
- Source Codeに関する情報を取得する
- Git Statusに関する情報を取得する
- Git Diffに関する情報を取得する
- Test Codeに関する情報を取得する
- Test Resultに関する情報を取得する
- 実行したCommandに関する情報を収集する
- ErrorおよびWarningを収集する
- 未完了事項を収集する
- Human Approvalが必要な事項を収集する
- 関連するApproval Recordを識別可能な情報を収集する
- 使用したCodex Promptが、対象SpecificationおよびApproved Implementation Planに対応するPromptであることを確認可能な情報を保持する

Codex Runnerから返された情報だけを
Implementation Evidenceの根拠としてはならない。

Application Layerは、
Codex Runnerから返されたImplementation実行結果に加えて、
可能な範囲で実際のRepositoryおよびTestの状態を取得し、
後続の照合処理で両者を比較可能な状態にする。

本処理では、
収集された情報のみを根拠として
ImplementationのSpecification適合性、
完全性、
または承認範囲からの逸脱に関する最終判断を行わない。

これらのReview判断は、
Phase 5 `Review & Correction`の責務とする。

##### Repository and Test State Verification

Implementation Evidenceを
Codex Runnerの自己申告だけに依存させないため、

Application Layerが、
Codex Runnerから返されたImplementation実行結果と、
実際のRepositoryおよびTestの状態を
照合可能にする処理を実装する。

少なくとも以下を行う。

- 対象ImplementationのImplementation Branchを確認する
- 対象ImplementationのBase Commitを確認する
- 実際のGit Statusを取得または参照する
- 実際のGit Diffを取得または参照する
- 実際のSource Codeの状態を確認可能にする
- 実際のTest Codeの状態を確認可能にする
- 実行されたTestおよびTest Resultを確認可能にする
- Codex Runnerが報告した作成ファイルと実際のRepository状態を照合する
- Codex Runnerが報告した変更ファイルと実際のRepository状態を照合する
- Codex Runnerが報告した削除ファイルと実際のRepository状態を照合する
- Codex Runnerが報告したTest実行情報と実際のTest状態を照合する
- Codex Runnerが報告したImplementation結果とGit Diffとの対応関係を確認可能にする
- Git Diffから実際に行われたCode変更をReview工程で確認可能にする
- RepositoryおよびTestの実状態を、後続のImplementation Evidence構築処理へ渡す

Codex Runnerから返された情報と、
実際のRepositoryまたはTestの状態に不一致が存在する場合、
その不一致を無視してEvidenceを正常として扱ってはならない。

不一致が検出された場合は、
その内容を後続のEvidence構築処理へ渡し、

- Error
- Warning
- Deviation
- Human Approvalが必要な事項

のいずれとして記録すべきかを
内容に応じて扱える状態にする。

RepositoryおよびTest State Verificationは、
ImplementationがSpecificationまたは
Approved Implementation Planに適合しているかを
最終判断する処理ではない。

本処理の責務は、

Codex Runner Report
        ↓
Actual Repository / Test State
        ↓
Comparison
        ↓
Verified Information / Detected Inconsistency
        ↓
Implementation Evidence Construction

という検証可能な情報経路を成立させることである。

Implementationの適合性、
完全性、
および承認範囲からの逸脱に関する最終的な評価は、
Phase 5 `Review & Correction`で行う。

##### Implementation Evidence Structure and Serialization

収集・照合されたImplementation情報を、
第9章で定義されたVersion 1の形式に従って
Implementation Evidenceとして構造化する処理を実装する。

Version 1のImplementation Evidenceは、
少なくとも以下の主要ブロックを持つ。

- identity
- basis
- scope
- changes
- verification
- deviations
- codex_summary

`identity`では、
対象となるImplementationを識別可能にする。

少なくとも以下を保持する。

- implementation_id
- created_at
- status

`basis`では、
Implementationが何を根拠として実行されたかを
追跡可能にする。

少なくとも以下を保持する。

- Specificationのpathおよびhash
- Approved Implementation Planのpathおよびhash
- Codex Promptのpathおよびhash

`scope`では、
承認されたImplementation Scopeを記録する。

少なくとも以下を保持する。

- target_paths
- allowed_changes
- forbidden_changes

`changes`では、
実際に行われた変更を記録する。

少なくとも以下を保持する。

- created_files
- modified_files
- deleted_files
- git_diff_path
- change_summary

`verification`では、
Implementation後に実施された検証を記録する。

少なくとも以下を保持する。

- commands
- tests_created_or_modified
- target_test_result
- full_test_result
- errors
- warnings

`deviations`では、
承認されたScopeとの不一致および
未解決事項を記録する。

少なくとも以下を保持する。

- out_of_scope_changes
- unplanned_changes
- unfinished_items
- human_approval_required

`codex_summary`では、
Codex Runnerから返されたImplementation実行結果を、
実際のRepositoryおよびTestの状態とは区別したうえで
追跡可能な形で保持する。

Implementation Evidenceには、
第9章で定義されたRequired Informationとして、
必要に応じて以下も関連付ける。

- 関連するApproval Recordの識別情報
- Implementationの実行開始・終了に関する情報
- Error
- Warning
- 未完了事項
- Human Approvalが必要な事項

Humanによる承認・判断そのものの正式な証拠は、
Implementation Evidenceへ重複して保存しない。

Human Approvalの正式記録は、
`approvals/*.json`に保存されたApproval Recordを正本とし、
Implementation Evidenceから必要なApproval Recordを
識別・参照可能にする。

Version 1では、
Implementation Evidenceの正式フォーマットとしてJSONを使用する。

Application Layerは、
構築したImplementation Evidenceを
安定してJSONへSerializationできるようにする。

SerializationされたJSONから、
Implementation Evidenceの構造および内容を
失うことなく復元可能な形式を使用する。

Human向けMarkdownまたはLogを
Implementation Evidenceの正式記録として
JSONと二重管理しない。

Implementation Evidenceの構造化およびSerializationは、
Evidenceに記録された内容から
Implementationの適合性を最終判断する責務を持たない。

本処理の責務は、

Collected / Verified Information
        ↓
Evidence Structure
        ↓
JSON Serialization
        ↓
Persistable Implementation Evidence

という、
機械的に保存・参照・比較可能な
Implementation Evidenceを成立させることである。

##### Evidence Persistence and Git Diff

構築されたImplementation Evidenceおよび
関連するGit Diffを、
後続のReview工程から安定して参照できるように
保存・取得する処理を実装する。

Version 1では、
Implementation Evidenceを
`evidence/`配下へ保存する。

Implementation Evidenceの正式記録は
JSON形式とする。

関連するGit Diffは、
実際のCode変更を検証するための補助Evidenceとして、
対応するImplementation Evidenceと関連付けて保存する。

概念的な保存構造は、以下とする。

projects/specflow/
└── evidence/
    ├── implementation_001.json
    ├── implementation_001.diff
    ├── implementation_002.json
    └── implementation_002.diff

少なくとも以下を行う。

- 構築されたImplementation EvidenceをJSONとして保存できる
- 保存されたImplementation Evidenceを取得できる
- 保存されたJSONからImplementation Evidenceを復元できる
- Implementation Evidenceに対応するGit Diffを保存できる
- Implementation Evidenceから対応するGit Diffを識別・参照できる
- Git Diffが、どのImplementation Evidenceに対応する補助Evidenceであるかを追跡できる
- 各Implementation Evidenceを一意に識別可能にする
- Initial ImplementationとCorrectionまたは再ImplementationによるEvidenceを区別可能にする
- 既存のImplementation Evidenceを保持したまま、新しいImplementation Evidenceを追加保存できる
- 後続のReview工程から対象Implementation Evidenceおよび関連Git Diffを取得できる

JSONをImplementation Evidenceの正本として扱う。

Git Diffは、
Implementation Evidenceそのものの代替ではなく、
Evidenceに記録された変更内容と
実際のCode変更を照合するための
補助Evidenceとして扱う。

Human向けMarkdownまたは`log.txt`を、
Implementation Evidenceの正式記録として
JSONと二重保存しない。

Human-readableな表示が必要となる場合は、
保存されたJSONからUI等によって
表示用データを生成することを前提とする。

Review開始後は、
対象となるImplementation Evidenceを
上書きしてはならない。

Correctionまたは再Implementationが行われた場合は、
既存Evidenceを更新するのではなく、
新しいImplementation Evidenceおよび
対応するGit Diffを生成・保存する。

概念的には、以下の関係を保持する。

Initial Implementation
        ↓
implementation_001.json
implementation_001.diff
        ↓
Review
        ↓
Correction 1
        ↓
implementation_002.json
implementation_002.diff
        ↓
Re-Review

これにより、
Initial Implementationから
各CorrectionおよびRe-ReviewまでのEvidenceを失わず、
Implementation履歴を追跡可能にする。

Evidence Persistence処理は、
保存されたEvidenceの内容から
Implementationの適合性を判断する責務を持たない。

本処理の責務は、

Implementation Evidence
        +
Related Git Diff
        ↓
Persistence
        ↓
Stable Retrieval
        ↓
Review Input

という、
後続工程から再現・参照可能な
Evidence保存基盤を成立させることである。

##### TDD Evidence

TDD対象となるImplementationについて、
TDDが定められた手順に従って実施されたことを
後続のReview工程から確認可能にするため、
TDDに関する実行情報をImplementation Evidenceへ記録する。

TDD対象のImplementationでは、
少なくとも以下を確認可能な形で保持する。

- tests_created_or_modified
- test_commands
- initial_test_result
- target_test_result
- full_test_result

`tests_created_or_modified`では、
対象Implementationのために
作成または変更されたTestを識別可能にする。

`test_commands`では、
TDDおよびImplementation後の検証において
実際に実行されたTest Commandを記録する。

`initial_test_result`では、
必要に応じてImplementation前に確認した
期待されるTest失敗を記録する。

期待されるTDD上のTest失敗は、
Technical ErrorまたはImplementation Failureと
混同してはならない。

`target_test_result`では、
対象Implementationに対応するTestの
Implementation後の結果を記録する。

`full_test_result`では、
必要な既存Testを含む
全体Testの実行結果を記録する。

TDD対象外のImplementationについても、
TDDを適用しなかったこと、および
必要に応じてその理由を
Implementation Evidenceから確認可能にする。

TDDの適用が技術的に困難、
または合理的でない場合に、
Codex Runnerが独自判断でTDDを省略したものとして
正常なEvidenceを成立させてはならない。

その場合は、
TDDを実施できなかった理由をEvidenceへ記録し、
必要に応じてHumanまたは後続のReview工程へ
判断を渡せる状態にする。

Test Resultが`PASS`であることのみを根拠として、
ImplementationがSpecificationまたは
Approved Implementation Planに適合していると
Phase 4で判断してはならない。

同様に、
Test Resultが`FAIL`であることのみを根拠として、
Phase 4がCorrection Loopを開始してはならない。

Phase 4におけるTDD Evidenceの責務は、

TDD Requirement
        ↓
Test Creation / Modification
        ↓
Initial Test Result
        ↓
Implementation
        ↓
Target Test Result
        ↓
Full Test Result
        ↓
Implementation Evidence

という実行経路を
後続のReview工程から検証可能にすることである。

TDDの適切性、
Testの必要十分性、
Implementationとの対応関係、
およびTest Resultを含むImplementation全体の適合性は、
Phase 5 `Review & Correction`で評価する。

##### Evidence Inconsistency Handling

Codex Runnerから返されたImplementation実行結果と、
実際のRepositoryまたはTestの状態との間に
不一致またはEvidence不足が存在する場合に、

その事実を失わずImplementation Evidenceへ反映し、
後続のReview工程から確認可能にする処理を実装する。

少なくとも以下の不一致または不足を
検出・記録可能にする。

- Codex Runnerが報告した作成ファイルと実際のRepository状態が一致しない
- Codex Runnerが報告した変更ファイルと実際のRepository状態が一致しない
- Codex Runnerが報告した削除ファイルと実際のRepository状態が一致しない
- Codex Runnerが報告していない変更がGit Diffに存在する
- Codex Runnerが報告した変更がGit Diffから確認できない
- Codex Runnerが報告したTest実行情報と実際のTest Resultが一致しない
- 必要なGit Statusを取得または参照できない
- 必要なGit Diffを取得または参照できない
- 必要なTest Resultを取得または確認できない
- Evidence構築に必要なSpecificationを識別できない
- Evidence構築に必要なApproved Implementation Planを識別できない
- Evidence構築に必要なCodex Promptを識別できない
- Codex Promptと対象SpecificationまたはApproved Implementation Planとの対応関係を確認できない
- Implementation BranchまたはBase Commitを識別できない
- その他、Reviewに必要なEvidenceが不足または矛盾している

検出された不一致または不足を、
無視、削除、または正常な情報として補完してはならない。

内容に応じて、

- Error
- Warning
- Deviation
- Human Approvalが必要な事項

としてImplementation Evidenceから
確認可能な形で保持する。

Application Layerは、
Evidenceに不足または不一致が存在することを
検出・記録できるが、

その事実だけを根拠として
Implementationの最終的な適合性判断を行ってはならない。

また、
不足しているEvidenceを推測によって生成したり、
Codex Runnerの自己申告によって補完したりしてはならない。

Humanによる判断が必要な不一致または不足については、
`human_approval_required`として
後続工程へ引き渡せる状態にする。

Evidence Inconsistency Handlingは、

Runner Report
        +
Actual Repository / Test State
        ↓
Comparison
        ↓
Mismatch / Missing Evidence Detection
        ↓
Error / Warning / Deviation /
Human Approval Required
        ↓
Implementation Evidence
        ↓
Review

という情報経路を成立させる。

不一致またはEvidence不足が、
Specification違反、
Approved Implementation Planからの逸脱、
Correction対象、
またはHuman Review対象に該当するかという
最終的な評価は、

Phase 5 `Review & Correction`で行う。

##### Evidence Immutability and Traceability

Implementation Evidenceの履歴を保持し、
Initial ImplementationからCorrection、
Re-Implementation、およびRe-Reviewまでを
追跡可能にする処理を実装する。

Reviewが開始されたImplementation Evidenceは、
その後の処理によって上書きまたは置換してはならない。

CorrectionまたはRe-Implementationが行われた場合は、
既存のImplementation Evidenceを変更するのではなく、
新しいImplementation Evidenceを生成する。

少なくとも以下を可能にする。

- 各Implementation Evidenceを識別可能にする
- 各Evidenceが対象とするImplementationを識別可能にする
- Initial Implementationに対応するEvidenceを保持する
- Correction後のImplementationに対応する新しいEvidenceを保持する
- Re-Implementationに対応する新しいEvidenceを保持する
- 各Evidenceに対応するGit Diffを識別可能にする
- 各Evidenceが使用したSpecificationを追跡可能にする
- 各Evidenceが使用したApproved Implementation Planを追跡可能にする
- 各Evidenceが使用したCodex Promptを追跡可能にする
- 関連するApproval Recordを識別可能にする
- Implementationの実行開始・終了に関する情報を追跡可能にする
- Initial ImplementationとCorrectionまたはRe-ImplementationによるEvidenceを区別可能にする
- 後続のReview工程が、対象とするEvidenceを明確に識別できるようにする
- 過去のEvidenceを保持したまま、新しいEvidenceを追加できるようにする

概念的には、以下の履歴を保持する。

Initial Implementation
        ↓
implementation_001.json
implementation_001.diff
        ↓
Review
        ↓
Correction 1
        ↓
implementation_002.json
implementation_002.diff
        ↓
Re-Review
        ↓
Correction 2
        ↓
implementation_003.json
implementation_003.diff
        ↓
Re-Review

このとき、
`implementation_002.json`を生成するために
`implementation_001.json`を変更してはならない。

同様に、
後続のCorrectionまたはRe-Implementationによって
過去のEvidenceおよび対応するGit Diffを
上書きしてはならない。

各Implementation Evidenceは、
その時点で実際に行われたImplementationと
RepositoryおよびTestの状態を表す
独立したEvidenceとして扱う。

Evidence間の追跡可能性を確保するために、
少なくとも、

- implementation_id
- 対象Implementationを識別する情報
- 関連するSpecification
- 関連するApproved Implementation Plan
- 関連するCodex Prompt
- 関連するGit Diff
- 関連するApproval Record

を用いて、
各Evidenceの根拠および関連Artifactを
識別可能にする。

ただし、
Human Approvalの正式な記録そのものを
Implementation Evidenceへ複製してはならない。

Human Approvalの正本はApproval Recordとし、
Implementation Evidenceでは
必要なApproval Recordを識別・参照可能にする。

Evidence Immutability and Traceabilityの責務は、

Implementation
        ↓
Evidence N
        ↓
Review
        ↓
Correction / Re-Implementation
        ↓
Evidence N+1
        ↓
Re-Review

という履歴を失わず、

「どのImplementationに対して、
どのEvidenceが生成され、
何を根拠としてReviewされたか」

を後から追跡可能にすることである。

本処理は、
過去Evidenceと新しいEvidenceを比較して
どちらがSpecificationに適合しているかを
最終判断する責務を持たない。

その評価は、
Phase 5 `Review & Correction`で行う。

##### DTO and Application Layer Interface

UC-08 `Collect Implementation Evidence`を
Application Layerから一貫した方法で実行できるように、

Implementation Evidence構築に必要なInputおよびOutputを
Application LayerのInterfaceとして扱えるようにする。

Inputでは、
少なくとも以下の情報を受け取る、
またはApplication Layerから識別・取得可能にする。

- 対象Implementationを識別する情報
- Codex Prompt
- Codex RunnerのImplementation実行結果
- Specification
- Approved Implementation Plan
- Implementation Branch
- Base Commit
- Source Codeに関する情報
- Git Statusに関する情報
- Git Diffに関する情報
- Test Codeに関する情報
- Test Resultに関する情報
- 実行したCommandに関する情報
- Error
- Warning
- 未完了事項
- Human Approvalが必要な事項
- 関連するApproval Recordを識別する情報

Application Layerは、
Inputとして渡された情報と、
実際のRepositoryおよびTestから取得した情報を
区別して扱えるようにする。

Outputでは、
少なくとも以下を後続処理から利用可能にする。

- 構築されたImplementation Evidence
- Implementation Evidenceを識別する情報
- 関連するGit Diff
- Evidence構築結果
- Evidenceの不足に関する情報
- Evidenceの不一致に関する情報
- Human Approvalが必要な事項

InputおよびOutputは、
Application Layerとその外部との境界を
明確に表現できる構造として定義する。

Application LayerのInterfaceは、
Infrastructure固有の保存形式、
Git操作の具体的実装、
またはRunner固有の内部実装へ
直接依存しないようにする。

Repository、
Git、
Test実行環境、
およびEvidence保存処理の具体的な実装は、
Application Layerから利用可能な抽象を介して扱う。

Codex Runnerから返されたImplementation実行結果を、
そのままImplementation Evidenceとして
Outputしてはならない。

Application Layerは、

Runner Result
        +
Actual Repository / Test State
        ↓
Collection / Verification
        ↓
Implementation Evidence Construction
        ↓
Persistence
        ↓
Application Layer Output

という処理を調整する。

DTOまたはApplication Layer Interfaceは、
Human Approvalを生成、
推定、
補完、
または代替する機能を持たない。

また、
Implementation Evidenceの構築結果を根拠として、
ImplementationのSpecification適合性、
完全性、
またはReview Resultを
Application Layer Interface自身が決定してはならない。

具体的なDTO名、
Use Case名、
Repository abstraction名、
およびInfrastructure implementation名については、

既存のApplication Layerの命名規則および
Specificationで定義された責務との整合性を維持し、
Implementation時に新たな仕様を導入しない範囲で決定する。

本Interfaceの責務は、

Phase 3 Implementation Result
        ↓
Phase 4 Application Layer
        ↓
Implementation Evidence
        ↓
Phase 5 Review Input

というApplication Layer上の境界を
明確に成立させることである。

##### Phase 5 Review Handoff

Phase 4で構築・保存されたImplementation Evidenceおよび
関連するArtifactを、
Phase 5 `Review & Correction`から
検証可能な状態で利用できるようにする。

Phase 5へのReview Inputとして、
少なくとも以下を識別・参照可能にする。

- Specification
- Approved Implementation Plan
- Codex Prompt
- Implementation Evidence
- Source Code
- Git Diff
- Test Code
- Test Result

必要に応じて、
以下についてもReview工程から確認可能にする。

- Implementation Branch
- Base Commit
- Git Status
- 実行したCommand
- Error
- Warning
- Evidenceの不足に関する情報
- Evidenceの不一致に関する情報
- 未完了事項
- Human Approvalが必要な事項
- 関連するApproval Recordを識別する情報

Phase 5へ渡すImplementation Evidenceは、
Codex Runnerの自己申告だけから構築されたものではなく、

Codex Runner Result
        +
Actual Repository State
        +
Actual Test State
        ↓
Collection / Verification
        ↓
Implementation Evidence

というPhase 4の処理を経たものとする。

ただし、
Phase 5はImplementation Evidenceの内容だけを根拠として
Reviewを完結してはならない。

Review工程から、

- Specification
- Approved Implementation Plan
- Codex Prompt
- Source Code
- Git Diff
- Test Code
- Test Result

をImplementation Evidenceと比較できる状態を維持する。

Implementation Evidenceに
`out_of_scope_changes`が存在しないと記録されていても、
実際のGit DiffまたはSource Codeから
承認範囲外の変更が確認される可能性を排除しない。

同様に、
Implementation Evidence上ではImplementationが完了していても、
SpecificationまたはApproved Implementation Planで要求された内容が
Source Code、Git Diff、またはTestから確認できない可能性を排除しない。

これらの判断は、
Phase 4で確定するのではなく、
Phase 5のReviewによって行う。

Phase 4は、
Phase 5がReviewに必要なArtifactおよびEvidenceを
識別・取得・比較できる状態を成立させるところまでを責務とする。

Phase 4では、

- `APPROVED`
- `REVISION_REQUIRED`
- `HUMAN_REVIEW_REQUIRED`

等のReview Resultを決定しない。

また、

- Correctionの開始
- Correction回数の更新
- Re-Reviewの実行
- Final Approvalへの遷移
- `developer` branchへのMerge

を実行しない。

これらは後続Phaseの責務とする。

Phase 4とPhase 5の境界は、

Implementation Execution
        ↓
Implementation Result
        ↓
Phase 4
Evidence Collection / Verification
        ↓
Implementation Evidence
        +
Actual Artifacts / Test Results
        ↓
Phase 5
Review & Correction

とする。

Phase 4の完了とは、
Implementationが適合していると判断された状態ではなく、

Phase 5が、
Implementation Evidenceと実際のArtifactおよびTest Resultを用いて
ImplementationをReviewできる状態が成立したことを意味する。


#### Tests

##### Implementation Evidence Collection

少なくとも以下をTest対象とする。

- UC-08 `Collect Implementation Evidence`をApplication Layerから実行できること
- Phase 3で取得されたCodex RunnerのImplementation実行結果を受け取れること
- Evidence構築対象となるImplementationを識別できること
- 対象Implementationで使用したSpecificationを識別できること
- 対象Implementationで使用したApproved Implementation Planを識別できること
- 対象Implementationで使用したCodex Promptを識別できること
- Implementation Branchを識別できること
- Base Commitを識別できること
- Source Codeに関する情報を取得または後続処理へ渡せること
- Git Statusに関する情報を取得または後続処理へ渡せること
- Git Diffに関する情報を取得または後続処理へ渡せること
- Test Codeに関する情報を取得または後続処理へ渡せること
- Test Resultに関する情報を取得または後続処理へ渡せること
- 実行したCommandに関する情報を収集できること
- ErrorおよびWarningを収集できること
- 未完了事項を収集できること
- Human Approvalが必要な事項を収集できること
- 関連するApproval Recordを識別可能な情報を収集できること
- Codex Promptと対象SpecificationおよびApproved Implementation Planとの対応関係を確認可能な情報を保持できること
- Codex Runnerから返された情報と、実際のRepositoryおよびTestから取得した情報を区別して扱えること
- Codex Runnerから返された情報だけを根拠としてImplementation Evidenceを正常なEvidenceとして確定しないこと
- Evidence収集処理がImplementationのSpecification適合性を最終判断しないこと
- Evidence収集処理がReview Resultを決定しないこと

##### Repository and Test State Verification

少なくとも以下をTest対象とする。

- 対象ImplementationのImplementation Branchを確認できること
- 対象ImplementationのBase Commitを確認できること
- 実際のGit Statusを取得または参照できること
- 実際のGit Diffを取得または参照できること
- 実際のSource Codeの状態を確認可能であること
- 実際のTest Codeの状態を確認可能であること
- 実行されたTestおよびTest Resultを確認可能であること
- Codex Runnerが報告した作成ファイルと実際のRepository状態を照合できること
- Codex Runnerが報告した変更ファイルと実際のRepository状態を照合できること
- Codex Runnerが報告した削除ファイルと実際のRepository状態を照合できること
- Codex Runnerが報告したTest実行情報と実際のTest状態を照合できること
- Codex Runnerが報告したImplementation結果とGit Diffとの対応関係を確認可能であること
- Git Diffから実際に行われたCode変更を確認可能であること
- RepositoryおよびTestの実状態を後続のImplementation Evidence構築処理へ渡せること
- Codex Runnerから返された情報と実際のRepository状態が一致しない場合、その不一致を検出できること
- Codex Runnerから返された情報と実際のTest状態が一致しない場合、その不一致を検出できること
- 検出された不一致を無視して正常な照合結果として扱わないこと
- 検出された不一致を後続のEvidence構築処理へ渡せること
- RepositoryまたはTestの実状態を取得できない場合、その不足を正常な情報として補完しないこと
- Repository and Test State VerificationがImplementationのSpecification適合性を最終判断しないこと
- Repository and Test State VerificationがReview Resultを決定しないこと

##### Evidence Structure and Serialization

少なくとも以下をTest対象とする。

- 収集・照合されたImplementation情報からVersion 1のImplementation Evidenceを構築できること
- Implementation Evidenceが`identity`ブロックを保持できること
- `identity`が少なくとも`implementation_id`、`created_at`、`status`を保持できること
- Implementation Evidenceが`basis`ブロックを保持できること
- `basis`がSpecificationのpathおよびhashを保持できること
- `basis`がApproved Implementation Planのpathおよびhashを保持できること
- `basis`がCodex Promptのpathおよびhashを保持できること
- Implementation Evidenceが`scope`ブロックを保持できること
- `scope`が少なくとも`target_paths`、`allowed_changes`、`forbidden_changes`を保持できること
- Implementation Evidenceが`changes`ブロックを保持できること
- `changes`が少なくとも`created_files`、`modified_files`、`deleted_files`、`git_diff_path`、`change_summary`を保持できること
- Implementation Evidenceが`verification`ブロックを保持できること
- `verification`が少なくとも`commands`、`tests_created_or_modified`、`target_test_result`、`full_test_result`、`errors`、`warnings`を保持できること
- Implementation Evidenceが`deviations`ブロックを保持できること
- `deviations`が少なくとも`out_of_scope_changes`、`unplanned_changes`、`unfinished_items`、`human_approval_required`を保持できること
- Implementation Evidenceが`codex_summary`ブロックを保持できること
- `codex_summary`に保持されたCodex Runnerの情報と、実際のRepositoryおよびTestから取得した情報を区別できること
- 関連するApproval Recordを識別可能な情報を保持できること
- Implementationの実行開始・終了に関する情報を保持できること
- Human Approvalの正式記録そのものをImplementation Evidenceへ複製しないこと
- Approval RecordをHuman Approvalの正本として参照可能であること
- Implementation EvidenceをJSONへSerializationできること
- SerializationされたJSONからImplementation Evidenceを復元できること
- Serializationと復元を行っても必要なEvidence情報が失われないこと
- JSONをVersion 1のImplementation Evidenceの正式記録として扱えること
- Human向けMarkdownまたはLogをJSONと並ぶ別の正式記録として生成することを必須としないこと
- Evidenceの構造化またはSerialization処理がImplementationのSpecification適合性を最終判断しないこと
- Evidenceの構造化またはSerialization処理がReview Resultを決定しないこと

##### Evidence Persistence and Retrieval

少なくとも以下をTest対象とする。

- Implementation Evidenceを`evidence/`配下へJSONとして保存できること
- Implementation Evidenceごとに識別可能な保存先を決定できること
- 保存されたImplementation Evidenceを後から取得できること
- 保存されたJSONからImplementation Evidenceを復元できること
- 保存前と取得・復元後で必要なEvidence情報が失われないこと
- Git DiffをImplementation Evidenceに関連する補助証跡として保存できること
- Implementation Evidenceから関連するGit Diffの保存先を識別できること
- 保存されたGit Diffを後から取得または参照できること
- Evidence JSONとGit Diffの対応関係を確認できること
- Implementation Evidenceの`changes.git_diff_path`から対応するGit Diffを識別できること
- Git DiffをImplementation Evidence JSONの代替となる正式記録として扱わないこと
- Implementation Evidence JSONをVersion 1の正式なEvidence記録として扱うこと
- Evidence保存時に既存のImplementation Evidenceを意図せず上書きしないこと
- CorrectionまたはReimplementationにより新しいEvidenceが必要な場合、既存Evidenceとは別のEvidenceとして保存できること
- Evidence保存処理に失敗した場合、保存成功として扱わないこと
- Git Diffの保存または取得に失敗した場合、その不足を正常な証跡として補完しないこと
- 保存されたEvidenceおよびGit DiffをPhase 5 Reviewへ渡せること
- Evidence Persistence処理がImplementationのSpecification適合性を最終判断しないこと
- Evidence Persistence処理がReview Resultを決定しないこと

##### TDD Evidence

少なくとも以下をTest対象とする。

- TDD対象となるImplementationについて、TDD実施状況をImplementation Evidenceへ記録できること
- 作成または変更されたTestを`tests_created_or_modified`として記録できること
- Test実行に使用したCommandを記録できること
- TDDにおける初期Test Resultを`initial_test_result`として記録できること
- 対象Testの最終結果を`target_test_result`として記録できること
- Full Test Suiteの結果を`full_test_result`として記録できること
- Test ResultについてPASS、FAIL、Technical Errorを区別可能な情報を保持できること
- 初期Test Resultと最終Test Resultを区別して保持できること
- 対象Testの結果とFull Test Suiteの結果を区別して保持できること
- TDDに関する情報を後からPhase 5 Reviewで確認可能であること
- TDDが要求される変更について、TDD Evidenceが不足している場合、その不足を確認可能な状態で記録できること
- TDDを適用しなかった場合、その理由を記録可能であること
- Codex Runnerが独自判断でTDDを省略したことを正常なTDD実施として扱わないこと
- TDDを適用しなかった理由についてHumanの判断が必要な場合、`human_approval_required`へ反映可能であること
- Codex Runnerから報告されたTest Resultだけでなく、実際に確認されたTest ResultをEvidenceへ反映できること
- Test Resultを取得できない場合、推測によってPASSまたはFAILとして補完しないこと
- TDD Evidenceの不足または不一致を無視して正常なEvidenceとして扱わないこと
- TDD Evidenceの収集・記録処理がImplementationのSpecification適合性を最終判断しないこと
- TDD Evidenceの収集・記録処理がReview Resultを決定しないこと

##### Evidence Inconsistency Handling

少なくとも以下をTest対象とする。

- Codex Runnerの報告と実際のRepository状態との不一致をImplementation Evidenceへ記録できること
- Codex Runnerの報告と実際のTest状態との不一致をImplementation Evidenceへ記録できること
- Specification、Approved Implementation Plan、Codex Promptの対応関係に不一致がある場合、その不一致を記録できること
- Implementation BranchまたはBase Commitに不一致がある場合、その不一致を記録できること
- Git StatusまたはGit Diffから想定外の変更が確認された場合、その内容を記録できること
- 許可されたScope外の変更を`out_of_scope_changes`として記録できること
- Approved Implementation Planにない変更を`unplanned_changes`として記録できること
- 未完了のImplementation項目を`unfinished_items`として記録できること
- Humanの判断が必要な事項を`human_approval_required`として記録できること
- Evidence構築に必要な情報が不足している場合、その不足を確認可能な形で記録できること
- RepositoryまたはTestの実状態を取得できない場合、その取得不能をEvidence上で確認できること
- ErrorとWarningを区別して記録できること
- Deviationとして扱う情報を他の通常情報と区別して保持できること
- 不一致または不足が存在する場合、それを正常な情報へ置き換えないこと
- 不一致または不足が存在する場合、それをEvidenceから削除または隠蔽しないこと
- 不明な情報を推測によって補完しないこと
- Codex Runnerの自己申告によって実際のRepositoryまたはTestとの不一致を解消済みとして扱わないこと
- 不一致または不足を保持したImplementation EvidenceをPhase 5 Reviewへ渡せること
- 不一致の検出だけを理由としてPhase 4が`PASS`、`REVISION_REQUIRED`、`HUMAN_REVIEW_REQUIRED`等のReview Resultを決定しないこと
- 不一致の検出だけを理由としてApplication LayerがHuman Approvalを代替しないこと
- Evidence Inconsistency HandlingがImplementationのSpecification適合性を最終判断しないこと

##### Evidence Immutability and Traceability

少なくとも以下をTest対象とする。

- Implementation Evidenceを一意に識別できること
- 保存されたImplementation Evidenceから対象Implementationを識別できること
- Implementation Evidenceから基礎となったSpecificationを識別できること
- Implementation Evidenceから基礎となったApproved Implementation Planを識別できること
- Implementation Evidenceから基礎となったCodex Promptを識別できること
- Implementation EvidenceからImplementation BranchおよびBase Commitを識別できること
- Implementation Evidenceから関連するGit Diffを識別できること
- Implementation Evidenceから関連するApproval Recordを識別可能であること
- Reviewに使用されたImplementation Evidenceを後から上書きしないこと
- Reviewに使用されたImplementation Evidenceの内容を後から変更しないこと
- Review開始後にEvidenceの不足または誤りが判明しても、既存Evidenceを修正して履歴を置き換えないこと
- Correction後には既存Evidenceを更新するのではなく、新しいImplementation Evidenceを生成できること
- Reimplementation後には既存Evidenceを更新するのではなく、新しいImplementation Evidenceを生成できること
- Correction前のImplementation Evidenceを履歴として保持できること
- Reimplementation前のImplementation Evidenceを履歴として保持できること
- 複数のImplementation Evidenceが存在する場合、それぞれを独立したEvidenceとして識別できること
- 新旧のImplementation Evidence間の関係を追跡可能な情報を保持できること
- 新しいImplementation Evidenceから、それがどのImplementation、CorrectionまたはReimplementationに対応するか確認可能であること
- Evidence履歴をたどることでImplementationの変更経過を確認可能であること
- EvidenceのTraceabilityを維持したままPhase 5 Reviewへ必要なEvidenceを渡せること
- 過去のEvidenceを新しいEvidenceで置き換えたように扱わないこと
- EvidenceのImmutabilityを理由としてCorrectionまたはReimplementation後の新しいEvidence生成を妨げないこと
- Evidence Immutability and Traceability処理がImplementationのSpecification適合性を最終判断しないこと
- Evidence Immutability and Traceability処理がReview Resultを決定しないこと

##### Application Layer Interface and Review Handoff

少なくとも以下をTest対象とする。

- UC-08 `Collect Implementation Evidence`をApplication LayerのUseCaseとして呼び出せること
- UC-08のInput DTOを通じてEvidence構築に必要な入力を受け取れること
- Input DTOがApplication Layerと外部境界の情報受け渡しに利用できること
- Evidence収集、RepositoryおよびTest状態の確認、Evidence構築、保存をApplication Layerからオーケストレーションできること
- Infrastructureの具体的な永続化実装へApplication Layerが直接依存しないこと
- Gitに関する具体的な取得処理へApplication Layerが不適切に直接依存しないこと
- CoreからApplication Layerへの逆依存を導入しないこと
- Phase 4で構築されたImplementation EvidenceをOutput DTOまたは同等のApplication Layer境界を通じて返せること
- Phase 5 Reviewが対象Implementation Evidenceを識別できること
- Phase 5 Reviewが対象Specificationを識別または取得可能であること
- Phase 5 Reviewが対象Approved Implementation Planを識別または取得可能であること
- Phase 5 Reviewが対象Codex Promptを識別または取得可能であること
- Phase 5 Reviewが対象Source Codeを確認可能であること
- Phase 5 Reviewが対象Git Diffを確認可能であること
- Phase 5 Reviewが対象Test Codeを確認可能であること
- Phase 5 Reviewが対象Test Resultを確認可能であること
- Phase 5 ReviewがEvidence上のError、Warning、Deviation、未完了事項およびHuman Approval Required事項を確認可能であること
- Phase 5 ReviewへImplementation Evidenceだけでなく、Reviewに必要な実際のArtifactを確認可能な形で引き渡せること
- Evidenceが不足または不整合を含む場合でも、その事実を保持したままPhase 5 Reviewへ引き渡せること
- Phase 4からPhase 5へのHandoff時にEvidenceの内容をReview用に都合よく変更しないこと
- Phase 4からPhase 5へのHandoffがImplementationのSpecification適合性を最終判断しないこと
- Phase 4からPhase 5へのHandoffが`PASS`、`REVISION_REQUIRED`、`HUMAN_REVIEW_REQUIRED`等のReview Resultを決定しないこと
- Phase 4からPhase 5へのHandoffがHuman Approvalを代替しないこと
- Phase 4完了時点で、Phase 5がSpecification、Approved Implementation Plan、Codex Prompt、Implementation Evidence、Source Code、Git Diff、Test CodeおよびTest Resultを用いてReviewを開始可能であること

#### Completion Conditions

Phase 4は、少なくとも以下の条件をすべて満たした場合に完了とする。

- UC-08 `Collect Implementation Evidence`をApplication Layerから実行できること
- Phase 3で取得されたImplementation実行結果と、実際のRepositoryおよびTestの状態を収集・照合できること
- Codex Runnerから返された情報だけに依存せず、実際のSource Code、Git Status、Git Diff、Test CodeおよびTest ResultをEvidence構築の根拠として扱えること
- 対象Implementation、Specification、Approved Implementation Plan、Codex Prompt、Implementation BranchおよびBase Commitを識別できること
- Version 1のImplementation Evidenceを、`identity`、`basis`、`scope`、`changes`、`verification`、`deviations`、`codex_summary`を含む構造化された形式で構築できること
- Implementation Evidenceを正式記録となるJSONとしてSerializationし、`evidence/`配下へ保存・取得・復元できること
- Git DiffをImplementation Evidenceに関連する補助証跡として保存・参照できること
- Evidence JSONとGit Diffとの対応関係を追跡できること
- TDD対象のImplementationについて、作成または変更されたTest、実行Command、初期Test Result、対象Test ResultおよびFull Test Suite ResultをReview可能なEvidenceとして記録できること
- PASS、FAILおよびTechnical Errorを区別して扱えること
- TDDを適用しなかった場合、その理由および必要に応じたHuman判断事項をEvidenceから確認できること
- Codex Runnerの報告と実際のRepositoryまたはTest状態との不一致を検出し、その事実をEvidenceへ記録できること
- Scope外変更、Plan外変更、未完了事項、Error、WarningおよびHuman Approvalが必要な事項を、必要に応じてEvidenceから確認できること
- 不足、不一致または不明な情報を推測によって正常な情報へ補完しないこと
- 関連するApproval Recordを識別可能であり、Human Approvalの正式記録そのものをImplementation Evidenceへ重複して保持しないこと
- Reviewに使用されたImplementation Evidenceを後から上書きまたは変更しないこと
- CorrectionまたはReimplementationが行われた場合、既存Evidenceを保持したまま新しいImplementation Evidenceを生成・保存できること
- 複数世代のImplementation Evidenceおよび関連ArtifactのTraceabilityを維持できること
- Application LayerがEvidence収集、実状態の確認、Evidence構築、保存およびPhase 5へのHandoffをオーケストレーションできること
- Application LayerからInfrastructureの具体実装への不適切な直接依存、およびCoreからApplication Layerへの逆依存を導入していないこと
- Phase 5 ReviewがSpecification、Approved Implementation Plan、Codex Prompt、Implementation Evidence、Source Code、Git Diff、Test CodeおよびTest Resultを確認可能な状態で引き継げること
- Evidenceに不足または不整合が存在する場合でも、その事実を保持したままPhase 5 Reviewへ引き継げること
- Phase 4がImplementationのSpecification適合性を最終判断しないこと
- Phase 4が`PASS`、`REVISION_REQUIRED`、`HUMAN_REVIEW_REQUIRED`等のReview Resultを決定しないこと
- Phase 4がHuman Approvalを代替しないこと
- Phase 4で追加または変更した振る舞いに対するTestが成功すること
- 既存Testを含むFull Test Suiteが成功し、Phase 4の変更によって既存機能を破壊していないこと
- Phase 5 `Review & Correction`がImplementationの検証を開始できる状態になっていること

### Phase 5 Review & Correction

### Phase 6 Final Approval & Merge

### Phase 7 Integration & MVP Completion