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

### Phase 3 Implementation Execution Foundation

### Phase 4 Implementation Evidence

### Phase 5 Review & Correction

### Phase 6 Final Approval & Merge

### Phase 7 Integration & MVP Completion