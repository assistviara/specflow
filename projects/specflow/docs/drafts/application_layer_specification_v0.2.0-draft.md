# SpecFlow Application Layer Specification Draft

Version: 0.2.0-draft  
Target: SpecFlow Version 1 MVP  
Status: Draft / Human Approval Pending

> 本書は、SpecFlow Version 1のApplication Layerに関する
> 正式Specification策定前の検討文書である。
>
> Humanによる承認が完了するまで、
> 実装の根拠として使用してはならない。

---

# 1. Purpose

Application Layerは、SpecFlow Version 1における開発工程全体をUseCaseとして提供する。

Application Layerは、Human、ChatGPT、Codex、および既存Engine群の間を接続し、次の開発サイクルを制御する。

```text
Specification
    ↓
Implementation Plan Draft
    ↓
Human Approval
    ↓
Codex Implementation
    ↓
Implementation Evidence
    ↓
ChatGPT Review
    ↓
Human Final Approval
    ↓
Application-controlled Merge
    ↓
developer
    ↓
completed
```

Application Layerは、AIが自律的に開発を完結させるための層ではない。

Humanの判断と承認を各工程の境界として維持しながら、現在手作業で行っているAI間の成果物受け渡しを自動化する。

---

# 2. Version 1 Scope

## 2.1 AI Role

SpecFlow Version 1では、Application LayerがAI製品を直接処理の責務として扱わず、必要な処理をRoleとして定義する。

各Roleには、Version 1で使用するRunnerを固定して割り当てる。

Version 1では、少なくとも以下のRoleとRunner Assignmentを使用する。

| Role | Assigned Runner | 主な責務 |
| --- | --- | --- |
| Plan Generation Role | ChatGPT Runner | Implementation Plan Draftの生成 |
| Codex Prompt Generation Role | ChatGPT Runner | Codex用Implementation Promptの生成 |
| Implementation Role | Codex Runner | Test作成・変更、Source Code作成・変更、Test実行、実装結果の報告 |
| Implementation Review Role | ChatGPT Runner | Implementationの適合性および逸脱のReview |
| Correction Instruction Role | ChatGPT Runner | Review結果に基づく修正指示の生成 |

Humanによる最終判断および承認はAI Roleには含めない。

```text
AI Role
= AIが担当する処理上の役割

Assigned Runner
= Version 1でそのRoleを実行するRunner

Human
= 承認および最終判断
```

Version 1では、RoleとRunnerの割り当てを固定する。

汎用的な`AIRunner`の構造は維持し、Application LayerのUseCaseが特定のAI製品そのものへ依存する構造とはしない。

Version 1の実行構成では、Claude、Gemini、Local LLM等への動的なRunner切り替えは行わない。

Runnerの動的割り当て、Fallback、および他のAI Runnerの利用は将来の拡張対象とする。

具体的なRoleとRunnerの割り当て方式は、15.13で定義する。

---

## 2.2 MVP Boundary

Version 1 MVPは、次の一本の開発フローを実行可能にする。

```text
HumanがSpecificationを作成
        ↓
HumanがSpecificationを承認
        ↓
ChatGPT RunnerがImplementation Plan Draftを生成
        ↓
HumanがPlanを承認または差し戻し
        ↓
ChatGPT RunnerがCodex用Promptを生成
        ↓
Implementation Branchを準備
        ↓
Codex Runnerが承認された範囲内で実装とテストを実行
        ↓
Implementation Evidenceを構築・保存
        ↓
Source Code・Git Diff・Test Result等をReviewへ提供
        ↓
ChatGPT RunnerがReview
        ↓
必要に応じて修正・再Review
        ↓
Humanが最終承認または差し戻し
        ↓
最終承認されたImplementation Branchをdeveloperへmerge
        ↓
completed
```

Version 1では、複数のAI Runnerを動的に選択する機能、複数ユーザー管理、並列実装、および高度なGit運用は対象外とする。

ただし、Version 1の安全なImplementationおよびReviewに必要な以下のGit操作はMVPに含める。

```text
Implementation Branchの準備
Base Commitの特定
Git Statusの取得
Git Diffの取得
Human Final Approval後のdeveloperへのmerge
```

Version 1では、以下のような高度なGit運用は必須としない。

```text
複数Implementation Branchの並列制御
複雑なBranch Strategy
自動Conflict Resolution
高度なRebase制御
複数Repositoryの統合管理
```

これらはVersion 1 MVPの対象外とし、必要になった場合に将来拡張として検討する。
---

# 3. Application Layer Responsibility

Application Layerは、以下を担当する。

- HumanまたはUIからUseCase実行要求を受け取る
- 現在の開発状態を確認する
- 次に実行可能なUseCaseを制御する
- 必要なEngineおよびAI Runnerを呼び出す
- 各工程の成果物を次工程へ受け渡す
- Humanによる判断をApproval Recordとして記録する
- Approval Recordと現在のArtifactの整合性を確認し、Human Approvalの有効性を検証する
- 有効なHuman Approvalを確認できない場合、承認を必要とする次工程への進行を停止する
- Implementation EvidenceおよびReviewに必要な成果物をReview工程へ渡す
- Review Resultに応じて、次工程、修正工程、またはHuman判断への返却を制御する
- 実行結果と状態遷移を呼び出し元へ返す

---

# 4. Non-Responsibility

Application Layerは、以下を直接実装または独自判断しない。

- Markdown文書の解析
- Prompt Templateの展開
- AI Provider固有の通信
- Codexの内部実装処理
- テストコードの具体的な生成
- Specificationの内容変更
- Implementation Plan Draftの内容生成
- Implementationの適合性に関するReview Resultの生成
- Humanに代わる承認判断

これらは、それぞれ既存Engine、AI Runner、Codex Runner、またはHumanの責務とする。

Application Layerは、これらの処理結果を受け取り、必要な検証、工程制御、状態遷移、および次工程への受け渡しを担当する。

---

# 5. Version 1 MVP Overall Flow

## 5.1 Main Flow

```text
[Human]
Specificationを作成・選択
        ↓
[Application Layer]
Specificationの有効なHuman承認を確認
        ↓
Plan生成UseCaseを開始
        ↓
[ChatGPT Runner]
Implementation Plan Draftを生成
        ↓
[Application Layer]
Plan承認待ちへ遷移
        ↓
[Human]
承認 または 差し戻し
        ↓
承認
        ↓
[ChatGPT Runner]
Codex用Implementation Promptを生成
        ↓
[Application Layer]
Implementation BranchおよびBase Commitを準備
        ↓
実装開始要求をCodex Runnerへ渡す
        ↓
[Codex Runner]
必要に応じてテスト作成
        ↓
TDD対象の場合は期待されるテスト失敗を確認
        ↓
必要最小限の実装
        ↓
対象テストおよび全体テストを実行
        ↓
実装結果をApplication Layerへ返す
        ↓
[Application Layer]
Source Code・Git Status・Git Diff・Test Result等を収集
        ↓
Implementation Evidence JSONを構築
        ↓
Review用入力を構築
        ↓
[ChatGPT Runner]
Specification・Approved Implementation Plan・
Codex Prompt・Implementation Evidence・
Source Code・Git Diff・Test Code・Test ResultをReview
        ↓
[Application Layer]
Review結果を評価
        ↓
[Review Result: APPROVED]
        ↓
最終承認待ちへ遷移
        ↓
[Human]
最終承認 または 差し戻し
        ↓
最終承認
        ↓
[Application Layer]
有効なFinal Approvalおよび対象Implementationを確認
        ↓
MergeApprovedImplementationUseCaseを実行
        ↓
[Git操作Component / Service]
Implementation Branchをdeveloperへmerge
        ↓
[Application Layer]
merge成功を確認
        ↓
completedへ遷移
```

---

## 5.2 TDD Position

Version 1では、振る舞いを変更するImplementationについて、Codexの実装手順としてTDDを原則とする。

```text
Specification
    ↓
期待動作をTestとして表現
    ↓
Test失敗を確認
    ↓
必要最小限のImplementation
    ↓
Test成功を確認
    ↓
既存Testを実行
```

TDDの適用要否は、単純なファイル拡張子ではなく、その変更がSystemの振る舞いを変更するかどうかを本質的な基準として判断する。

`.py`ファイルの変更は、原則としてTest対象とする。

一方、文書修正、コメント修正、その他Systemの振る舞いを変更しない変更については、TDDを必須としない。

TDDはSpecificationに代わるものではない。

Specificationは要求事項の正本であり、TestはSpecificationに定義された期待動作を検証可能な形で表現した成果物として扱う。

TDDの具体的な適用範囲および例外条件は、15.10で定義する。
---

# 6. Required UseCases

## UC-01 Load Development Input

### Purpose

開発対象となるSpecificationおよび関連文書を受け取り、後続工程で利用可能な開発入力として読み込む。

### Input

* Constitution
* Principles
* Specification
* Decisions
* Implementation Plan Template
* Plan Prompt Template
* Project Metadata
* Specification Approval Record



### Output

* 読み込まれたDevelopment Input
* 入力検証結果
* 開発対象識別情報

### Notes

Version 1では、ファイル選択またはPath指定による入力を許容する。

Project全体の自動探索・自動読み込みは必須としない。

後続工程においてHuman Approvalを必要とするArtifactについては、単にファイルが存在することだけをもって承認済みとは判断しない。

必要に応じて、対応するApproval Recordおよび現在のArtifact Hashとの整合性を確認し、有効な承認状態であることを検証する。

Development Inputの読み込みと、Human Approvalの有効性判定は責務を区別する。

Specificationに対するHuman Approvalは、Application Layerが生成または代替するものではない。

Version 1では、HumanがApplication Layerの外部でSpecificationを作成または選択し、その内容を承認する。

Specification Approval Recordは、そのHumanによる承認判断の証拠としてDevelopment InputとともにApplication Layerへ渡される。

Application Layerは、後続工程へ進む前に、現在のSpecificationからArtifact Hashを計算し、Specification Approval Recordに記録された`artifact_hash`との一致を確認する。

Specification Approval Recordが存在しない場合、`decision`が承認を示していない場合、または現在のSpecificationのArtifact Hashと一致しない場合、そのSpecificationを有効に承認済みとして扱ってはならない。

Specification Approvalの判断主体と、その承認の有効性を検証する責務は区別する。

```text
Human
    ↓
Specificationを作成・選択・承認
    ↓
Specification Approval Record
    ↓
Application Layer
    ↓
現在のSpecificationとの同一性を検証
    ↓
有効な場合のみ後続工程へ進行

---

## UC-02 Generate Implementation Plan Draft

### Purpose

Specificationを基にImplementation Plan Draftを生成する。

### Processing

```text
PlanPromptGenerator
    ↓
PromptResult
    ↓
PromptAdapter
    ↓
AIRequest
    ↓
ChatGPT Runner
    ↓
AIResponse
```

### Output

* Implementation Plan Draft
* Plan生成結果
* エラー情報
* 使用したSpecificationの参照

### Completion

生成されたImplementation PlanはDraftとして扱う。

Implementation Planに対する有効なHuman Approvalが確認されるまで、Codex Prompt生成工程へ進んではならない。

単にImplementation Plan Draftが生成されたことをもって、承認済みImplementation Planとして扱ってはならない。

---

## UC-03 Request Plan Approval

### Purpose

Implementation Plan DraftをHumanへ提示し、承認、修正依頼、または中止の判断を受け取る。

### Input

- Implementation Plan Draft
- 対象Implementation PlanのPath
- 必要に応じて関連するSpecificationおよびPlan生成情報

### Human Actions

- 承認
- 修正依頼
- 中止

### Approval Record

Humanの判断は、15.4で定義したApproval Recordとして`approvals/`配下へ保存する。

Approval Recordを生成する際、Application Layerは承認対象となる現在のImplementation PlanからArtifact Hashを計算し、その値を`artifact_hash`として記録する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```
Implementation Planを承認する場合、概念的には以下のようなApproval Recordを生成する。

```json
{
  "approval_id": "plan_approval_001",
  "artifact_type": "implementation_plan",
  "artifact_path": "<Implementation Plan path>",
  "artifact_hash": "<SHA-256 hash>",
  "decision": "approved",
  "approved_at": "<timestamp>",
  "comment": ""
}
```

修正依頼の場合は、`decision`に修正要求を示す値を記録し、Humanによる修正理由または要求内容を`comment`へ記録する。

中止の場合は、`decision`に中止を示す値を記録する。

### Approval Validation

HumanがImplementation Planを承認した場合、その承認は承認時点の特定内容のImplementation Planに対してのみ有効とする。

後続工程へ進む前に、Application Layerは現在のImplementation PlanからHashを計算し、Approval Recordに保存された`artifact_hash`と比較する。

```text
Approval Record
artifact_hash
        │
        │ compare
        │
Current Implementation Plan
current_hash
```

Hashが一致し、かつ`decision`が承認を示している場合にのみ、現在のImplementation Planを有効に承認済みとして扱う。

承認後にImplementation Planが変更されHashが一致しなくなった場合、以前のApproval Recordを現在のImplementation Planに対する有効な承認として扱ってはならない。

### Output

- Human Decision
- Approval Record
- 承認有効性に関する情報
- 修正依頼内容
- 中止情報

### Transition

Humanが有効に承認した場合は、`plan_approved`へ遷移し、Codex Prompt生成工程へ進むことができる。

修正依頼の場合は、`plan_revision_requested`へ遷移し、Implementation Plan修正工程へ戻る。

中止の場合は、`cancelled`へ遷移する。

### Rule

Application LayerまたはAI RunnerがHumanの代わりにImplementation Planを承認してはならない。

単に`state.json`が`plan_approved`であることや、Implementation Plan本文に承認済み表記が存在することだけを根拠として、有効なHuman Approvalと判断してはならない。

有効な承認の判断には、HumanによるApproval Recordと現在のImplementation PlanのArtifact Hashの一致を必要とする。

---

## UC-04 Revise Implementation Plan

### Purpose

Humanからの修正依頼を基にImplementation Plan Draftを再生成する。

### Input

- 現在のImplementation Plan Draft
- Humanの修正理由または修正要求
- 元のSpecification
- 関連文書

### Output

- 修正版Implementation Plan Draft
- 変更点
- 前版との対応情報

### Transition

修正版Implementation Plan Draftを生成した後は、`plan_approval_pending`へ遷移し、再びHuman Approvalを求める。

### Rule

修正版Implementation Plan Draftは、新しい承認対象Artifactとして扱う。

以前のImplementation Planに対するApproval Recordを、修正版Implementation Planに対する有効な承認として引き継いではならない。

修正版Implementation Planを後続工程で使用するためには、UC-03で定義したApproval Validationに従い、新たなHuman Approvalを取得しなければならない。

---

## UC-05 Generate Codex Implementation Prompt

### Purpose

Approved Implementation Planを基に、Implementation Roleを実行するCodex Runnerへ渡すImplementation Promptを生成する。

Codex Promptは、Codex RunnerがHumanによって承認された範囲内でImplementationを実行できるよう、実装対象、許可された変更範囲、TDDルール、完了条件、および停止条件を明示する。

### Input

- 承認済みSpecification
- 承認済みImplementation Plan
- 実装対象Path
- TDD実行ルール
- 完了条件
- 停止条件
- Implementation Evidence生成に必要な実行結果の報告要件

### Processing

Codex Prompt Generation Roleを実行し、Version 1で割り当てられたChatGPT RunnerによってCodex用Implementation Promptを生成する。

Promptには、必要に応じて以下を明示する。

```text
Implementation Scope
Allowed Changes
Forbidden Changes
TDD Requirements
Completion Conditions
Stop Conditions
Required Execution Result Reporting
Human Approval Required Conditions
```

Codex RunnerがSpecificationまたはApproved Implementation Planに存在しない事項を独自に補完することを前提としてはならない。

### Output

- Codex用Implementation Prompt
- 使用したSpecificationの参照
- 使用したApproved Implementation Planの参照
- Prompt生成結果

### Rule

有効に承認されていないSpecificationまたはImplementation Planを基にCodex Promptを生成してはならない。

承認の有効性は、単に承認済み状態が記録されていることだけで判断せず、対応するApproval Recordおよび現在のArtifact Hashとの整合性を確認する。

Codex Promptは、SpecificationおよびApproved Implementation Planで承認されたImplementation Scopeを拡張してはならない。

承認範囲を超える変更が必要となる可能性がある場合は、Codex Runnerが独自に判断して実行するのではなく、Human Approvalを要求する条件としてPromptに明示する。

Codex Promptは、Codex Runner自身にImplementation Evidenceの正当性を自己確定させてはならない。

Codex Runnerには、Implementation Evidenceを構築するために必要な実行結果を報告させる。

最終的なImplementation Evidenceは、Application LayerがCodex Runnerの実行結果と実際のSource Code、Git Status、Git Diff、およびTest Result等を収集して構築する。

生成されたCodex Promptは、どのSpecificationおよびApproved Implementation Planを基に生成されたかを後続工程で識別可能でなければならない。

---

## UC-06 Execute Implementation

### Purpose

Implementation Roleに割り当てられたCodex Runnerを使用し、Approved Implementation PlanおよびCodex Promptで承認された範囲内のImplementationとTestを実行する。

### Input

- Specification
- Approved Implementation Plan
- Codex Prompt
- Implementation Branch
- Base Commit

### Processing

Implementationの内容に応じて、15.10で定義したTDD適用ルールに従う。

```text
Codex Prompt
        ↓
Implementation Scopeを確認
        ↓
TDD適用要否を確認
        ↓
┌─ TDD対象
│      ↓
│  必要なTestを作成・変更
│      ↓
│  期待されるTest失敗を確認
│      ↓
│  必要最小限のImplementation
│
└─ TDD対象外
       ↓
   承認された範囲内で必要なImplementation
        ↓
対象Testを実行
        ↓
必要な既存Testを実行
        ↓
実装結果をApplication Layerへ返す
```

TDDの適用要否は、単純なファイル拡張子ではなく、変更がSystemの振る舞いを変更するかどうかを本質的な基準として判断する。

`.py`ファイルの変更は原則としてTest対象とする。

文書修正、コメント修正、その他Systemの振る舞いを変更しない変更については、TDDを必須としない。

### Output

- Codex Runner実行結果
- 作成・変更・削除したファイルに関する情報
- 実行したCommandに関する情報
- Test実行結果
- ErrorおよびWarning
- 未完了事項
- Human Approvalが必要な事項
- 成功または失敗

### Rule

Codex Runnerは、Specification、Approved Implementation Plan、およびCodex Promptによって承認された範囲を超える変更を行ってはならない。

承認範囲を超える変更が必要であると判断した場合、Codex Runnerは独自に変更を実行せず、Human Approvalが必要な事項としてApplication Layerへ返す。

Codex RunnerはImplementation Evidenceの正当性を自己確定してはならない。

Application LayerはCodex Runnerから返された実装結果に加え、実際のSource Code、Git Status、Git Diff、およびTest Result等を収集し、Implementation Evidenceを構築する。

承認範囲を超える変更がUC-07で定義したCritical Changeに該当する場合、Application LayerはImplementationを継続させず、`critical_approval_pending`へ遷移してUC-07 `Request Critical Change Approval`へ処理を渡す。

Critical Changeに対する有効なHuman Approvalが確認されるまで、Codex Runnerは当該変更を含むImplementationを再開してはならない。

---

## UC-07 Request Critical Change Approval

### Purpose

Codex RunnerによるImplementation中に、承認済みのSpecification、Approved Implementation Plan、Codex Prompt、または既存のHuman Approval Scopeを超える重要変更が必要になった場合、Implementationを停止し、Humanへ判断を求める。

Critical Changeは、Codex RunnerまたはApplication Layerが独自判断で実行してはならない。

### Input

- 対象Implementation
- Implementation Branch
- Specification
- Approved Implementation Plan
- Codex Prompt
- Critical Changeの内容
- Critical Changeが必要となった理由
- 変更対象および影響範囲
- 現在のState
- 必要に応じて関連するImplementation Evidence

### Critical Changes

少なくとも以下の変更をCritical Changeとして扱う。

- DB変更
- 認証変更
- 権限変更
- 外部API変更
- 依存ライブラリ変更
- PKL互換性を損なう変更
- データ消失の可能性がある変更
- その他の破壊的変更
- SpecificationまたはApproved Implementation Planに記載されていない変更
- 既存のHuman Approval Scopeを超える変更

### Human Actions

- 承認してImplementationを続行
- 修正を依頼
- Specificationの再検討へ戻す
- Implementation Planの再検討へ戻す
- Implementationを中止

### Approval Record

HumanによるCritical Changeへの判断は、15.4で定義したApproval Recordとして記録する。

Critical Change Approvalでは、Humanへ提示する変更内容、変更理由、対象Implementation、変更対象、および影響範囲をCritical Change Requestとして構築・保存し、承認対象Artifactとして扱う。

Application Layerは、Humanへ判断を求める前にCritical Change Requestを識別可能なArtifactとして確定し、そのArtifactからHashを計算する。

Approval Recordには、少なくとも以下を保持する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```

Critical Change Approval Recordの`artifact_path`および`artifact_hash`は、承認対象となったCritical Change Requestを参照する。

Critical Changeを承認する場合、その承認はHumanへ提示された特定のCritical Change Requestおよび対象Implementationに対してのみ有効とする。

Application Layerは、Critical Change承認後にImplementationを再開する前に、現在のCritical Change RequestからHashを計算し、Approval Recordに保存された`artifact_hash`と比較する。

```text
Approval Record
artifact_hash
        │
        │ compare
        │
Current Critical Change Request
current_hash
```

Hashが一致し、かつ`decision`が承認を示している場合にのみ、そのCritical Change Approvalを有効として扱う。

Critical Change Requestの内容がHuman承認後に変更されHashが一致しなくなった場合、以前のApproval Recordを変更後のCritical Changeに対する有効な承認として扱ってはならない。

対象Implementationが承認時点から変更され、Critical Change Requestに記録された対象Implementationとの同一性を確認できない場合も、以前のApproval Recordを有効な承認として扱ってはならない。

### Transition

Critical Changeが検出された場合は、`critical_approval_pending`へ遷移する。

HumanがCritical Changeを有効に承認した場合は、承認された範囲内で`implementing`へ戻り、Implementationを再開できる。

修正依頼の場合は、`correction_requested`へ遷移し、指定された修正工程へ戻る。

SpecificationまたはImplementation Planの再検討が必要な場合は、それぞれ対応する策定・修正工程へ戻る。

中止の場合は、`cancelled`へ遷移する。

```text
implementing
        ↓
critical_approval_pending
        │
        ├── 承認
        │      ↓
        │  implementing
        │
        ├── 修正
        │      ↓
        │  correction_requested
        │
        ├── Specification / Plan再検討
        │      ↓
        │  指定された工程
        │
        └── 中止
               ↓
           cancelled
```

### Output

- Human Decision
- Critical Change Approval Record
- 承認有効性に関する情報
- 承認された変更範囲
- 修正要求
- 再検討対象
- 中止情報

### Rule

Humanによる有効な承認が確認される前に、Critical Changeを実行してはならない。

Critical Change Approvalは、提示された特定の変更内容に対する承認であり、Specification、Approved Implementation Plan、またはImplementation全体を包括的に変更する権限をCodex Runnerへ与えるものではない。

Codex Runner、Application Layer、またはAI RunnerがHumanの代わりにCritical Changeを承認してはならない。

有効なCritical Change Approvalを確認した場合でも、Implementationは承認された変更範囲内でのみ再開できる。

---

## UC-08 Collect Implementation Evidence

### Purpose

Codex RunnerによるImplementationの実行結果と、実際のRepositoryおよびTestの状態を収集し、Review工程で検証可能なImplementation Evidenceを構築する。

Implementation Evidenceは、Codex Runnerの自己申告のみを根拠として生成してはならない。

Application Layerは、Codex Runnerから返された実行結果と実際の成果物を照合し、第9章で定義した形式に従ってImplementation Evidenceを構築する。

### Input

- Codex Prompt
- Codex Runner実行結果
- Specification
- Approved Implementation Plan
- Implementation Branch
- Base Commit
- Source Code
- Git Status
- Git Diff
- Test Code
- Test Result
- 実行したCommandに関する情報
- ErrorおよびWarning
- 未完了事項
- Human Approvalが必要な事項

### Processing

Application Layerは、Codex Runnerから返された情報に加え、可能な範囲で実際のRepositoryおよびTestの状態を取得し、Implementation Evidenceを構築する。

概念的な処理は、以下とする。

```text
Codex Runner実行結果
        │
        ├──────────────┐
        │              │
        ↓              ↓
Repository情報      Test情報
        │              │
        ├──────┬───────┤
        │      │       │
        ↓      ↓       ↓
Git Status  Git Diff  Test Result
        │      │       │
        └──────┴───────┘
               ↓
      Application Layer
               ↓
      情報の収集・関連付け
               ↓
   Implementation Evidence JSON
```

Application Layerは、少なくとも以下を確認する。

- 対象Implementationを識別できる
- 使用したSpecificationを識別できる
- 使用したApproved Implementation Planを識別できる
- 使用したCodex Promptを識別できる
- Implementation BranchおよびBase Commitを識別できる
- 作成・変更・削除されたファイルを確認できる
- Git Diffを取得または参照できる
- 実行したTestおよびその結果を確認できる
- Error、Warningおよび未完了事項を記録できる
- Human Approvalが必要な事項を記録できる
- 使用したCodex Promptが、対象SpecificationおよびApproved Implementation Planに対応するPromptであることを確認できる

Codex Runnerから返された情報と実際のRepositoryまたはTestの状態に不一致がある場合、その不一致を無視してEvidenceを正常として扱ってはならない。

不一致は、Error、Warning、Deviation、またはHuman Approvalが必要な事項として、内容に応じて記録する。

### Output

- Implementation Evidence JSON
- 関連するGit Diff
- Evidence構築結果
- Evidence不足または不整合に関する情報
- Human Approvalが必要な事項

### Rule

Implementation Evidenceの正式フォーマット、Required Information、保存方法、およびImmutabilityは第9章の定義に従う。

Codex Runner自身がImplementation Evidenceの正当性を自己確定してはならない。

Application LayerはImplementation Evidenceを構築する責務を持つが、Implementationの適合性を最終判断してはならない。

Implementationの適合性は、UC-09 `Review Implementation`においてReviewする。

Review開始後は、対象となるImplementation Evidenceを上書きしてはならない。

Correctionまたは再Implementationを行った場合は、第9章のImmutability Ruleに従って新しいImplementation Evidenceを生成する。

---

## UC-09 Review Implementation

### Purpose

承認済みの要求・実装計画と実際のImplementation結果を照合し、ImplementationがSpecificationおよびApproved Implementation Planに適合しているかを評価する。

Reviewは、単にTestが成功しているかを確認する工程ではない。

以下の観点から、Implementationの完全性、正確性、および承認範囲からの逸脱の有無を検証する。

```text
要求されたものが実装されているか

要求されていないものが追加されていないか

承認された範囲外の変更が行われていないか

必要なTestが存在するか

既存の振る舞いを不必要に変更していないか

未完了事項、Error、Warning等が残っていないか

Human Approvalを必要とする変更が含まれていないか
```

---

### Input

Reviewでは、少なくとも以下を参照する。

- Specification
- Approved Implementation Plan
- Codex Prompt
- Implementation Evidence
- Source Code
- Git Diff
- Test Code
- Test Result

Implementation EvidenceのみをReviewの根拠としてはならない。

Implementation Evidenceに記録された内容と、実際のSource Code、Git Diff、Test Code、およびTest Resultを相互に比較する。

Review開始前に、Specification、Approved Implementation Plan、Codex Prompt、Implementation Evidence、Implementation Branch、および関連するGit Diff等が、同一の対象Implementationに対する一連のArtifactとして対応していることを確認する。

Review対象Artifact間の対応関係を確認できない場合、その不整合を無視してReviewを継続し、`APPROVED`としてはならない。

---

### Review Scope

Reviewでは、少なくとも以下を確認する。

#### Requirement Compliance

- Specificationで要求されたImplementationが不足していないか
- Specificationで定義された期待動作を満たしているか
- Approved Implementation Planで要求された項目が実装されているか

#### Scope Compliance

- Codex Promptで指定された実装範囲を逸脱していないか
- SpecificationまたはApproved Implementation Planに存在しないImplementationが追加されていないか
- 不要なファイルが作成、変更、または削除されていないか
- 修正対象以外のSource Codeへ不要な変更が加えられていないか
- Human Approvalを必要とする変更が承認なしに行われていないか

#### Implementation Compliance

- Implementationが要求された振る舞いを実現しているか
- 必要な処理が欠落していないか
- 不必要な処理が追加されていないか
- 修正によって既存の正常なImplementationを不必要に変更していないか

#### Test Compliance

- 必要なTestが作成または更新されているか
- TDD対象のImplementationについて、期待される振る舞いを検証するTestが存在するか
- 対象Testが成功しているか
- 既存Testを含む全体Testが成功しているか
- TestがSpecificationまたはApproved Implementation Planで要求された振る舞いを適切に検証しているか

#### Evidence Compliance

- Implementation Evidenceに必要な情報が存在するか
- Implementation Evidenceと実際のGit Diffが一致しているか
- Implementation Evidenceに記録された変更ファイルと実際の変更ファイルが一致しているか
- Test ResultがImplementation Evidenceの記録と一致しているか
- Error、Warning、未完了事項が適切に記録されているか
- Specification、Approved Implementation Plan、Codex Prompt、Implementation Evidence、およびGit Diff等の対応関係が確認できるか

---

### Review Method

Review対象が一括Reviewに適した範囲である場合は、一括Reviewを行うことができる。

Review対象が大きく、一括Reviewによって重要な情報の欠落、比較精度の低下、またはContext上限への接近が予想される場合は、15.9で定義したSemantic Staged Reviewを使用する。

Semantic Staged Reviewでは、Review対象を単純な文字数やファイル数のみで機械的に分割せず、意味上の責務単位に分けてReviewする。

基本的なReview Stageは、以下とする。

```text
Requirement Review
        ↓
Change Scope Review
        ↓
Implementation Review
        ↓
Test Review
        ↓
Integration Review
```

#### Requirement Review

SpecificationおよびApproved Implementation Planから、今回のImplementationで満たすべき要求を確認する。

#### Change Scope Review

Codex Prompt、Implementation Evidence、およびGit Diffを比較し、承認された変更範囲を逸脱していないかを確認する。

#### Implementation Review

Source CodeおよびGit Diffを確認し、要求されたImplementationが正しく実現されているか、不足または不要な変更が存在しないかを確認する。

#### Test Review

Test CodeおよびTest Resultを確認し、要求された振る舞いが適切に検証されているか、既存の振る舞いが維持されているかを確認する。

#### Integration Review

各Review Stageの結果を統合し、Implementation全体としての適合性を判断する。

個別Stageが適合していても、Stage間の整合性に問題がある場合は、Implementation全体を適合として扱ってはならない。

---

### Review Result

Review結果は、少なくとも以下のいずれかとして扱う。

```text
APPROVED
REVISION_REQUIRED
HUMAN_REVIEW_REQUIRED
```

#### APPROVED

Specification、Approved Implementation Plan、および承認されたImplementation Scopeに適合し、Review上の重大な問題が確認されない場合。

#### REVISION_REQUIRED

承認された範囲内で修正可能なImplementation上の問題が確認された場合。

#### HUMAN_REVIEW_REQUIRED

以下のような、Application LayerまたはAI Runnerのみでは判断してはならない問題が確認された場合。

```text
Specificationの不足・矛盾・不明確さ

Approved Implementation Plan自体の変更が必要

承認範囲を超える変更が必要

Critical Changeが必要

Humanによる設計判断が必要

安全に自動修正を継続できない
```

---

### Output

Reviewは、少なくとも以下を出力する。

- Review Report
- Review Result
- 適合または不適合となった項目
- 不適合箇所
- 判断根拠
- 修正対象
- 修正工程の返却先
- Humanへの確認事項
- 未解決事項

`REVISION_REQUIRED`の場合は、後続のCorrection Instructionおよび修正ループで利用できるよう、修正対象とその根拠を明確にする。

`HUMAN_REVIEW_REQUIRED`の場合は、AIが判断を補完せず、Humanが判断すべき事項を明確にして処理を返す。

---

### Rule

ReviewはSpecification自体を変更してはならない。

ReviewはApproved Implementation Plan自体を変更してはならない。

Reviewは、CodexがImplementation Evidence内に記述した自己評価のみを根拠としてはならない。

以下を相互に比較して判断する。

```text
Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Code
Test Result
```

CodexがImplementation Evidence内で、

```text
out_of_scope_changes = []
```

等と報告していても、Git DiffまたはSource Codeに承認範囲外の変更が確認された場合は、Review側で逸脱として検出する。

同様に、SpecificationまたはApproved Implementation Planで要求されたImplementationが、Source Code、Git Diff、Test Code、またはTest Resultから確認できない場合は、Implementation不足として扱う。

ReviewによってSpecification、Approved Implementation Plan、またはHuman Approval Scopeそのものの変更が必要と判断された場合は、Review側で変更してはならない。

その場合は、

```text
HUMAN_REVIEW_REQUIRED
```

として、対応する工程またはHumanへ判断を返す。

Review結果が`REVISION_REQUIRED`の場合は、15.11で定義した修正ループの規則に従う。

自動修正を行う場合であっても、修正回数上限、Early Stop Condition、Convergence Detection、およびHuman Escalationの規則を無視してはならない。
---

## UC-10 Request Final Approval

### Purpose

Review ReportをHumanへ提示し、対象Implementationを`developer`へ取り込んでよいかについて最終判断を受け取る。

### Input

- Review Report
- Review Result
- 対象Implementation Branch
- Base Commit
- 現在のHEAD Commit
- Implementation Evidence
- Git Diff
- 対象Implementationを識別する情報
- 必要に応じて関連するApproval Record

### Human Actions

- 最終承認
- 実装修正へ戻す
- Plan修正へ戻す
- Specification再検討へ戻す
- 中止

### Approval Record

Humanによる最終判断は、15.4で定義したApproval Recordとして`approvals/`配下へ保存する。

最終承認の場合、Approval Recordには少なくとも以下を保持する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```

最終承認時には、Humanが承認した対象Implementationを一意に識別できる情報およびArtifact HashをApproval Recordへ記録する。

Final Approvalにおける承認対象ArtifactおよびArtifact Hashの算出対象は、15.4で定義した方式に従い、承認時とmerge開始前で同一の規則を使用する。

概念的には、以下のようなApproval Recordを生成する。

```json
{
  "approval_id": "final_approval_001",
  "artifact_type": "implementation",
  "artifact_path": "<approved implementation reference>",
  "artifact_hash": "<SHA-256 hash>",
  "decision": "approved",
  "approved_at": "<timestamp>",
  "comment": ""
}
```

### Approval Validation

Humanによる最終承認は、承認時点の特定のImplementationに対してのみ有効とする。

merge工程へ進む前に、Application Layerは現在の対象ImplementationとApproval Recordに記録された承認対象が一致していることを確認する。

少なくとも以下を確認する。

```text
Final Approval Recordが存在する

decisionが承認を示している

対象Implementation Branchが一致する

対象ImplementationのHEAD Commitが承認時点と一致する

対象Implementationが承認された内容と一致する

Approval Recordのartifact_hashと
現在の対象Implementationについて
同一の算出規則で計算したArtifact Hashが一致する
```

いずれかの条件を満たさない場合、そのFinal Approvalを現在のImplementationに対する有効な承認として扱ってはならない。

### Output

- Human Decision
- Final Approval Record
- 承認有効性に関する情報
- 修正要求
- 中止情報

### Transition

Humanが最終承認し、そのApproval Recordが現在の対象Implementationに対して有効であることを確認できた場合、Application Layerは`MergeApprovedImplementationUseCase`へ進むことができる。

実装修正が選択された場合は、対応するImplementation修正工程へ戻る。

Plan修正が選択された場合は、Implementation Plan修正工程へ戻る。

Specification再検討が選択された場合は、Specification策定工程へ戻る。

中止の場合は、`cancelled`へ遷移する。

### Rule

Application LayerまたはAI RunnerがHumanの代わりにFinal Approvalを行ってはならない。

Humanによる最終承認のみをもって`completed`へ遷移してはならない。

有効なFinal Approvalを確認した後、15.14で定義したmerge工程を実行し、対象Implementation Branchの`developer`へのmergeが正常に完了した場合にのみ`completed`へ遷移できる。

merge開始前に、Approval Recordと現在の対象Implementationの整合性を確認しなければならない。

---

## UC-11 Resume Correction

### Purpose

Review結果またはHumanによる差し戻しを受け、問題の種類および承認範囲に応じて、適切な修正工程へ処理を戻す。

UC-11は修正内容そのものを決定または実装するUseCaseではなく、Review Report、Review Result、Human Decision、および現在の状態を基に、再開すべき工程を決定する。

### Input

- Review Report
- Review Result
- Human Decision
- 現在のState
- 対象Implementation
- 必要に応じて関連するApproval Record
- 修正対象および修正理由
- 修正回数およびEarly Stop情報

### Return Destination

| 問題 | 戻り先 |
| --- | --- |
| Specification不足・矛盾・不明確さ | Specification策定工程 |
| Implementation Plan不備 | Plan修正工程 |
| Codex用Prompt不備 | Prompt再生成工程 |
| Implementation不備 | Codex再実装工程 |
| Test不足・誤り | Test修正工程 |
| Humanによる設計判断が必要 | Human判断 |
| 承認範囲を超える変更が必要 | Human判断 |
| Critical Changeが必要 | Critical Change Approval工程 |
| 自動修正を安全に継続できない | Human判断 |

### Processing

Review Resultが`REVISION_REQUIRED`の場合は、15.11で定義したCorrection Loopおよび停止条件を確認する。

自動修正可能であり、修正回数が上限未満で、Early Stop Conditionに該当しない場合は、Review Reportで指定された修正対象に応じた工程へ戻す。

```text
REVISION_REQUIRED
        ↓
Correction条件確認
        ↓
修正可能
        ↓
Return Destinationを決定
        ↓
指定された修正工程
```

Review Resultが`HUMAN_REVIEW_REQUIRED`の場合は、自動的に修正工程を選択して進行してはならない。

```text
HUMAN_REVIEW_REQUIRED
        ↓
Human判断
        ↓
Humanが指定した工程へ再開
```

HumanによるFinal Approval Rejectionまたはその他の差し戻しの場合は、Humanが指定した修正理由および戻り先に従う。

### Output

- Return Destination
- 次に実行可能なUseCase
- 修正理由
- Human判断が必要かどうか
- 再開可能なState
- 停止情報

### Rule

UC-11は、Specification、Approved Implementation Plan、またはHuman Approval Scopeを独自に変更してはならない。

`HUMAN_REVIEW_REQUIRED`の場合、Application LayerがHumanの代わりに修正方針を確定してはならない。

自動修正を再開する場合は、15.11で定義した最大修正回数、Early Stop Condition、Convergence Detection、およびHuman Escalationの規則に従う。

修正後に再Reviewを行う場合は、第9章で定義した新しいImplementation Evidenceを生成し、以前のEvidenceを上書きしてはならない。

修正によってHuman Approvalの対象Artifactが変更された場合、変更前のApproval Recordを変更後のArtifactに対する有効な承認として引き継いではならない。

UC-11は修正工程へ処理を戻す際、修正によって再取得が必要となるHuman Approvalを識別し、対応するApproval工程を経ずに後続工程へ進行させてはならない。
---

## UC-12 Merge Approved Implementation

### Purpose

Humanによって最終承認されたImplementationについて、Final Approvalの有効性および対象Implementationの同一性を確認した上で、Implementation Branchを`developer`へmergeする。

UC-12はHumanによるFinal Approvalを代替するUseCaseではなく、有効なFinal Approvalを前提として承認済みImplementationを`developer`へ取り込む工程を実行する。

### Input

- 対象Implementation Branch
- Base Commit
- 現在のHEAD Commit
- Final Approval Record
- Final Approval Target Artifact
- Implementation Evidence
- Review Report
- Review Result
- 現在のState
- 必要に応じてGit StatusおよびGit Diff

### Precondition

merge開始前に、少なくとも以下を確認する。

```text
Review ResultがAPPROVEDである

有効なFinal Approval Recordが存在する

Final Approval Recordのdecisionが承認を示している

Final Approval Target Artifactが存在する

対象Implementation Branchが承認時点と一致する

HEAD Commitが承認時点と一致する

Final Approval Recordのartifact_hashと
現在のFinal Approval Target Artifactから
同一の算出規則で計算したArtifact Hashが一致する
```

いずれかの条件を満たさない場合、mergeを開始してはならない。

### Processing

概念的な処理は、以下とする。

```text
Final Approval Record
        +
Final Approval Target Artifact
        +
Current Implementation
        ↓
Approval Validation
        ↓
対象Implementationの同一性確認
        ↓
merge実行可能性確認
        ↓
Implementation Branch
        ↓
developerへmerge
        ↓
merge結果確認
        │
        ├── 成功
        │      ↓
        │  completed
        │
        └── 失敗
               ↓
           completedへ遷移しない
               ↓
           Human判断へ返す
```

Git操作そのものは、Application Layerが直接実装するのではなく、Git操作を担当するComponentまたはServiceを利用する。

### Output

- Merge Result
- merge対象Implementation
- merge元Branch
- merge先Branch
- merge後Commitに関する情報
- ErrorおよびWarning
- Human判断が必要な事項
- 遷移可能なState

### Transition

mergeが正常に完了し、対象Implementationが`developer`へ正しく取り込まれたことを確認できた場合にのみ、`completed`へ遷移する。

mergeに失敗した場合は、`completed`へ遷移してはならない。

merge conflict、Repository状態の不整合、承認対象との不一致、その他安全に自動継続できない問題が確認された場合は、自動的に問題を解消したものとして処理せず、必要な情報を記録してHumanへ判断を返す。

### Rule

Humanによる有効なFinal Approvalが確認される前にmergeを実行してはならない。

Final Approval後に対象Implementation Branch、HEAD Commit、Final Approval Target Artifact、または承認対象の内容が変更された場合、以前のFinal Approvalを現在のImplementationに対する有効な承認として使用してはならない。

UC-12は、Final Approvalの対象となったImplementationを変更してはならない。

mergeのためにImplementation自体の修正が必要となった場合は、承認済みImplementationを直接修正してmergeを継続せず、適切な修正工程へ処理を戻す。

merge成功の確認前に`completed`へ遷移してはならない。

---



# 7. Human Approval Points

Version 1では、少なくとも以下のHuman承認ポイントを設ける。

## Approval Point 1: Specification

SpecificationはHumanが作成または承認する。

Application Layerは、Specificationに対する有効なHuman Approvalを確認できない限り、Plan生成工程へ進んではならない。

Specification Approvalの有効性は、対応するApproval Recordと現在のSpecificationのArtifact Hashが一致することによって確認する。

---

## Approval Point 2: Implementation Plan

ChatGPT Runnerが生成したImplementation Plan DraftをHumanが確認する。

Application Layerは、Implementation Planに対する有効なHuman Approvalを確認できない限り、Codex Prompt生成工程へ進んではならない。

Implementation Plan Approvalの有効性は、UC-03および15.4で定義したApproval Recordと現在のImplementation PlanのArtifact Hashが一致することによって確認する。

---

## Approval Point 3: Critical Change

Codex RunnerによるImplementation中にCritical Changeが必要となった場合、Implementationを停止してHumanへ判断を求める。

HumanによるCritical Changeへの判断は、UC-07および15.4で定義したCritical Change Requestを承認対象Artifactとして記録する。

Critical Change Requestに対する有効なApproval Recordが確認されない限り、Critical Changeを実行してはならない。

HumanがCritical Changeを承認した場合でも、Implementationは承認された変更範囲内でのみ再開できる。

---

## Approval Point 4: Final Review

ChatGPTによるReview ReportをHumanが確認し、Implementationを`developer`へ取り込んでよいかを最終判断する。

Humanによる最終承認がない限り、承認済みImplementationを`developer`へmergeしてはならない。

Humanによる最終承認後、Application Layerは15.14で定義したmerge工程を開始する。

対象Implementation Branchの`developer`へのmergeが正常に完了した場合にのみ、開発状態を`completed`へ遷移できる。

Humanによる最終承認のみをもって`completed`としてはならない。

mergeに失敗した場合は`completed`へ遷移してはならない。

---

# 8. Correction Loops

## 8.1 Plan Correction Loop

```text
Plan Draft
    ↓
Human Review
    ↓
未承認
    ↓
修正理由入力
    ↓
ChatGPTによるPlan再生成
    ↓
Plan Draft
```

各版のPlanは上書きせず、履歴を残す。

---

## 8.2 Implementation Correction Loop

ImplementationまたはReviewにおいて修正が必要となった場合は、
Review Resultおよび停止条件に基づき、自動修正を継続できるかを判断する。

```text
Codex Implementation
    ↓
Test実行
    ↓
Implementation Evidence構築
    ↓
ChatGPT Review
    ↓
Review Result
    │
    ├── APPROVED
    │       ↓
    │   Human Final Approvalへ
    │
    ├── REVISION_REQUIRED
    │       ↓
    │   異常・停止条件確認
    │       │
    │       ├── 自動修正可能
    │       │       ↓
    │       │   修正回数確認
    │       │       │
    │       │       ├── 上限未満
    │       │       │       ↓
    │       │       │   修正指示生成
    │       │       │       ↓
    │       │       │   Codex再実装
    │       │       │       ↓
    │       │       │   再テスト
    │       │       │       ↓
    │       │       │   新しいImplementation Evidence構築
    │       │       │       ↓
    │       │       │   Re-Review
    │       │       │
    │       │       └── 上限到達
    │       │               ↓
    │       │           Human判断へ返す
    │       │
    │       └── Early Stop Condition
    │               ↓
    │           Human判断へ返す
    │
    └── HUMAN_REVIEW_REQUIRED
            ↓
        Human判断へ返す
```

---

## 8.3 Specification Return Loop

Specificationの不足・矛盾・不明確さが原因の場合、Application Layerは処理を停止する。

```text
Implementation / Review
    ↓
Specification問題を検出
    ↓
Humanへ返却
    ↓
Specification策定工程
```

AIが推測でSpecificationを補完してはならない。

---

## 8.4 Retry Limit

Version 1では、自動修正の回数を記録する。

初回Implementationは修正回数に含めず、ChatGPT Reviewによる`REVISION_REQUIRED`を受けてCodexが修正を実行した時点で、1回の修正として数える。

自動修正の最大回数は、原則として3回とする。

ただし、最大回数は自動修正を必ず3回まで実行することを意味しない。

修正過程において、異常、悪化、非収束、承認範囲外変更等のEarly Stop Conditionを検出した場合は、最大回数へ到達する前であっても自動修正を停止する。

基本原則は、以下とする。

```text
正常に収束している
        ↓
最大回数の範囲内で自動修正を継続

異常・悪化・非収束を検出
        ↓
Early Stop
        ↓
Humanへ判断を返す

最大修正回数へ到達
        ↓
自動修正停止
        ↓
Humanへ判断を返す
```

Humanによる新たな判断なしに、自動修正回数の上限を解除してはならない。

具体的なEarly Stop Condition、Convergence Detection、およびHuman Escalationの規則は、15.11で定義する。

---

# 9. Implementation Evidence

## 9.1 Purpose

Implementation Evidenceは、Implementationにおいて何が行われたかをReview可能にするための構造化された証拠である。

単なるデバッグログやCodex Runnerによる自己申告ではなく、Specification、Approved Implementation Plan、Codex Prompt、Source Code、Git Diff、およびTest Resultを結びつける追跡情報として扱う。

Implementation Evidenceは、Application LayerおよびChatGPT Reviewが、Implementationの適合性、完全性、および承認範囲からの逸脱を検証するために使用する。

---

## 9.2 Required Information

Version 1では、Implementation Evidenceに少なくとも以下の情報を保持する。

- Implementationを識別する情報
- 使用したSpecification
- 使用したApproved Implementation Plan
- Codex Runnerへ渡したCodex Prompt
- 承認されたImplementation Scope
- Codex Runnerの実行結果
- 作成したファイル
- 変更したファイル
- 削除したファイル
- ファイル変更の概要
- Git Diffへの参照
- 実行したCommand
- 作成または変更したTest
- 対象Test Result
- 全体Test Result
- Error
- Warning
- 承認範囲外として検出または報告された変更
- 未完了事項
- Human Approvalが必要な事項
- 関連するApproval Recordの識別情報
- 実行開始・終了に関する情報

Humanによる承認・判断そのものの正式な証拠は、Implementation Evidenceへ重複して保持せず、`approvals/*.json`に保存されたApproval Recordを正本として扱う。

Implementation EvidenceからHumanによる判断を参照する必要がある場合は、対応するApproval Recordを識別可能な情報によって関連付ける。

---

## 9.3 Version 1 Format

Version 1では、Implementation Evidenceの正式フォーマットとしてJSONを使用する。

Implementation Evidenceは、Codex Runnerによる実装結果を単に記録するためのテキストログではなく、Application LayerおよびChatGPT Reviewが機械的に解析・比較できる構造化データとして扱う。

JSONには、少なくとも以下の主要ブロックを保持する。

```text
identity
basis
scope
changes
verification
deviations
codex_summary
```

主な内容は、以下とする。

```text
identity
- implementation_id
- created_at
- status

basis
- Specification path / hash
- Implementation Plan path / hash
- Codex Prompt path / hash

scope
- target_paths
- allowed_changes
- forbidden_changes

changes
- created_files
- modified_files
- deleted_files
- git_diff_path
- change_summary

verification
- commands
- tests_created_or_modified
- target_test_result
- full_test_result
- errors
- warnings

deviations
- out_of_scope_changes
- unplanned_changes
- unfinished_items
- human_approval_required
```

Human ApprovalがImplementationに関連する場合は、必要に応じて対応するApproval Recordを識別する情報を保持できる。

ただし、Humanによる承認内容そのものの正本は`approvals/*.json`とし、Implementation Evidenceとの二重管理は行わない。

Version 1では、Implementation Evidence JSONを正式な記録の正本とする。

Git Diffは、実際のSource Code変更を確認するための補助証拠として、Implementation Evidenceと関連付けて保存する。

概念的な保存構成は、以下とする。

```text
projects/specflow/
└── evidence/
    ├── implementation_001.json
    ├── implementation_001.diff
    ├── implementation_002.json
    └── implementation_002.diff
```

Human向けのMarkdown版または`log.txt`を正式記録として二重保存しない。

HumanがImplementation Evidenceを確認する必要がある場合は、UI等がJSONをHuman-readableな形式へ変換して表示する。

Version 1では、機械可読性、Review工程での安定性、およびImplementation Evidenceの一貫性を優先し、JSONを正式フォーマットとして採用する。

---

## 9.4 Review Input

Review工程には、少なくとも以下を渡す。

```text
Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Code
Test Result
```

Implementation Evidenceのみを根拠にReviewしてはならない。

Reviewでは、

```text
Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Code
Test Result
```

を相互に比較し、Implementationの適合性、完全性、および承認範囲からの逸脱を判断する。

例えば、Implementation Evidenceに承認範囲外の変更が存在しないと記録されていても、Git DiffまたはSource Codeに承認範囲外の変更が確認された場合は、Review側で逸脱として検出する。

同様に、SpecificationまたはApproved Implementation Planで要求されたImplementationが、Source Code、Git Diff、Test Code、またはTest Resultから確認できない場合は、Implementation不足として扱う。

---

## 9.5 Immutability

Review開始後、対象となるImplementation Evidenceを上書きしてはならない。

再実装または修正を行った場合は、既存のImplementation Evidenceを変更するのではなく、新しいImplementation Evidenceを生成する。

各Evidenceは、`implementation_id`、実行ID、または修正番号等によって識別可能とし、どのImplementationまたはCorrectionに対応するEvidenceであるかを追跡できるようにする。

関連するGit Diffについても、各Implementation Evidenceに対応する補助証拠として保持する。

概念的には、以下とする。

```text
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
```

この方式により、Correctionによって過去のImplementation Evidenceが失われることを防ぎ、Initial Implementationから各CorrectionおよびRe-Reviewまでの経過を追跡可能にする。

---

# 10. State Transition

## 10.1 States

Version 1では、少なくとも以下の状態を使用する。

```text
specification_ready
plan_generating
plan_approval_pending
plan_revision_requested
plan_approved
implementation_prompt_generating
implementation_ready
implementing
critical_approval_pending
implementation_failed
implementation_completed
reviewing
review_failed
final_approval_pending
correction_requested
completed
cancelled
```

---
## 10.2 Main Transition

Version 1における正常系のMain Transitionは、以下とする。

```text
specification_ready
        ↓
plan_generating
        ↓
plan_approval_pending
        ↓
plan_approved
        ↓
implementation_prompt_generating
        ↓
implementation_ready
        ↓
implementing
        ↓
implementation_completed
        ↓
reviewing
        ↓
[Review Result: APPROVED]
        ↓
final_approval_pending
        ↓
Human Final Approval
        ↓
Implementation Branchをdeveloperへmerge
        ↓
merge成功
        ↓
completed
```

`APPROVED`はStateではなく、UC-09で定義したReview Resultである。

Review Resultが`APPROVED`の場合にのみ、`reviewing`から`final_approval_pending`へ遷移できる。

Review Resultが`REVISION_REQUIRED`または`HUMAN_REVIEW_REQUIRED`の場合は、Main Transitionを継続せず、10.5で定義するReview結果に応じた遷移を行う。

Humanによる最終承認は、対象Implementationを`developer`へ取り込むことを許可する判断であり、最終承認のみをもって`completed`へ遷移してはならない。

Humanによる最終承認後、Application Layerは15.14で定義したmerge工程を実行する。

承認されたImplementation Branchが`developer`へ正常にmergeされたことを確認した場合にのみ、`completed`へ遷移する。

mergeに失敗した場合は`completed`へ遷移してはならない。

Version 1では、merge処理のための独立したStateは設けない。
---

## 10.3 Plan Rejection Transition

```text
plan_approval_pending
        ↓
plan_revision_requested
        ↓
plan_generating
        ↓
plan_approval_pending
```

---

## 10.4 Critical Change Transition

Implementation中にCritical Changeが必要となった場合は、Implementationを継続せず、`critical_approval_pending`へ遷移してHuman判断を求める。

Humanの判断に応じて、以下のように遷移する。

```text
implementing
        ↓
critical_approval_pending
        │
        ├── 承認
        │      ↓
        │  implementing
        │
        ├── 修正
        │      ↓
        │  correction_requested
        │
        ├── Specification再検討
        │      ↓
        │  Specification策定・修正工程
        │
        ├── Implementation Plan再検討
        │      ↓
        │  Plan策定・修正工程
        │
        └── 中止
               ↓
           cancelled
```

Critical ChangeがHumanによって有効に承認された場合にのみ、承認された変更範囲内で`implementing`へ戻ることができる。

SpecificationまたはImplementation Planの再検討へ戻った場合は、修正後の成果物について必要なHuman Approvalを改めて取得しなければならない。

以前のApproval Recordを、変更後のSpecificationまたはImplementation Planに対する有効な承認として自動的に引き継いではならない。

Critical Change Approvalの有効性は、UC-07および15.4で定義したApproval RecordとCritical Change Requestの同一性確認に従う。

---

## 10.4.1 Implementation Failure Transition

Implementation中に、Codex Runnerの実行失敗、Test失敗、またはその他の理由によりImplementationを正常に完了できず、定められた範囲で処理を継続できない場合は、`implementation_failed`へ遷移する。

```text
implementing
        ↓
Implementation Failure
        ↓
implementation_failed
        ↓
停止条件確認
        │
        ├── 再試行可能
        │      ↓
        │  定められた範囲で再試行
        │
        └── 継続不能
               ↓
           Human判断へ返す
```

`implementation_failed`は、TDDにおける期待されたTest失敗を示すStateではない。

TDD対象のImplementationにおいて、Implementation前に期待される振る舞いを表現したTestが意図どおり失敗することは正常な工程として扱い、それ自体を`implementation_failed`への遷移理由としてはならない。

`implementation_failed`への遷移は、Codex Runnerの実行失敗、Implementation後のTest失敗、実行環境上の問題、またはその他の理由により、現在のImplementationを正常に継続または完了できない場合に使用する。

再試行可能な場合は、第13章および15.13で定義した範囲内で再試行できる。

再試行によって解消できない場合は、自動的に別のAI Runnerへ切り替えず、停止理由、現在の状態、影響範囲、および再開に必要なHuman操作を記録してHumanへ判断を返す。

---

## 10.5 Review Failure Transition

Review Resultが`REVISION_REQUIRED`または`HUMAN_REVIEW_REQUIRED`の場合、Main Transitionを継続して`final_approval_pending`へ進んではならない。

### REVISION_REQUIRED

Review Resultが`REVISION_REQUIRED`の場合は、以下の遷移を基本とする。

```text
reviewing
        ↓
[Review Result: REVISION_REQUIRED]
        ↓
review_failed
        ↓
correction_requested
        ↓
異常・停止条件確認
        │
        ├── 自動修正可能
        │       ↓
        │  修正回数確認
        │       │
        │       ├── 上限未満
        │       │       ↓
        │       │  指定された修正工程
        │       │       ↓
        │       │    Re-Review
        │       │
        │       └── 上限到達
        │               ↓
        │          Human判断へ返す
        │
        └── Early Stop Condition
                ↓
           Human判断へ返す
```

修正対象は、Review Reportに基づき、以下のいずれかとする。

```text
Specification修正
Plan修正
Prompt修正
Implementation修正
Test修正
```

Specification、Approved Implementation Planおよび既存のHuman Approvalの範囲内で自動修正可能な場合は、15.11で定義したCorrection Loopに従って修正およびRe-Reviewを行う。

修正完了後は、問題の種類に応じた工程へ戻る。

### HUMAN_REVIEW_REQUIRED

Review Resultが`HUMAN_REVIEW_REQUIRED`の場合は、自動修正ループへ進んではならない。

```text
reviewing
        ↓
[Review Result: HUMAN_REVIEW_REQUIRED]
        ↓
correction_requested
        ↓
Human判断へ返す
```

Humanは、Review Reportおよび停止理由を確認し、必要な修正工程、承認、再検討、または中止等の次の操作を判断する。

`REVISION_REQUIRED`であっても、Early Stop Conditionを検出した場合、または自動修正の最大回数に到達した場合は、自動修正を継続せずHumanへ判断を返す。

`REVISION_REQUIRED`および`HUMAN_REVIEW_REQUIRED`はStateではなく、UC-09で定義したReview Resultである。
---

## 10.6 Final Rejection Transition

```text
final_approval_pending
        ↓
correction_requested
        ↓
指定された修正工程
```

Humanによる最終承認、および承認されたImplementation Branchの`developer`へのmergeが正常に完了しない限り、`completed`へ遷移してはならない。

---

# 11. Application Layer Structure

Version 1では、Application Layerを一つの巨大なクラスにしない。

HumanまたはUIの操作単位でUseCaseを分割する。

Application Layerに配置するUseCaseクラスは、15.2で定義した命名規則に従い、

```text
動詞 + 目的語 + UseCase
```

を基本とする。

概念的な構成は次のとおりとする。

```text
Application Layer
├── LoadDevelopmentInputUseCase
├── GenerateImplementationPlanUseCase
├── RequestPlanApprovalUseCase
├── ReviseImplementationPlanUseCase
├── GenerateCodexPromptUseCase
├── ExecuteImplementationUseCase
├── RequestCriticalChangeApprovalUseCase
├── CollectImplementationEvidenceUseCase
├── ReviewImplementationUseCase
├── RequestFinalApprovalUseCase
├── ResumeCorrectionUseCase
└── MergeApprovedImplementationUseCase
```

各UseCaseは、必要な既存EngineまたはServiceを利用する。

UseCaseは、他のUseCaseの内部処理を直接書き換えてはならない。

---

# 12. Existing Component Usage

Version 1では、既存Core ComponentおよびAI Runnerを可能な限り再利用し、Application Layer内に同等の責務を重複実装しない。

Version 1では、少なくとも以下の既存Componentを再利用する。

- `PlanPromptGenerator`
- `PromptAdapter`
- `AIRequest`
- `AIResponse`
- `AIService`
- `AIRunner`
- `OpenAIAPIRunner`
- `CodexRunner`

Application Layerは、これらのComponentが持つ既存責務を直接再実装せず、必要なUseCaseから利用する。

---

Version 1では、Project全体を自動探索・自動読み込みする専用`ProjectLoader`を必須としない。

Development Inputは、ファイル選択またはPath指定によって読み込むことを許容する。

---

Version 1では、Review専用の`ReviewRunner`を必須としない。

Review処理はApplication Layer上のRoleとして扱い、15.13で定義したRunner Assignmentに従って実行する。

---

Version 1では、現在の開発状態および状態遷移履歴を管理する機能を必要とする。

状態管理は、15.5で定義した以下の保存形式に従う。

```text
state.json
= 現在の状態

state_history/*.json
= 状態遷移の履歴
```

---

# 13. Error and Stop Conditions

以下の場合、Application Layerは処理を停止する。

- 必要な正式文書が存在しない
- Specificationが有効に承認されていない
- Implementation Planが有効に承認されていない
- Prompt生成に失敗した
- PromptResultがAI実行可能でない
- ChatGPT RunnerまたはCodex Runnerの実行に失敗し、定められた範囲で処理を継続できない
- CodexがHuman承認を必要とする重要変更の必要性を報告した
- Implementation後の対象Testまたは全体Testが期待に反して失敗し、自動修正可能な範囲で解消できない
- Implementation Evidenceが不足している
- Reviewに必要な成果物が不足している
- Specificationに不足・矛盾・不明確さがあり、現在の承認範囲内で処理を継続できない
- 修正ループにおいてEarly Stop Conditionを検出した
- 自動修正の最大回数に到達した
- Human判断が必要である

TDDにおいて、Implementation前に期待される振る舞いを表現したTestが意図どおり失敗することは、正常な工程として扱い、それ自体を停止条件とはしない。

停止時は、少なくとも以下を返す。

- 停止理由
- 現在の状態
- 影響範囲
- 次に必要なHuman操作
- 再開可能な工程

---

# 14. MVP Completion Conditions

SpecFlow Version 1 MVPは、以下を満たした場合に完成とする。

- UIまたは呼び出し元からSpecificationを指定できる
- Specificationに対する有効なHuman Approvalを確認できる
- ChatGPT RunnerがImplementation Plan Draftを生成できる
- HumanがPlanを承認または差し戻しできる
- 承認済みImplementation PlanからCodex用Promptを生成できる
- Codex Runnerが承認された範囲内で実装とテストを行える
- 振る舞いを変更する実装について、原則としてTDDを適用できる
- Implementation EvidenceをJSON形式で構築・保存できる
- Source CodeおよびGit Diffを取得できる
- Specification、Approved Implementation Plan、Codex Prompt、Implementation Evidence、Source Code、Git Diff、Test CodeおよびTest ResultをReviewへ提供できる
- ChatGPT RunnerがReview Reportを生成できる
- Review不適合時に、定められた範囲で自動修正および再Reviewを行える
- Early Stop Conditionまたは修正回数上限に到達した場合、処理を停止してHumanへ判断を返せる
- Humanが最終承認または差し戻しできる
- Humanによる最終承認後、承認されたImplementation BranchをApplication Layerの制御によって`developer`へmergeできる
- mergeが正常に完了した場合にのみ`completed`へ遷移できる
- Humanによる有効な承認なしに、承認を必要とする次工程へ進まない
- 現在の開発状態、状態遷移履歴、Human Approval、およびImplementation Evidenceを追跡できる
---

# 15. Decisions and Open Issues Before Formal Specification

正式Specification策定前に、Application Layerの基本設計に関する事項をHumanが決定する。

決定済み事項については、決定内容だけでなく、その判断理由を本章に記録する。

未決事項については、Humanの判断なしに実装段階で補完してはならない。

---

## 15.1 Application Layerを配置するPythonパッケージ

**Status: Decided**

Application Layerは、`core`の外側に独立したトップレベルPython Packageとして配置する。

概念的な構成は、以下とする。

```text
specflow/
├── application/
├── core/
├── projects/
└── tests/
```

依存方向は、以下を原則とする。

```text
UI / Interface
      ↓
Application
      ↓
Core
```

Application LayerはCoreを利用できる。

CoreはApplication Layerへ依存してはならない。

### Decision Reason

Application Layerは、以下の責務を持つ。

- UseCase制御
- Human承認
- 状態遷移
- 修正ループ
- Engine間の成果物受け渡し

これらは、再利用可能なCore Engineとは責務が異なる。

`core/application/`としてCore内部へ配置する案は、Version 1 MVPにおいて構成を単純にできる利点がある。

一方で、Application LayerをCore内部へ配置すると、再利用可能なCore Engineと、SpecFlow固有のUseCase制御との責務境界が不明確になる可能性がある。

そのため、Version 1 MVPでは実装対象機能を限定するが、MVPであることのみを理由として責務分離を弱めない。

SpecFlowでは、機能についてはMVPとして必要最小限に限定しつつ、構造については将来の拡張を妨げない最小限の責務分離を採用する。

Application LayerをCoreから分離することで、将来的に以下のInterfaceから共通してApplication Layerを利用できる構造を維持する。

```text
Web UI ─┐
CLI    ├──> Application ───> Core
API    ┘
```

これにより、将来Web UI、CLI、API等を追加する場合にも、Core Engineの構造を大きく変更せずに拡張できる。

また、Core EngineはApplication LayerやUIの存在を知る必要がなく、独立した再利用可能な部品として維持する。

以上の理由から、Application Layerは`core`の外側に独立したトップレベルPython Packageとして配置する。

---

## 15.2 UseCaseの命名規則

**Status: Decided**

Application Layerに配置するUseCaseクラスは、原則として以下の命名規則を使用する。

```text
動詞 + 目的語 + UseCase
```

Pythonのクラス名はPascalCaseとする。

例：

```python
LoadDevelopmentInputUseCase
GenerateImplementationPlanUseCase
RequestPlanApprovalUseCase
ReviseImplementationPlanUseCase
GenerateCodexPromptUseCase
ExecuteImplementationUseCase
RequestCriticalChangeApprovalUseCase
CollectImplementationEvidenceUseCase
ReviewImplementationUseCase
RequestFinalApprovalUseCase
ResumeCorrectionUseCase
MergeApprovedImplementationUseCase
```

対応するPythonファイル名はsnake_caseとし、クラス名と対応関係が分かる名称とする。

例：

```text
load_development_input_use_case.py
generate_implementation_plan_use_case.py
request_plan_approval_use_case.py
revise_implementation_plan_use_case.py
generate_codex_prompt_use_case.py
execute_implementation_use_case.py
request_critical_change_approval_use_case.py
collect_implementation_evidence_use_case.py
review_implementation_use_case.py
request_final_approval_use_case.py
resume_correction_use_case.py
merge_approved_implementation_use_case.py
```

### Decision Reason

Application LayerのUseCaseは、Core EngineやService、Runner等とは異なり、複数の部品を利用してSpecFlowの開発工程を進行する責務を持つ。

そのため、クラス名に`UseCase`を明示することで、そのクラスがApplication Layerの進行処理を担当することを、名前だけから判断できるようにする。

例えば、

```python
GenerateImplementationPlan
```

という名称だけでは、それがUseCase、Service、Engine、Runner等のどの責務を持つものかが明確でない。

一方、

```python
GenerateImplementationPlanUseCase
```

とすることで、Application Layerに属するUseCaseであることを明示できる。

また、Human Approvalを扱うUseCaseについては、Application Layer自身が承認を行うのではなく、Humanへ判断を求め、その結果を記録・検証・状態遷移へ反映する責務を持つ。

そのため、Human Approvalを扱うUseCaseでは、

```text
Approve...
```

ではなく、

```text
Request...Approval...
```

を使用する。

例えば、

```python
RequestPlanApprovalUseCase
RequestCriticalChangeApprovalUseCase
RequestFinalApprovalUseCase
```

とすることで、

```text
Human
= Approval Decision

Application Layer
= Approval Request / Record / Validation / State Transition
```

という責務分離を名称上も明確にする。

SpecFlowでは今後、以下のような異なる責務を持つコンポーネントが共存する。

```text
UseCase
Engine
Service
Runner
Adapter
Loader
```

そのため、多少名称が長くなっても、責務を名前から判別できることを優先する。

また、SpecFlowの開発ではAIによるコード生成やコピー・編集を利用するため、名称が長くなることによる入力負担は限定的である。

以上の理由から、Application LayerのUseCaseクラスは、

```text
動詞 + 目的語 + UseCase
```

を基本命名規則とする。

---

## 15.3 UseCase入力・出力DTOの形式

**Status: Decided**

Application LayerのUseCaseにおける入力・出力DTOは、原則としてPython標準ライブラリの`dataclass`を使用する。

DTOは、原則として以下の形式で定義する。

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleInput:
    ...


@dataclass(frozen=True)
class ExampleOutput:
    ...
```

UseCaseごとに、必要に応じてInput DTOおよびOutput DTOを定義する。

命名は、対象となるUseCaseとの対応関係が明確になる名称を使用する。

例：

```python
@dataclass(frozen=True)
class GenerateImplementationPlanInput:
    ...


@dataclass(frozen=True)
class GenerateImplementationPlanOutput:
    ...
```

Application LayerのUseCaseは、これらのDTOを通じて入力を受け取り、処理結果を返すことを基本とする。

概念的なデータの流れは、以下とする。

```text
UI / Interface
      ↓
Input DTO
      ↓
Application UseCase
      ↓
Core
      ↓
Application UseCase
      ↓
Output DTO
      ↓
UI / Interface
```

### DTOの責務

DTOは、LayerやUseCase間でデータを受け渡すためのデータ構造である。

DTO自身は、開発工程の進行判断やAI実行等の業務処理を担当しない。

Application Layerにおいて、

- どのデータを入力として必要とするか
- どのデータを処理結果として返すか

を明示するための契約として使用する。

### Decision Reason

Pythonの`dict`を使用すれば、柔軟かつ簡潔にデータを受け渡すことができる。

一方で、Application Layerの正式な入出力契約として`dict`を使用すると、

- 必要なキーがコードから判別しにくい
- キー名の誤りを検出しにくい
- 値の型が不明確になりやすい
- UseCaseの規模拡大に伴いデータ構造を把握しにくくなる

という問題が生じる可能性がある。

`dataclass`を使用することで、UseCaseが必要とするデータ構造と型をコード上で明示できる。

また、IDE、静的解析、テスト、およびAIによるコード生成・レビューにおいても、InputとOutputの契約を把握しやすくなる。

SpecFlowでは既に`AIRequest`および`AIResponse`で`@dataclass(frozen=True)`を使用しており、既存コードとの設計上の一貫性も保つことができる。

`frozen=True`を基本とすることで、生成されたDTOが受け渡し途中で意図せず変更されることを防ぎ、データの流れを追跡しやすくする。

以上の理由から、Version 1ではApplication Layer内部のUseCase Input / Output DTOに`dataclass(frozen=True)`を基本形式として採用する。

### `dict`の扱い

`dict`の使用自体は禁止しない。

Core内部のContextや、一時的・内部的なデータ構造など、柔軟なデータ表現が適切な箇所では使用できる。

ただし、Application LayerのUseCaseにおける正式なInput / Output契約については、原則としてDTOを使用する。

### Pydanticの扱い

Version 1のApplication Layer内部DTOでは、Pydanticを必須としない。

将来Web UIやAPI等を実装し、外部から不確かな入力データを受け取る場合には、入力ValidationのためにPydantic等を利用できる。

その場合も、外部InterfaceにおけるValidationモデルと、Application Layer内部のDTOは責務を分離することを原則とする。

概念的には、以下の構造を想定する。

```text
External Input
      ↓
Validation
(Pydantic等)
      ↓
Application DTO
(dataclass)
      ↓
Application UseCase
      ↓
Core
```

これにより、外部入力の検証責務と、Application Layer内部のデータ受け渡し責務を分離する。

---

## 15.4 承認記録の保存形式

**Status: Decided**

Version 1では、現在の進行状態とHumanによる承認記録を分離して管理する。

現在の進行状態は`state.json`で管理する。

Humanによる承認記録は、独立したJSONファイルとして`approvals/`配下に保存する。

概念的な構成は、以下とする。

```text
projects/specflow/
├── state.json
└── approvals/
    ├── specification_approval_001.json
    ├── plan_approval_001.json
    ├── critical_change_approval_001.json
    └── final_approval_001.json
```

`state.json`は、現在の開発工程や状態を管理する。

例：

```json
{
  "state": "plan_approved"
}
```

承認記録JSONは、Humanが何をどのように判断したかを記録する。

承認記録には、少なくとも以下の情報を保持する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```

`artifact_hash`は、Humanが承認した成果物と現在の成果物が同一であることを確認するために使用する。

承認後に対象成果物が変更され、現在のhashと承認時の`artifact_hash`が一致しない場合、その承認記録を現在の成果物に対する有効な承認として扱ってはならない。

### Decision Reason

`state.json`のみで承認状態を管理する方法は実装が簡潔である一方、どの成果物をHumanが承認したのかを十分に追跡できない。

例えば、

```text
plan_approved = true
```

という情報だけでは、承認後にImplementation Planが変更された場合でも、承認済み状態が残る可能性がある。

そのため、

```text
state.json
= 現在の状態

approvals/*.json
= Humanによる判断の証拠
```

として責務を分離する。

これにより、Application Layerは現在の工程を管理しながら、Human承認の対象、判断内容、時点、および承認対象の同一性を追跡できる。

Version 1では、承認記録の保存のためにDBを必須としない。

JSON形式を採用することで、実装を比較的単純に保ちつつ、Gitによる変更履歴の追跡やHumanによる内容確認を容易にする。

将来、複数ユーザー管理、高度な検索、監査機能等が必要になった場合には、DBへの移行または併用を検討できる。

以上の理由から、Version 1では、

```text
state.json + approvals/*.json
```

による分離管理を採用する。

### Specification Approval

Specificationに対するHuman Approvalは、Application Layerが生成または代替するものではない。

Version 1では、HumanがApplication Layerの外部でSpecificationを作成または選択し、その内容を承認する。

HumanによるSpecificationへの承認判断は、Specification Approval Recordとして`approvals/`配下に保存し、Development InputとともにApplication Layerへ渡す。

Specification Approval Recordでは、承認対象となったSpecificationそのものをArtifactとして扱う。

Approval Recordの`artifact_path`は承認対象Specificationを参照し、`artifact_hash`にはHumanが承認した時点のSpecificationから算出したHashを記録する。

概念的には、以下とする。

```text
Specification
        ↓
Human Review / Approval
        ↓
Specification Approval Record
        ├── artifact_path
        └── artifact_hash
        ↓
Development Input
        ↓
Application Layer
        ↓
Current Specification Hashとの同一性確認
```

Application Layerは、Specificationを後続工程で使用する前に、現在のSpecificationからArtifact Hashを計算し、Specification Approval Recordに保存された`artifact_hash`と比較する。

Hashが一致し、かつ`decision`が承認を示している場合にのみ、現在のSpecificationを有効に承認済みとして扱う。

Specification Approval Recordが存在しない場合、`decision`が承認を示していない場合、または現在のSpecificationのHashと`artifact_hash`が一致しない場合、そのSpecificationを有効に承認済みとして扱ってはならない。

Humanによる承認後にSpecificationが変更された場合、以前のSpecification Approval Recordを変更後のSpecificationに対する有効な承認として使用してはならない。

Specificationの承認判断はHumanの責務とし、Application Layerはその判断を代替せず、承認記録と現在のSpecificationとの同一性を検証する。

### Critical Change Approval

Critical Changeに対するHuman Approvalでは、Humanへ提示した変更要求そのものを承認対象Artifactとして扱う。

Version 1では、Critical Changeの内容、理由、対象Implementation、変更対象、および影響範囲等を識別可能なCritical Change Requestとして保存する。

Critical Change Approval Recordの`artifact_path`および`artifact_hash`は、このCritical Change Requestを参照する。

概念的には、以下とする。

```text
Critical Change Request
        ↓
Human Review
        ↓
Approval Record
        ↓
artifact_path
artifact_hash
        ↓
Critical Change Requestとの同一性確認
```
Critical Change Requestの内容がHuman承認後に変更され、現在のHashとApproval Recordに保存された`artifact_hash`が一致しなくなった場合、以前のApproval Recordを変更後のCritical Changeに対する有効な承認として扱ってはならない。

この方式により、Critical Change Approvalについても、Humanが具体的にどの変更要求を承認したかをArtifact単位で追跡可能にする。

### Final Approval

Final Approvalでは、Humanが最終Reviewを経て`developer`へ取り込むことを承認した特定時点のImplementationを承認対象とする。

Version 1では、承認対象Implementationを少なくともImplementation Branchおよび承認時点のHEAD Commitによって識別する。

Final Approvalの対象となるImplementationについて、承認対象を識別可能なFinal Approval Target Artifactを構築・保存し、そのArtifactをApproval Recordの承認対象として扱う。

Final Approval Target Artifactには、少なくとも以下を含める。

```text
implementation_branch
head_commit
base_commit
implementation_evidence_reference
git_diff_reference
review_report_reference
```

Approval Recordの`artifact_path`はFinal Approval Target Artifactを参照し、`artifact_hash`には当該Artifactから算出したHashを記録する。

概念的には、以下とする。

```text
Reviewed Implementation
        ↓
Final Approval Target Artifact
        ├── Implementation Branch
        ├── HEAD Commit
        ├── Base Commit
        ├── Implementation Evidence
        ├── Git Diff
        └── Review Report
        ↓
Human Final Approval
        ↓
Approval Record
        ├── artifact_path
        └── artifact_hash
        ↓
merge開始前に同一性確認
```

merge開始前に、Application Layerは現在の対象ImplementationからFinal Approval Target Artifactに対応する情報を確認し、承認時点の対象Implementationと一致していることを検証する。

Final Approval Target Artifactの内容が承認後に変更された場合、または対象Implementation BranchのHEAD Commitが承認時点から変更された場合、以前のFinal Approval Recordを現在のImplementationに対する有効な承認として扱ってはならない。

Final ApprovalにおけるArtifact Hashは、承認時とmerge開始前で同一の算出規則を使用する。

---

## 15.5 状態管理の保存形式

**Status: Decided**

Version 1では、現在の開発状態と状態遷移の履歴を分離して管理する。

現在の開発状態は、`state.json`に保存する。

状態遷移の履歴は、独立したJSONファイルとして`state_history/`配下に保存する。

概念的な構成は、以下とする。

```text
projects/specflow/
├── state.json
├── state_history/
│   ├── state_transition_001.json
│   ├── state_transition_002.json
│   └── state_transition_003.json
└── approvals/
```

`state.json`は、SpecFlowが現在どの開発工程にあるかを示すCurrent Stateとして扱う。

例：

```json
{
  "state": "plan_approval_pending",
  "updated_at": "2026-08-10T22:00:00+09:00"
}
```

状態が変更された場合、`state.json`を新しい状態へ更新するとともに、その状態遷移を`state_history/`へ記録する。

状態遷移履歴には、少なくとも以下の情報を保持する。

```text
transition_id
from_state
to_state
occurred_at
reason
```

例：

```json
{
  "transition_id": "state_transition_003",
  "from_state": "plan_generating",
  "to_state": "plan_approval_pending",
  "occurred_at": "2026-08-10T22:00:00+09:00",
  "reason": "Implementation Plan Draft generated"
}
```

### Current StateとHistoryの責務

`state.json`は、現在の状態を確認するために使用する。

`state_history/*.json`は、現在の状態へ至るまでに、どのような状態遷移が発生したかを追跡するために使用する。

役割は、以下のように分離する。

```text
state.json
= 現在の状態

state_history/*.json
= 状態遷移の履歴
```

Application Layerは、次のUseCaseを実行できるか判断する際に、`state.json`のCurrent Stateを参照する。

状態遷移が発生した場合は、Current Stateの更新だけでなく、その遷移を履歴として記録する。

### Decision Reason

`state.json`のみを更新する方式は、現在の状態を把握する方法としては簡潔である。

一方で、`state.json`を上書きするだけでは、過去にどの状態を経由し、なぜ現在の状態へ到達したのかを追跡できない。

SpecFlowでは、Humanによる差し戻し、Review不適合、再実装、再Review等によって、以前の工程へ戻る状態遷移が発生する。

例えば、以下のような状態遷移が想定される。

```text
plan_approval_pending
        ↓
Human Rejected
        ↓
plan_revision_requested
        ↓
plan_generating
        ↓
plan_approval_pending
```

Current Stateのみを保存した場合、最終的には、

```text
plan_approval_pending
```

という現在状態しか確認できず、

- 一度Humanから差し戻されたこと
- Plan修正工程へ戻ったこと
- 再度Planが生成されたこと

などの経過が失われる。

そのため、

```text
state.json
= 現在地

state_history/*.json
= そこへ至った経路
```

として責務を分離する。

これにより、Application Layerは`state.json`を参照することで現在の工程を単純に判断できる一方、必要に応じて`state_history/`から過去の状態遷移とその理由を追跡できる。

また、15.4で決定したHuman承認記録についても、

```text
approvals/*.json
= Humanによる判断の証拠
```

として独立して管理する。

したがって、Version 1では、

```text
state.json
= 現在の状態

state_history/*.json
= 状態遷移の履歴

approvals/*.json
= Humanによる承認・判断の証拠
```

という責務分離を採用する。

Version 1では、状態管理および状態履歴の保存のためにDBを必須としない。

JSON形式を採用することで、実装を比較的単純に保ちながら、Humanによる確認、Gitによる変更履歴の追跡、および将来のReview・Traceability処理との連携を可能にする。

将来、複数プロジェクト、複数ユーザー、高度な履歴検索等が必要になった場合には、DBへの移行または併用を検討できる。

以上の理由から、Version 1では、

```text
state.json + state_history/*.json
```

による状態管理を採用する。

---
## 15.6 Implementation Evidenceの正式なフォーマット

**Status: Decided**

Version 1では、Implementation Evidenceの正式フォーマットとしてJSONを使用する。

Implementation Evidenceは、Codexによる実装結果を単に記録するためのログではない。

ChatGPTが、承認済みSpecification、Implementation Plan、Codex Promptと、実際のSource Code変更、Test Result、およびGit Diffを比較し、以下を検証するための構造化された証拠として扱う。

- 必要な実装が不足していないか
- SpecificationまたはPlanにない実装を追加していないか
- 不要なファイル変更を行っていないか
- 修正対象以外を変更していないか
- Testが必要十分に追加または更新されているか
- 対象Testおよび既存Testが成功しているか
- Error、Warning、未完了事項が残っていないか
- Human承認が必要な変更を含んでいないか

Implementation Evidenceは、以下の主要ブロックを持つ。

```text
identity
basis
scope
changes
verification
deviations
codex_summary
```

### identity

実装作業を識別する情報を保持する。

最低限、以下を含む。

```text
implementation_id
created_at
status
```

### basis

Codexが何を根拠に実装したかを記録する。

最低限、以下を含む。

```text
Specification path / hash
Implementation Plan path / hash
Codex Prompt path / hash
```

### scope

承認された実装範囲を記録する。

最低限、以下を含む。

```text
target_paths
allowed_changes
forbidden_changes
```

### changes

Codexが実際に行った変更を記録する。

最低限、以下を含む。

```text
created_files
modified_files
deleted_files
git_diff_path
change_summary
```

### verification

実装後に行った検証を記録する。

最低限、以下を含む。

```text
commands
tests_created_or_modified
target_test_result
full_test_result
errors
warnings
```

### deviations

承認済み範囲との不一致や未解決事項を記録する。

最低限、以下を含む。

```text
out_of_scope_changes
unplanned_changes
unfinished_items
human_approval_required
```

### Review Rule

ChatGPT Reviewは、CodexがEvidence内に記述した自己評価のみを根拠としてはならない。

以下を相互に比較する。

```text
Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Result
```

例えば、Codexが`out_of_scope_changes`を空として報告していても、Git Diffに承認範囲外の変更が存在する場合は、Review側で逸脱として検出する。

同様に、Implementation Planで要求された実装項目が、変更ファイル、Git Diff、Testのいずれにも確認できない場合は、実装不足として扱う。

### Storage

Version 1では、Implementation Evidenceを`evidence/`配下へ保存する。

例：

```text
projects/specflow/
└── evidence/
    ├── implementation_001.json
    ├── implementation_001.diff
    ├── implementation_002.json
    └── implementation_002.diff
```

JSONをImplementation Evidenceの正本とする。

Git Diffは、実際のコード変更を検証するための補助証拠として保存する。

Human向けのMarkdown版を正式記録として二重保存しない。

HumanがEvidenceを確認する必要がある場合は、UI等がJSONをHuman-readableな形式へ変換して表示する。

### Decision Reason

Implementation Evidenceは、主としてCodex、Application Layer、ChatGPT Review間で受け渡される内部データである。

そのため、Human向け可読性よりも、機械が安定して解析・比較できる構造化形式を優先する。

JSONを採用することで、Application Layerによる自動処理、ChatGPT Reviewによる比較、および将来のUI表示やDB移行を容易にする。

MarkdownはHumanにとって読みやすいが、Version 1では保存形式として二重管理せず、必要に応じてJSONから表示用データを生成する。

以上の理由から、Version 1ではImplementation Evidenceの正式フォーマットとしてJSONを採用する。

## 15.7 Codexの停止・再開方式

**Status: Decided**

Version 1では、Codexの停止・再開を、Codex自身のセッション状態に依存させない。

Codexのセッションは、SpecFlowにおける正式な状態（Source of Truth）として扱わない。

Codexの実装中に停止が必要となった場合は、現在の実装状況、状態、変更内容、および必要なEvidenceをSpecFlow側へ保存したうえで、その実行単位を終了する。

再開時は、以前のCodexセッションを継続することを前提とせず、SpecFlowに保存された正式な情報から再開に必要なPromptを生成し、新しいCodex実行として処理を開始する。

基本的な流れは、以下とする。

```text
Approved Specification
        ↓
Approved Implementation Plan
        ↓
Codex Prompt
        ↓
Codex Implementation
        ↓
停止条件発生
        ↓
Implementation Evidence保存
        ↓
Git Diff / Source Code変更保存
        ↓
state.json更新
        ↓
state_history記録
        ↓
必要に応じてHuman承認要求
        ↓
approvals記録
        ↓
Application Layer
        ↓
再開用Prompt生成
        ↓
New Codex Execution
        ↓
Implementation Resume
```

### Stop

Version 1における「停止」は、Codexプロセスまたはセッションを単に一時停止状態で保持することを意味しない。

停止時には、再開に必要な情報をSpecFlow側へ保存し、そのCodex実行単位を終了可能な状態にする。

停止時には、少なくとも以下の情報を保持する。

```text
Current State
Approved Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Changed Files
Git Diff
Test Result
Errors / Warnings
Unfinished Items
Human Approval Requirement
```

Human承認が必要な場合は、Codexをそのまま自律的に続行させてはならない。

Application Layerは状態を承認待ちへ遷移させ、Humanの判断を待つ。

### Resume

Version 1における「再開」は、以前のCodexとの会話を継続することを意味しない。

再開時には、SpecFlow側に保存された正式な状態を参照し、Application Layerが再開に必要な情報を構成する。

再開用Promptには、必要に応じて以下を含める。

```text
Approved Specification
Approved Implementation Plan
Current State
Previous Implementation Evidence
Current Source Code
Git Diff
Test Result
Human Approval Result
Remaining Tasks
Allowed Changes
Forbidden Changes
```

Codexは、以前のセッション内部の記憶ではなく、この再開用Promptと現在のSource Codeを基準として実装を再開する。

### Source of Truth

Codex Sessionは、SpecFlowのSource of Truthとして扱わない。

Version 1における正式な状態および再開根拠は、SpecFlow側で管理する。

概念的には、以下を正式な情報として扱う。

```text
Specification
Approved Implementation Plan
state.json
state_history/*.json
approvals/*.json
Implementation Evidence
Source Code
Git Diff
Test Result
```

したがって、

```text
Codex remembers the previous work
```

ことを、再開可能性の前提としてはならない。

再開可能性は、

```text
SpecFlow preserves the required state
```

によって保証する。

### Human Approval

Codexが実装中に、承認済みImplementation Planの範囲を超える変更、重要な設計変更、またはHuman判断が必要な事項を検出した場合は、自律的にその変更を続行してはならない。

その場合は、

```text
Codex
  ↓
停止
  ↓
Evidence保存
  ↓
State更新
  ↓
Human Approval Pending
  ↓
Human Decision
```

の流れへ移行する。

Humanが承認した場合は、その承認内容を`approvals/*.json`へ記録したうえで、新しい再開用Promptを生成する。

Humanが承認しなかった場合は、必要に応じてPlan修正、Prompt再生成、またはその他の適切な前工程へ戻る。

### Session Independence

Version 1では、同一Codexセッションを継続できる場合であっても、それを再開の必須条件とはしない。

同一セッションの継続機能を利用する場合でも、SpecFlow側に保存された正式な状態との整合性を優先する。

Codexセッション内の文脈と、SpecFlow側の正式情報に不一致がある場合は、SpecFlow側の正式情報を優先する。

これにより、

- Codexセッションの終了
- PCの再起動
- 実行途中での中断
- 翌日以降の作業再開
- Codex実行環境の変更

等が発生しても、特定のCodexセッションに依存せず、保存された状態から作業を再構成できる設計とする。

### Decision Reason

同一Codexセッションを継続する方式は、実装が比較的簡単であり、Codexがそれまでの会話文脈を保持できる利点がある。

一方で、Codexセッションそのものへ開発状態を依存させると、セッション終了、障害、実行環境変更等によって、再開に必要な情報が失われる可能性がある。

また、Codexが以前の実行中に行った独自解釈や補完を、そのまま次の実装へ引き継ぐ可能性がある。

SpecFlowでは、

```text
Humanが承認した正式情報
```

と、

```text
AIが内部で保持している文脈
```

を区別する必要がある。

そのため、Codexのセッション記憶ではなく、SpecFlow側に保存されたSpecification、Approved Implementation Plan、State、Approval、Implementation Evidence、Source Code、Git Diff、Test Result等を正式な再開根拠とする。

この方式により、

- 再現性
- 監査可能性
- 障害復旧性
- Human承認との整合性
- Codexの過剰な自己判断の抑制
- 将来のImplementation AI変更への対応

を確保する。

Version 1では、Codexを永続的な状態保持主体ではなく、

```text
SpecFlowから現在の正式状態と実行指示を受け取り、
その実行単位を担当するImplementation Runner
```

として扱う。

以上の理由から、Version 1では、

**Codexセッション非依存・SpecFlow状態保存型**

の停止・再開方式を採用する。

---

## 15.8 Source CodeおよびGit Diffの取得方法

**Status: Decided**

Version 1では、CodexによるImplementationを、実装単位ごとに作成する専用Implementation Branch上で実行する。

Codexは、Humanによる最終承認前に、安定した開発Branchである`developer`へ直接変更を加えてはならない。

Implementation Branchは、`developer`の特定Commitを基準として作成する。

Branch作成時の基準Commitを`base_commit`として記録し、Implementation EvidenceおよびReviewでは、この`base_commit`を今回のImplementationにおける変更前の基準点として使用する。

概念的な流れは、以下とする。

```text
developer
    ↓
Base Commitを取得
    ↓
Implementation Branch作成
    ↓
Codex Implementation
    ↓
Source Code変更
    ↓
Test
    ↓
Git Status / Git Diff取得
    ↓
Implementation Evidence
    ↓
ChatGPT Review
    ↓
Human Final Approval
    │
    ├── Approved
    │       ↓
    │   developerへmerge
    │
    └── Rejected
            ↓
        修正継続
        または
        Branch破棄
```

### Implementation Branch

Codexによる実装は、Implementationごとに作成した専用Branch上で行う。

Version 1では、Implementation Branchの命名規則を原則として以下とする。

```text
impl/<implementation-name>-<sequence>
```

例：

```text
impl/review-runner-001
impl/state-manager-001
impl/application-layer-001
```

Branch名は、どのImplementationに対応するBranchであるかをHumanおよびApplication Layerが識別できる名称とする。

Implementation Branchは、原則として`developer`から作成する。

### Base Commit

Implementation Branch作成時に、基準となる`developer`のCommit Hashを取得する。

概念的には、以下の情報を保持する。

```json
{
  "git": {
    "base_branch": "developer",
    "base_commit": "a003616",
    "implementation_branch": "impl/review-runner-001"
  }
}
```

`base_commit`は、今回のImplementation開始時点におけるSource Codeの基準状態を示す。

Review時には、現在の`developer`Branchそのものではなく、原則として保存された`base_commit`を変更前の基準として使用する。

これにより、Implementation実行中に`developer`側へ別の変更が追加された場合でも、今回のCodex実装による変更範囲を特定できるようにする。

### Source Code

Source Codeは、Implementation Branch上の現在のファイル内容を実装結果として扱う。

ChatGPT Reviewでは、必要に応じて対象Source Codeを取得し、SpecificationおよびApproved Implementation Planとの適合性を確認する。

Source CodeとGit Diffは、それぞれ異なる目的で使用する。

```text
Source Code
= 現在どのような実装になっているか

Git Diff
= 今回のImplementationで何が変更されたか
```

そのため、ReviewではGit Diffのみを確認して完了とせず、必要に応じて現在のSource Codeそのものも確認する。

### Git Status

Codex実装後には、Gitの状態を取得する。

Git Statusは、少なくとも以下を識別するために使用する。

```text
Modified Files
Created / Untracked Files
Deleted Files
Renamed Files
```

未追跡の新規ファイルについてもImplementation Evidenceの対象とし、通常のGit Diffのみでは検出できない変更を見落としてはならない。

### Git Diff

Git Diffは、Implementation Branch作成時に保存した`base_commit`と、Implementation Branch上の現在の実装結果との差分として取得する。

概念的には、以下とする。

```text
Base Commit
    ↓
    │
    │ Codex Implementation
    │
    ↓
Implementation Branch Current State

Git Diff
=
Base Commit
vs
Implementation Branch Current State
```

Git Diffは、Implementation Evidenceに関連付けて保存する。

例：

```text
projects/specflow/
└── evidence/
    ├── implementation_001.json
    └── implementation_001.diff
```

Implementation Evidenceには、少なくとも以下のGit関連情報を保持する。

```text
base_branch
base_commit
implementation_branch
created_files
modified_files
deleted_files
renamed_files
git_diff_path
```

### Review Rule

ChatGPT Reviewは、Codexが報告した変更内容のみを根拠としてはならない。

以下を相互に比較する。

```text
Approved Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Status
Git Diff
Test Result
```

例えば、Approved Implementation Planでは、

```text
core/review_runner.py
tests/test_review_runner.py
```

のみが変更対象であるにもかかわらず、Git StatusまたはGit Diffに、

```text
core/config.py
```

の変更が確認された場合、その変更がImplementation Plan上必要であるかをReviewする。

必要性を確認できない場合は、範囲外変更または未承認変更の候補として扱う。

逆に、Approved Implementation Planで要求されたファイルまたは実装項目がSource Code、Git Diff、Test等から確認できない場合は、実装不足の候補として扱う。

### Human Approval and Merge

CodexによるImplementationが完了しても、その変更を自動的に`developer`へmergeしてはならない。

Implementation Branch上で、

```text
Implementation
↓
Test
↓
Evidence
↓
ChatGPT Review
↓
Human Final Approval
```

を完了した後に、初めて`developer`へのmergeを許可する。

したがって、

```text
Implementation Branch
= AIによる未承認の作業領域

developer
= Human承認を通過した変更を取り込む安定した開発領域
```

として扱う。

Humanが最終承認しなかった場合は、`developer`へmergeせず、Implementation Branch上で修正工程を継続する。

修正を継続しない場合は、そのImplementation Branchを破棄できる。

### Branch Isolation

Version 1では、CodexのImplementationを専用Branchへ隔離することによって、Codexによる未承認変更が直接`developer`へ反映されることを防止する。

CodexがPlan外の変更や不要な変更を行った場合でも、Humanが承認するまでは安定Branchへ取り込まれない構造とする。

ただし、Version 1ではGit Worktreeによる物理的な作業ディレクトリの分離までは必須としない。

Version 1では、

```text
Dedicated Implementation Branch
+
Fixed Base Commit
```

による論理的な変更分離を採用する。

将来、複数Implementationの並行実行、より強いFilesystem隔離、AI実行環境の独立等が必要になった場合は、Git Worktree等の導入を検討する。

### Decision Reason

単純にWorking Tree上でCodexを実行し、実装後に`git diff`を取得する方式は実装が簡潔である。

一方で、Humanによる既存変更とCodexによる変更が混在する可能性があり、今回のImplementationによる変更範囲を正確に識別できない場合がある。

Implementationごとに専用Branchを作成することで、

- Codexによる変更を安定Branchから隔離できる
- 未承認変更が`developer`へ直接入ることを防止できる
- Implementation単位で変更範囲を追跡できる
- Review不適合時にBranch上で修正を継続できる
- 必要に応じてImplementation全体を破棄できる
- Git DiffをImplementation Evidenceの客観的証拠として利用できる

という利点がある。

また、Branch作成時の`base_commit`を固定して記録することで、Implementation実行後に`developer`が更新された場合でも、今回のImplementation開始時点を基準として変更内容を再現できる。

Version 1では、Git Worktreeまで導入するとGit操作およびLifecycle管理が複雑になるため、Implementation Branchによる分離を採用する。

以上の理由から、Version 1では、

```text
Dedicated Implementation Branch
+
Fixed Base Commit
+
Git Status
+
Git Diff
```

をSource CodeおよびGit Diff取得の基本方式とする。

---

## 15.9 Review用Promptの入力上限と分割方法

**Status: Decided**

Version 1では、Review用Promptについて、固定的なToken数または文字数のみを基準として機械的に分割する方式は採用しない。

Review対象が一括して十分な精度で処理可能な場合は、一括Reviewを許可する。

一方、Review対象が大規模である場合、または一括ReviewによってReview精度が低下する可能性がある場合は、Review対象を意味単位およびReview責務単位に分割し、段階的にReviewする。

Version 1では、以下を基本方針とする。

```text
Small Implementation
        ↓
一括Review
        ↓
Review Result
```

Review対象が大きい場合は、以下のように段階的Reviewを行う。

```text
Approved Specification
Approved Implementation Plan
Codex Prompt
Implementation Evidence
Source Code
Git Diff
Test Result
        ↓
意味単位・Review責務単位へ分割
        ↓
Individual Reviews
        ↓
Integration Review
        ↓
Final Review Result
```

### Review Principle

Review用Promptには、単に入力可能な情報をすべて投入するのではなく、そのReviewで判断するために必要な情報を選択して渡す。

Review対象の分割は、単純な文字数、行数、Token数のみを基準として行わない。

例えば、

```text
500行ごと
10000文字ごと
```

のように、Source Code、Git Diff、Specification等の意味的なまとまりを無視して機械的に分割することを基本方式とはしない。

可能な限り、

```text
Requirement
File
Class
Function
Test
Change Scope
Review Responsibility
```

等の意味単位を維持して分割する。

### Review Responsibility

Version 1では、必要に応じてReviewを以下のような責務へ分割する。

```text
Requirement Review
Change Scope Review
Implementation Review
Test Review
Integration Review
```

#### Requirement Review

SpecificationおよびApproved Implementation PlanとImplementation Evidenceを比較し、要求された実装が不足していないかを確認する。

主な確認事項：

```text
必要な実装が存在するか
要求事項の抜けがないか
Planの実装項目が反映されているか
```

#### Change Scope Review

Approved Implementation Plan、Implementation Evidence、Git StatusおよびGit Diffを比較し、変更範囲の逸脱を確認する。

主な確認事項：

```text
Plan外の変更がないか
不要なファイル変更がないか
未承認変更がないか
削除・追加・Renameが適切か
```

#### Implementation Review

Specification、Approved Implementation Plan、対象Source Codeおよび対応するGit Diffを比較し、実装内容の正確性を確認する。

主な確認事項：

```text
要求されたロジックが正しく実装されているか
不足実装がないか
余計な実装がないか
既存構造を不必要に変更していないか
```

#### Test Review

Specification、Approved Implementation Plan、Test CodeおよびTest Resultを比較し、検証が十分であるかを確認する。

主な確認事項：

```text
必要なTestが存在するか
変更内容に対応したTestになっているか
既存Testを不必要に変更していないか
対象Testが成功しているか
全体Testが成功しているか
```

#### Integration Review

個別Reviewの結果を統合し、Implementation全体としての適合性を判断する。

Integration Reviewでは、少なくとも以下を確認する。

```text
個別Review間に矛盾がないか
未解決事項が残っていないか
Human判断が必要な事項がないか
Implementation全体として承認候補にできるか
```

### Review Input Selection

各Reviewには、その判断に必要な情報を優先して渡す。

例えばTest Reviewを行うためだけに、変更対象と直接関係しないSource Code全体を必ず入力する必要はない。

同様に、特定ファイルのImplementation Reviewでは、関連するSpecification、Plan、Git Diff、Source Code等を中心としてReview Contextを構成する。

これにより、

```text
必要な情報へAIのReviewを集中させる
```

ことを優先する。

### Input Limit

Version 1では、

```text
最大○○Token
最大○○文字
```

のような固定的な入力上限をArchitecture上の恒久的な値として定義しない。

利用するAI ModelおよびRunnerによって入力可能量が異なり、将来的にその値が変更される可能性があるためである。

Version 1では、

```text
一括して安全かつ十分な精度でReview可能
```

と判断できる場合は一括Reviewを行い、それが困難な場合は意味単位の段階的Reviewへ移行する。

具体的な実装上の閾値が必要な場合は、変更可能なConfigurationとして扱い、Application Layerの設計原則そのものへ固定値を埋め込まない。

### Final Review Result

段階的Reviewを実施した場合、各Review結果をそのまま独立した最終判断として扱わない。

個別Review結果をIntegration Reviewへ渡し、Implementation全体について最終的なReview Resultを生成する。

概念的には、以下とする。

```text
Requirement Review ─────┐
                        │
Change Scope Review ────┤
                        │
Implementation Review ──┼──> Integration Review
                        │             ↓
Test Review ────────────┘      Final Review Result
```

最終的なHuman承認は、この統合されたReview Resultを基に行う。

### Future Extension

Version 1では、意味単位およびReview責務単位による段階的Reviewを基本方式として採用する。

一方、将来以下の必要性が生じた場合は、Runnerの入力可能量を考慮したDynamic Review Budget方式への拡張を検討する。

```text
Review対象がさらに大規模化した場合
利用するAI RunnerごとにContext Capacityが異なる場合
Token Budgetの自動管理が必要になった場合
意味単位Reviewをさらに自動分割する必要が生じた場合
複数AI ModelをReview用途に応じて切り替える場合
```

将来拡張候補は、以下とする。

```text
Semantic Review
        +
Runner Capability
        +
Dynamic Review Budget
```

Dynamic Review Budgetでは、将来的に、

```text
Runnerの入力可能量
        ↓
出力用領域
        ↓
Safety Margin
        ↓
利用可能Review Budget
        ↓
Review Contextの自動構成
```

のような処理を検討できる。

ただし、このDynamic Review Budget機能はVersion 1の実装対象には含めない。

Future Extensionとして本章に明示的に記録し、Version 1で意図的に採用しなかった設計候補として保持する。

### Decision Reason

常に一括Reviewする方式は実装が簡潔であり、小規模なImplementationでは有効である。

しかし、Implementationが大規模化すると、入力上限だけでなく、大量の情報によって重要な変更、逸脱、不足等を見落とす可能性がある。

一方、固定文字数や固定行数による機械的分割は入力サイズを制御できるが、Specification、Source Code、Git Diff等の意味的なまとまりを破壊する可能性がある。

そのためVersion 1では、小規模なImplementationについては一括Reviewを許可し、大規模なImplementationについては意味単位およびReview責務単位で段階的にReviewする。

これにより、

- Review対象への注意集中
- 実装不足の検出
- 範囲外変更の検出
- 不要な変更の検出
- Test妥当性の確認
- 大規模Implementationへの対応

を両立する。

また、固定的なToken上限をArchitectureへ埋め込まず、将来Runner CapabilityおよびDynamic Review Budgetを導入できる余地を残す。

以上の理由から、Version 1では、

```text
Small Implementation
    → 一括Review

Large / Complex Implementation
    → Semantic Staged Review
    → Integration Review
```

をReview用Promptの基本的な入力・分割方式として採用する。

---

## 15.10 TDDを必須とする範囲

**Status: Decided**

Version 1では、TDDの適用対象をファイル拡張子だけで機械的に判断しない。

TDDを適用する本質的な基準は、

```text
その変更がプログラムの振る舞いを変えるかどうか
```

とする。

そのうえで、Version 1では実務上の補助ルールとして、`.py`ファイルの新規作成または変更は原則としてテスト対象とする。

---

### Basic Principle

Version 1では、プログラムの振る舞いを変更するImplementationに対して、TDDを原則として適用する。

基本的な流れは、以下とする。

```text
Approved Specification
        ↓
Approved Implementation Plan
        ↓
期待される振る舞いをTestとして表現
        ↓
Testを実行
        ↓
期待どおり失敗することを確認
        ↓
必要最小限のImplementation
        ↓
対象Testを再実行
        ↓
対象Test成功
        ↓
既存Testを含む全体Test
        ↓
Implementation Evidenceへ記録
```

TDDはSpecificationに代わるものではない。

SpecificationおよびApproved Implementation Planを正本とし、Testは、それらに定義された期待動作を検証可能な形で表現する成果物として扱う。

---

### TDD Required

以下のような変更は、原則としてTDD対象とする。

```text
ロジックの新規追加
既存ロジックの変更
Bug Fix
状態遷移の変更
承認判定ロジックの変更
Validationの追加・変更
DTOの振る舞いに関する変更
AI Runnerの振る舞いの変更
Application UseCaseの追加・変更
Core Engineの追加・変更
例外処理の追加・変更
外部入出力に影響する変更
```

また、`.py`ファイルの新規作成または変更がある場合は、原則としてテスト対象とする。

ただし、`.py`ファイルが変更されたという事実だけで、必ず新しいTest Caseを追加しなければならないという意味ではない。

既存Testによって変更内容が十分に検証される場合は、そのTestの実行によって検証できる。

---

### TDD Not Required

以下のように、実行時の振る舞いを変更しない変更については、TDDを必須としない。

```text
Markdown等の文書のみの変更
コメントのみの変更
docstringのみの変更
コードフォーマットのみの変更
振る舞いに影響しない命名・表記修正
Human向け説明文のみの変更
```

文書のみの変更については、原則として新しいTest Caseの作成を要求しない。

ただし、文書変更によってSpecification、Plan、Configuration等の正式な意味が変更される場合は、後続Implementationにおいて必要なTestを検討する。

---

### Configuration and Data Files

`.json`、`.yaml`、`.yml`、`.toml`等の設定ファイルやデータファイルについては、拡張子のみでTDD対象外とは判断しない。

変更によってプログラムの振る舞いが変わる場合は、テスト対象とする。

例：

```text
state.jsonのSchema変更
Workflow設定変更
Runner設定変更
Retry回数変更
Feature Flag変更
Validation条件変更
```

一方、実行時の振る舞いに影響しない単なる記録データや説明情報の変更については、TDDを必須としない。

---

### Test Execution Rule

TDD対象となるImplementationでは、Codexは少なくとも以下を実行する。

```text
1. 変更対象に対応するTestを作成または特定する
2. 必要に応じてImplementation前の失敗を確認する
3. 必要最小限のImplementationを行う
4. 対象Testを実行する
5. 対象Testの成功を確認する
6. 既存Testを含む全体Testを実行する
7. Test ResultをImplementation Evidenceへ記録する
```

Bug Fixの場合は、可能な限りBugを再現するFailing Testを先に作成し、そのTestが修正後に成功することを確認する。

---

### Implementation Evidence

TDD対象となるImplementationでは、Implementation EvidenceにTDD実施状況を記録する。

最低限、以下を確認可能な形で保持する。

```text
tests_created_or_modified
test_commands
initial_test_result
target_test_result
full_test_result
```

必要に応じて、以下のような構造化データを使用できる。

```json
{
  "tdd": {
    "required": true,
    "tests_created_or_modified": [
      "tests/test_example.py"
    ],
    "initial_test_result": {
      "status": "failed"
    },
    "target_test_result": {
      "status": "passed"
    },
    "full_test_result": {
      "status": "passed"
    }
  }
}
```

TDD対象外の場合も、その理由をEvidenceから確認できるようにすることが望ましい。

例：

```json
{
  "tdd": {
    "required": false,
    "reason": "documentation-only change"
  }
}
```

---

### Review Rule

ChatGPT Reviewは、単にTestが成功したという事実だけでImplementationを適合と判断してはならない。

以下を相互に確認する。

```text
Specification
Approved Implementation Plan
Source Code
Git Diff
Test Code
Test Result
Implementation Evidence
```

Reviewでは、少なくとも以下を確認する。

```text
変更された振る舞いに対応するTestが存在するか
必要なTestが不足していないか
TestがImplementation内容と対応しているか
Testを通すためだけの不自然なImplementationがないか
既存Testを不必要に削除・弱体化していないか
対象Testだけでなく全体Testが成功しているか
```

したがって、

```text
Test Passed
```

という結果だけを、Specification適合の十分条件として扱わない。

---

### Exceptions

TDDの適用が技術的に困難、または合理的でない場合は、Codexが独自判断でTDDを省略してはならない。

その場合は、Implementation Evidenceに理由を記録し、必要に応じてHumanまたはReview工程へ判断を返す。

例：

```text
外部サービスへの依存が強く自動Testが困難
実行環境依存の変更
Test環境が存在しない
既存Architecture上、適切なTest Harnessが存在しない
```

このような場合も、可能な範囲で代替検証方法を提示する。

---

### Decision Reason

`.py`ファイルの変更を一律にTDD必須とする方法は単純である一方、コメントやdocstring等、実行時の振る舞いを変更しない修正まで形式的にTDD対象となる可能性がある。

逆に、`.json`や`.yaml`等の変更であっても、設定内容によってプログラムの振る舞いが変わる場合がある。

そのためVersion 1では、ファイル拡張子ではなく、

```text
プログラムの振る舞いを変更するか
```

をTDD適用の本質的な判断基準とする。

ただし、実務上の判断を単純にするため、

```text
.pyファイルの新規作成・変更
= 原則としてTest対象
```

という補助ルールを採用する。

これにより、TDDを形式的な作業にせず、SpecificationおよびApproved Implementation Planで要求された振る舞いをTestとして検証することを重視する。

Version 1では、

```text
Behavior Change
    → 原則TDD

Documentation / Non-Behavior Change
    → 原則TDD対象外
```

を基本方針とする。

---

## 15.11 修正ループの最大回数と早期停止条件

**Status: Decided**

Version 1では、ChatGPT Reviewによって修正が必要と判断された場合、Codexによる自動修正を一定回数まで許可する。

ただし、修正ループの制御を最大回数のみに依存させない。

修正過程において異常または収束しない兆候を検出した場合は、最大回数へ到達する前であっても自動修正を停止し、Humanによる判断を要求する。

基本原則は、以下とする。

```text
正常に収束している修正
    → AIによる自動修正を継続

異常または非収束を検出
    → 早期停止
    → Human Review Required

最大修正回数へ到達
    → 自動修正停止
    → Human Review Required
```

### Correction Loop

基本的な修正ループは、以下とする。

```text
Codex Implementation
        ↓
ChatGPT Review
        │
        ├─ APPROVED
        │       ↓
        │  Human Final Approval Candidate
        │
        ├─ REVISION_REQUIRED
        │       ↓
        │  異常・停止条件確認
        │       │
        │  ┌────┴────┐
        │  │         │
        │ 問題なし   問題あり
        │  │         │
        │  ↓         ↓
        │ 修正回数確認  Early Stop
        │  │         ↓
        │  │    Human Review Required
        │  │
        │ ┌┴────────┐
        │ │         │
        │ 上限未満   上限到達
        │ │         │
        │ ↓         ↓
        │ Codex     Stop
        │ Correction │
        │ ↓         ↓
        │ Re-Review Human Review Required
        │
        └─ HUMAN_REVIEW_REQUIRED
                ↓
           Human Review Required
```

Humanは、通常の修正ループへ毎回介入する必要はない。

Specification、Approved Implementation Planおよび既存の承認範囲内で修正可能であり、修正が正常に収束している場合は、CodexとChatGPT Reviewの間で自動修正を継続できる。

---

### Maximum Correction Count

Version 1では、初回Implementationを修正回数には含めない。

ChatGPT Reviewによる`REVISION_REQUIRED`を受けてCodexが修正を実行した時点で、1回の修正として数える。

概念的には、以下とする。

```text
Initial Implementation
        ↓
Review
        ↓
Correction 1
        ↓
Review
        ↓
Correction 2
        ↓
Review
        ↓
Correction 3
        ↓
Review
```

Version 1における自動修正の最大回数は、原則として**3回**とする。

3回の自動修正を実施してもReviewが適合とならない場合は、それ以上CodexとChatGPT Reviewのみで修正を継続せず、自動修正を停止してHumanへ判断を返す。

最大回数は無限ループ防止のSafety Limitとして扱う。

---

### Early Stop

最大修正回数は、自動修正を必ずその回数まで実行することを意味しない。

以下のような状態を検出した場合は、最大回数へ到達する前であっても修正ループを停止する。

```text
同一または実質的に同一のReview指摘が繰り返される

修正によって新たなPlan外変更が発生する

修正のたびに変更対象ファイルが不合理に増加する

修正によって、それまで成功していたTestが失敗する

Test Resultが修正前より悪化する

修正によって新たなErrorまたは重大なWarningが発生する

Approved Implementation Planの範囲内では解決できない

Specificationの曖昧さまたは矛盾が疑われる

Implementation Plan自体の修正が必要と判断される

Architecture上の新たな判断が必要になる

既存のHuman承認範囲を超える変更が必要になる
```

これらを検出した場合は、

```text
REVISION_REQUIRED
        ↓
Early Stop Condition Detected
        ↓
Automatic Correction Stop
        ↓
Human Review Required
```

へ遷移する。

---

### Convergence Detection

Version 1では、修正ループが単に継続可能かだけでなく、修正が問題解決へ向かって収束しているかを確認する。

例えば、以下は非収束または悪化の兆候として扱う。

```text
同じ問題が解消されない

修正するたびに別の問題が発生する

変更範囲が拡大し続ける

Plan外変更が増加する

Test失敗数が増加する

以前成功していたTestが失敗する

Review指摘数または重大度が改善しない
```

このような状態では、

```text
まだ最大回数に達していない
```

ことだけを理由として自動修正を継続してはならない。

---

### Human Escalation

修正ループが早期停止または最大回数到達によって停止した場合、Application Layerは状態をHuman判断が必要な状態へ遷移させる。

Humanへ提示する情報には、少なくとも以下を含める。

```text
Original Implementation Evidence
Correction History
Review History
Current Source Code
Git Diff
Test Results
Remaining Review Issues
Stop Reason
Correction Count
```

Humanは、状況に応じて以下を判断できる。

```text
追加修正を許可する

Implementation Planを修正する

Specificationへ戻る

Architecture上の判断を行う

Implementation Branchを破棄する

別の実装方針を選択する
```

Humanによる判断なしに、自動的に修正回数上限を解除してはならない。

---

### Correction History

各修正について、何を指摘され、何を修正し、その結果がどう変化したかを追跡可能にする。

最低限、以下を識別できるようにする。

```text
correction_number
review_issues
correction_summary
changed_files
test_result
remaining_issues
```

これにより、Application LayerおよびChatGPT Reviewは、単一の修正結果だけでなく、修正ループ全体の推移を確認できる。

特に、同一指摘の繰り返しやTest Resultの悪化等を検出するために使用する。

---

### Review Rule

ChatGPT Reviewは、各修正を独立したImplementationとしてのみ評価してはならない。

必要に応じて以前のReviewおよび修正結果と比較し、

```text
問題が減っているか

同じ問題を繰り返していないか

新しい問題を発生させていないか

変更範囲が不必要に拡大していないか
```

を確認する。

したがって、修正ループの評価では、

```text
Current Result
```

だけでなく、

```text
Correction History
```

もReview Contextとして利用する。

---

### Decision Reason

修正ループを無制限に許可すると、CodexとChatGPT Reviewが収束しない修正を繰り返す可能性がある。

一方、最大回数だけで修正ループを制御すると、明らかに悪化または非収束している場合でも、設定された回数まで不要な修正を継続する可能性がある。

SpecFlowでは、Humanがすべての修正へ逐次介入するのではなく、AIによって安全に解決可能な修正については自動化する。

ただし、

```text
自動修正が正常に収束している
```

ことを自律継続の条件とする。

異常、悪化、非収束、承認範囲外変更等を検出した場合は、最大回数にかかわらず早期停止し、Humanへ判断を返す。

これにより、

```text
Humanの不要な介入を減らす
        +
無駄なAI修正ループを防止する
        +
異常を早期に検出する
        +
SpecificationおよびPlanからの逸脱拡大を防止する
```

ことを両立する。

以上の理由から、Version 1では、

```text
Maximum Correction Count
        +
Early Stop Conditions
        +
Convergence Detection
        +
Human Escalation
```

によって修正ループを制御する。

自動修正の最大回数は原則3回とする。

---

## 15.12 HumanがSpecificationを承認済みと判断する方法

**Status: Decided**

Version 1では、SpecificationがHumanによって承認済みであるかを、単純なBoolean FlagまたはSpecification本文中のStatus表記のみで判断しない。

Specificationを承認済みと判断するためには、Humanによる明示的な承認記録が存在し、その承認記録が現在のSpecificationと一致していることを確認する。

基本原則は、以下とする。

```text
Human Approval
        +
Approval Record
        +
Artifact Hash Verification
        ↓
Specification Approved
```

Humanによる承認は、

```text
Specificationという種類の文書を承認した
```

という意味ではなく、

```text
その時点における特定内容のSpecificationを承認した
```

という意味として扱う。

---

### Approval Source of Truth

Specificationの承認記録は、15.4で定義した`approvals/*.json`を正式な承認証拠として使用する。

概念的な構成は、以下とする。

```text
projects/specflow/
├── state.json
├── approvals/
│   └── specification_approval_001.json
└── docs/
    └── specifications/
        └── specification.md
```

Specification本文に、

```text
Status: Approved
```

等の記述が存在する場合でも、その記述のみを根拠としてApplication Layerが承認済みと判断してはならない。

同様に、

```json
{
  "specification_approved": true
}
```

のようなBoolean Flagのみを、正式な承認証拠として扱ってはならない。

正式な承認証拠は、Humanによって作成されたApproval Recordとする。

---

### Approval Record

Specification承認時には、少なくとも以下の情報を承認記録として保持する。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```

例：

```json
{
  "approval_id": "specification_approval_001",
  "artifact_type": "specification",
  "artifact_path": "projects/specflow/docs/specifications/specification.md",
  "artifact_hash": "<SHA-256 hash>",
  "decision": "approved",
  "approved_at": "2026-08-12T20:00:00+09:00",
  "comment": ""
}
```

`artifact_path`は、Humanが承認したSpecificationを識別するために使用する。

`artifact_hash`は、Humanが承認した時点のSpecification内容と、現在のSpecification内容が同一であることを確認するために使用する。

---

### Artifact Hash

Version 1では、Specificationの内容同一性を確認するために、SHA-256によるHashを使用する。

HumanがSpecificationを承認する際に、対象SpecificationのHashを計算し、Approval Recordへ保存する。

概念的には、以下とする。

```text
Specification
        ↓
Human Review
        ↓
Human Approval
        ↓
SHA-256計算
        ↓
Approval Record
        ↓
artifact_hash保存
```

後続工程へ進む前に、Application Layerは現在のSpecificationから再度Hashを計算する。

```text
Approval Record
artifact_hash
        │
        │ compare
        │
Current Specification
current_hash
```

両者が一致する場合、その承認記録は現在のSpecificationに対して有効である。

一致しない場合、その承認記録を現在のSpecificationに対する有効な承認として扱ってはならない。

---

### Approval Validation Rule

Version 1では、少なくとも以下の条件をすべて満たした場合にのみ、現在のSpecificationを承認済みと判断する。

```text
1. 対象Specificationに対応するApproval Recordが存在する

2. artifact_typeがSpecificationを示している

3. artifact_pathが現在の対象Specificationと一致する

4. decisionがapprovedである

5. Approval Recordのartifact_hashと
   現在のSpecificationから計算したHashが一致する
```

概念的には、以下とする。

```text
Approval Record Exists
        AND
Artifact Type Matches
        AND
Artifact Path Matches
        AND
Decision == Approved
        AND
Approved Hash == Current Hash
        ↓
Specification Approved
```

いずれかの条件を満たさない場合は、承認済みとして扱わない。

---

### Modification After Approval

Humanによる承認後にSpecificationが変更された場合、以前の承認を変更後のSpecificationへ自動的に引き継いではならない。

例えば、

```text
Specification A
        ↓
Human Approval
        ↓
Hash = AAA
        ↓
Specificationを変更
        ↓
Specification B
        ↓
Hash = BBB
```

となった場合、

```text
AAA != BBB
```

であるため、Specification Bは未承認として扱う。

この場合、以前のApproval Recordそのものを削除する必要はない。

以前の承認記録は、

```text
過去のSpecificationに対してHumanが承認した証拠
```

として保持できる。

ただし、現在のSpecificationに対する有効な承認としては使用しない。

変更後のSpecificationを後続工程で使用するためには、Humanによる再確認および新しい承認記録を必要とする。

---

### State Transition

Specification承認の有効性が確認された場合、Application Layerは承認結果に基づいて次の状態へ遷移できる。

概念的には、以下とする。

```text
Specification Draft
        ↓
Human Review
        ↓
Human Approval
        ↓
Approval Record作成
        ↓
Hash Verification
        ↓
Specification Approved
        ↓
Next State
```

一方、承認後の変更等によってHashが一致しない場合は、

```text
Approved Hash
        ≠
Current Hash
        ↓
Approval Invalid for Current Artifact
        ↓
後続工程へ進行しない
        ↓
Human Re-Approval Required
```

とする。

`state.json`は現在の進行状態を示すために使用するが、`state.json`に承認済み状態が記録されていることだけを根拠として、現在のSpecificationが有効に承認されていると判断してはならない。

必要な工程へ進む際には、Approval Recordと現在のArtifactの整合性を確認する。

---

### Human Explicit Approval

Specificationの承認は、Humanによる明示的な操作または明示的な意思表示によってのみ成立する。

ChatGPT、Codex、Application Layer、その他のAIまたは自動処理が、Humanの代わりにSpecificationを承認してはならない。

AIは、

```text
Specification appears complete
Specification is ready for approval
No blocking issue detected
```

等のReview結果または承認候補を提示できる。

しかし、それらを、

```text
Human Approved
```

へ自動的に変換してはならない。

基本的な責務分離は、以下とする。

```text
AI
= Review / Recommendation

Human
= Approval Decision

Application
= Approval Validation / State Transition
```

---

### Relationship with Other Approvals

Specification承認は、15.4で定義したHuman Approval管理方式の一種として扱う。

同じ原則は、必要に応じて以下のArtifactにも適用できる。

```text
Specification
Implementation Plan
Critical Change
Final Result
```

つまり、

```text
Humanが承認した
```

という事実だけではなく、

```text
HumanがどのArtifactの
どの内容を
いつ
どの判断として承認したか
```

を追跡可能にする。

Version 1では、Artifact HashをHuman ApprovalとArtifact内容を結びつけるための識別情報として使用する。

---

### Decision Reason

単純な、

```text
approved = true
```

という状態だけでは、Humanが具体的にどの内容を承認したのかを十分に保証できない。

また、Specification本文に`Status: Approved`と記載する方式では、承認後に本文が変更されてもStatus表記だけが残る可能性がある。

SpecFlowでは、Humanによる承認後もAIまたはHumanによってArtifactが変更される可能性がある。

そのため、

```text
Human Approval
        ↓
Approved Artifact Hash
        ↓
Current Artifact Hashとの比較
```

によって、現在使用しようとしているSpecificationがHumanによって実際に承認された内容と同一であることを確認する。

これにより、

- 承認後の無断変更を検出できる
- AIが変更後のSpecificationを承認済みとして誤認することを防止できる
- Humanが何を承認したのか追跡できる
- 過去の承認記録を保持できる
- 後続工程の開始条件を機械的に検証できる

という利点がある。

SpecFlowでは、承認を単なる状態Flagではなく、

```text
Humanが特定内容のArtifactに対して行った判断
```

として扱う。

以上の理由から、Version 1では、

```text
Explicit Human Approval
        +
Approval Record
        +
SHA-256 Artifact Hash
        +
Current Artifact Verification
```

をSpecification承認判定の基本方式とする。

---

## 15.13 ChatGPT RunnerとCodex Runnerの具体的な割り当て方法

**Status: Decided**

Version 1では、AI Runnerの割り当てについて、特定のAI製品名をApplication LayerのUseCase責務へ直接固定する方式は採用しない。

Application Layerでは、AIが担当する処理をRoleとして定義し、それぞれのRoleにRunnerを割り当てる。

Version 1では、RoleとRunnerの割り当ては固定とする。

基本原則は、以下とする。

```text
Application Layer
        ↓
AI Role
        ↓
Assigned Runner
```

Version 1では、

```text
Role-based Fixed Assignment
```

をAI Runner割り当ての基本方式として採用する。

---

### Basic Principle

Application Layerは、

```text
ChatGPTを使用する
Codexを使用する
```

というAI製品そのものを中心として処理を定義しない。

Application Layerが必要とする責務をRoleとして定義し、そのRoleを実行するRunnerを割り当てる。

概念的には、以下とする。

```text
Application UseCase
        ↓
Required Role
        ↓
Runner Assignment
        ↓
Concrete AI Runner
```

これにより、

```text
何を実行するか
```

というApplication上の責務と、

```text
どのAIが実行するか
```

というRunnerの割り当てを分離する。

---

### Version 1 Role Assignment

Version 1では、少なくとも以下のRoleを使用する。

```text
Plan Generation Role
Codex Prompt Generation Role
Implementation Review Role
Correction Instruction Role
Implementation Role
```

Version 1におけるRunnerの割り当ては、以下を基本とする。

```text
Plan Generation Role
        ↓
ChatGPT Runner

Codex Prompt Generation Role
        ↓
ChatGPT Runner

Implementation Review Role
        ↓
ChatGPT Runner

Correction Instruction Role
        ↓
ChatGPT Runner

Implementation Role
        ↓
Codex Runner
```

概念的には、以下のようになる。

```text
Human
  ↓
Specification
  ↓
Application Layer
  ↓
Plan Generation Role
  ↓
ChatGPT Runner
  ↓
Implementation Plan
  ↓
Human Approval
  ↓
Codex Prompt Generation Role
  ↓
ChatGPT Runner
  ↓
Codex Prompt
  ↓
Implementation Role
  ↓
Codex Runner
  ↓
Implementation
  ↓
Implementation Evidence
  ↓
Implementation Review Role
  ↓
ChatGPT Runner
  ↓
Review Result
```

修正が必要な場合は、

```text
Review Result
        ↓
Correction Instruction Role
        ↓
ChatGPT Runner
        ↓
Correction Instruction
        ↓
Implementation Role
        ↓
Codex Runner
        ↓
Correction
        ↓
Re-Review
```

とする。

---

### Responsibility of ChatGPT Runner

Version 1では、ChatGPT Runnerを主として、

```text
Planning
Instruction Generation
Review
Correction Instruction
```

を担当するRunnerとして使用する。

ChatGPT Runnerは、Specification、Approved Implementation Plan、Implementation Evidence、Source Code、Git Diff、Test Result等を参照し、Application Layerから要求されたRoleに応じた成果物を生成する。

ChatGPT Runner自身がApplication全体の状態遷移を決定してはならない。

状態遷移、Human Approvalの確認、修正ループの継続可否等は、Application Layerの責務として扱う。

---

### Responsibility of Codex Runner

Version 1では、Codex Runnerを主としてImplementation Roleを担当するRunnerとして使用する。

Codex Runnerは、Approved Implementation PlanおよびCodex Promptによって指定された範囲内で、

```text
Test作成・変更
Source Code作成・変更
必要なCommand実行
Test実行
実装結果の報告
```

等を行う。

Codex Runnerは、Human承認なしにSpecificationまたはApproved Implementation Planの範囲を拡張してはならない。

また、Codex Runner自身が、

```text
この変更はHuman承認済みである
このImplementationは最終承認可能である
```

と確定してはならない。

Codex RunnerはImplementation担当であり、Human Approvalおよび最終的な工程制御はApplication LayerとHumanの責務として扱う。

---

### Application Layer Responsibility

Application Layerは、RoleとRunnerの間を調整する。

概念的には、

```text
UseCase
   ↓
必要なRoleを決定
   ↓
Version 1のRunner Assignmentを参照
   ↓
対応RunnerへAIRequestを渡す
   ↓
AIResponseを受け取る
   ↓
次の工程を制御
```

とする。

Application Layerは、Runner内部のAI製品固有処理を可能な限り知る必要がない構造とする。

例えばApplication LayerにおけるReview処理は、

```text
Review Roleを実行する
```

ことを責務とし、

```text
ChatGPTという製品を直接操作する
```

ことを本質的な責務とはしない。

---

### Fixed Assignment in Version 1

Version 1では、RoleごとにRunnerを動的選択する機能は実装しない。

例えば、

```text
Cost
Speed
Context Capacity
Model Performance
Availability
Task Complexity
```

等を評価して、自動的にRunnerを切り替える処理はVersion 1の対象外とする。

Version 1では、

```text
Role
    ↓
Predefined Runner
```

という固定割り当てを使用する。

これにより、Architecture上の責務分離を維持しながら、MVPの実装複雑性を抑える。

---

### Runner Failure

Version 1では、割り当てられたRunnerが実行不能となった場合に、Application Layerが独自判断で別のAI Runnerへ自動的に切り替えてはならない。

例えば、

```text
ChatGPT Runner Failure
        ↓
自動的に別AIへ切替
```

または、

```text
Codex Runner Failure
        ↓
自動的に別Implementation AIへ切替
```

のようなFallback Routingは、Version 1では行わない。

Runner実行不能時は、失敗状態を記録し、再試行可能な場合は定められた範囲で再試行し、それでも処理できない場合は停止またはHuman判断が必要な状態へ遷移する。

これにより、Humanが認識しないまま異なるAIへ処理主体が変更されることを防止する。

---

### Role and Product Separation

Version 1では、

```text
Role
≠
AI Product
```

として扱う。

例えば、

```text
Implementation Review Role
```

はApplication上の責務であり、

```text
ChatGPT Runner
```

はVersion 1におけるそのRoleの実行担当である。

したがって、将来Runnerの割り当てが変更された場合でも、

```text
Implementation Review Role
```

というApplication上の責務そのものは維持できる構造とする。

同様に、

```text
Implementation Role
```

と、

```text
Codex Runner
```

も概念上は分離する。

---

### Future Extension

Version 1ではRole-based Fixed Assignmentを採用する。

一方、将来以下の必要性が生じた場合は、Runnerの動的割り当てを検討する。

```text
複数AI Providerを利用する場合

Roleごとに複数Runner候補を持つ場合

AI Modelごとの能力差を利用する場合

Context CapacityによってRunnerを選択する場合

CostまたはExecution Timeを考慮する場合

Runner障害時のFallbackが必要になった場合

Task ComplexityによってAI Modelを変更する場合
```

将来拡張候補は、概念的には以下とする。

```text
Application
      ↓
Role
      ↓
Runner Registry
      ↓
Runner Capability
      ↓
Assignment / Routing
      ↓
Concrete Runner
```

Runner Capabilityには、将来的に以下のような情報を持たせることを検討できる。

```text
Supported Roles
Context Capacity
Model Capability
Cost
Availability
Provider
```

これらを利用することで、将来的には、

```text
Role
  +
Task Requirements
  +
Runner Capability
        ↓
Dynamic Runner Assignment
```

へ拡張できる。

ただし、このDynamic Runner Assignment、Runner Registry、Capability-based Routing、および自動FallbackはVersion 1の実装対象には含めない。

Future Extensionとして本章に明示的に記録し、Version 1で意図的に採用しなかった設計候補として保持する。

---

### Decision Reason

AI製品をApplication Layerへ直接固定する方式は実装が単純であり、Version 1 MVPには適している。

一方で、

```text
Planning = ChatGPT
Review = ChatGPT
Implementation = Codex
```

という製品名そのものをApplicationの責務として固定すると、将来AI Runnerを変更する際にUseCaseやApplication Layerへ変更が波及する可能性がある。

逆に、Version 1から完全動的なRunner割り当てを実装すると、

```text
Runner Registry
Capability Management
Routing Rule
Fallback
Configuration Validation
Provider Difference Handling
```

等が必要となり、MVPとして過剰な複雑性を持ち込む。

そのためVersion 1では、

```text
役割は抽象化する
        +
担当Runnerは固定する
```

という中間方式を採用する。

これにより、

- Application Layerの責務をAI製品から分離できる
- Version 1の実装を単純に保てる
- Runnerのテストや差し替えを行いやすくできる
- 将来別のAI Runnerへ変更できる
- Dynamic Assignmentへの拡張余地を残せる

という利点を得る。

以上の理由から、Version 1では、

```text
Role-based Fixed Assignment
```

をChatGPT RunnerおよびCodex Runnerの割り当て方式として採用する。

---

## 15.14 承認済みImplementationのmerge責務

**Status: Decided**

Version 1では、Humanによる最終承認後のImplementation Branchから`developer`へのmergeは、Application Layerの責務として実行する。

Codex RunnerはImplementationを担当するが、承認済みImplementationを`developer`へmergeする責務を持たない。

Humanは、Implementationを`developer`へ取り込んでよいかを最終承認する。

Humanによる最終承認後、Application Layerは承認記録および対象Implementationを確認し、merge工程を開始する。

基本的な責務分離は、以下とする。

```text
Human
= Implementationを取り込んでよいか判断する

Application Layer
= Human承認を確認し、merge工程を制御する

Git操作Component / Service
= 実際のGit操作を実行する

Codex Runner
= Implementationを担当し、mergeは実行しない
```

概念的な流れは、以下とする。

```text
ChatGPT Review
        ↓
Human Final Approval
        ↓
Application Layer
        ↓
Approval Record確認
        ↓
対象Implementation Branch確認
        ↓
MergeApprovedImplementationUseCase
        ↓
Git操作Component / Service
        ↓
Implementation Branch
        ↓
developerへmerge
        ↓
merge成功
        ↓
completed
```

Application LayerのUseCase自身が、Gitコマンドの具体的な実行方法を直接担当することを原則としない。

Application Layerはmerge工程を制御し、実際のGit操作はGit操作を担当するComponentまたはServiceへ委譲する。

### MergeApprovedImplementationUseCase

Version 1では、承認済みImplementationを`developer`へ取り込むApplication UseCaseとして、

```text
MergeApprovedImplementationUseCase
```

を使用する。

このUseCaseは、少なくとも以下を確認した後にmergeを開始する。

```text
Human Final Approvalが存在する
Approval Recordが有効である
対象Implementation Branchが特定できる
対象Implementationが承認された内容と一致する
```

mergeが正常に完了した場合にのみ、Application Layerは開発状態を`completed`へ遷移できる。

mergeに失敗した場合は`completed`へ遷移してはならない。

### Decision Reason

Humanが最終承認した後のmergeは、Humanによる新たな設計判断ではなく、承認結果に基づいて実行される定型的な工程である。

そのため、Human自身がGit操作を手動で行う方式ではなく、Application Layerが工程を制御する方式を採用する。

一方、Codex Runnerへmergeを担当させると、

```text
Implementation
+
Stable Branchへの反映
```

を同じImplementation AIが担当することになり、15.8で採用したImplementation Branchによる隔離の意味を弱める。

そのため、

```text
Codex Runner
= Implementation

Human
= Approval

Application Layer
= Merge Control
```

として責務を分離する。

また、Application Layer自身にGit操作の詳細を持たせず、Git操作ComponentまたはServiceへ委譲することで、Application Layerを工程制御の責務に集中させる。

以上の理由から、Version 1では、

```text
Human Final Approval
        ↓
Application-controlled Merge
        ↓
developer
        ↓
completed
```

を採用する。

---

## 15.15 Open Issues

Version 1の正式Specification策定前にHumanによる決定を必要としていたApplication Layerの基本設計事項について、本章で列挙したOpen Issuesはすべて決定済みとなった。

したがって、現時点で本章に残るOpen Issueはない。

今後、新たな未決事項が発見された場合は、実装段階で暗黙に補完せず、必要に応じて本章または適切なDecision Documentへ追加し、Humanによる判断を行う。

また、本章で`Future Extension`として記録した事項は、Version 1の実装対象ではない。

Future Extensionは、将来の検討候補を保持するための記録であり、Humanによる新たな判断なしにVersion 1へ追加実装してはならない。

---

## 15.16 Approval Recordの生成・保存責務

**Status: Decided**

Version 1では、Human Approvalに関する判断、工程制御、Approval Recordの構築、および保存の責務を分離する。

責務分担は、以下を基本とする。

```text
Human
    ↓
Approval Decision
    ↓
Application Layer
    ↓
ApprovalRecordService
    ↓
ApprovalRecordRepository
    ↓
approvals/*.json
```

### Human

Humanは、承認対象Artifactの内容を確認し、承認、修正依頼、中止、その他必要な判断を行う。

Human Approvalの判断をApplication Layer、AI Runner、Service、Repository等が代替してはならない。

### Application Layer

Application Layerは、開発工程においてHuman Approvalが必要となる時点を制御し、Humanによる判断結果を受け取る。

Application Layerは、Humanの判断結果に基づいてApproval Recordの構築を依頼し、その後のState Transitionおよび後続工程への進行可否を制御する。

Application Layer自身がHumanに代わってApproval Decisionを生成してはならない。

### ApprovalRecordService

`ApprovalRecordService`は、HumanによるApproval Decisionと承認対象Artifactに関する情報を受け取り、15.4で定義した形式に従ってApproval Recordを構築する責務を持つ。

少なくとも以下の情報を扱う。

```text
approval_id
artifact_type
artifact_path
artifact_hash
decision
approved_at
comment
```

`artifact_hash`は、承認対象Artifactに対して定義された算出規則に従って生成する。

`ApprovalRecordService`は、HumanによるApproval Decisionの内容を独自に変更、補完、または代替してはならない。

また、承認対象Artifactの内容が適切であるかどうかを判断する責務を持たない。

### ApprovalRecordRepository

`ApprovalRecordRepository`は、`ApprovalRecordService`によって構築されたApproval Recordの保存および読み出しを担当する。

Version 1では、Approval Recordを`approvals/`配下のJSONファイルとして保存する。

`ApprovalRecordRepository`は、Human Approvalの判断、Approval Recordの内容に関する業務的判断、または後続工程への進行可否を決定してはならない。

### Common Use

`ApprovalRecordService`および`ApprovalRecordRepository`は、特定のApproval UseCase専用とはせず、以下のHuman Approvalで共通して利用可能な仕組みとする。

```text
Specification Approval
Implementation Plan Approval
Critical Change Approval
Final Approval
```

各Approvalで承認対象となるArtifactは異なるが、Humanによる判断を特定のArtifactおよびArtifact Hashと関連付けて記録する基本的な責務は共通とする。

### Responsibility Boundary

概念的な責務境界は、以下とする。

```text
Human
= 判断する

Application Layer
= いつ判断を求めるか、および判断後の工程を制御する

ApprovalRecordService
= Humanの判断をApproval Recordとして構築する

ApprovalRecordRepository
= Approval Recordを保存・読み出しする
```

この責務分離により、Human Approvalの判断主体と、承認記録の構築・保存処理を分離し、Application LayerまたはAIがHuman Approvalを暗黙的に代替することを防止する。

---

## 15.17 Approval Recordの検証責務

**Status: Decided**

Version 1では、保存されたApproval Recordが現在の承認対象Artifactに対して有効であるかを検証する共通責務を、`ApprovalValidationService`として定義する。

`ApprovalValidationService`はHumanによるApproval Decisionを行うものではなく、既に記録されたHuman Approvalと現在の承認対象Artifactとの整合性を検証する。

概念的な処理は、以下とする。

```text
Approval Record
        │
        ├── decision
        ├── artifact_type
        ├── artifact_path
        └── artifact_hash
                │
                │ compare
                │
Current Artifact
        │
        ├── artifact_type
        ├── artifact_path
        └── current_hash
                │
                ↓
    ApprovalValidationService
                ↓
        Validation Result
```

### Responsibility

`ApprovalValidationService`は、少なくとも以下を確認する。

```text
Approval Recordが存在する

decisionが要求された承認状態を示している

Approval Recordが現在の承認対象Artifactに対応している

現在のArtifactからHashを計算できる

Approval Recordのartifact_hashと
現在のArtifact Hashが一致する
```

対象となるApprovalの種類に応じて追加の同一性確認が必要な場合は、その確認も行う。

例えばFinal Approvalでは、15.4で定義したFinal Approval Target Artifactに基づき、Implementation Branch、HEAD Commit、Base Commit、および関連Artifact等の対応関係を確認する。

Critical Change Approvalでは、Approval Recordが現在のCritical Change Requestおよび対象Implementationに対応していることを確認する。

### Validation Result

`ApprovalValidationService`は、少なくとも以下の情報を返す。

```text
is_valid
approval_id
artifact_type
validation_errors
validation_warnings
```

`is_valid`は、Humanによる承認判断そのものを表すものではない。

`is_valid = true`は、

```text
Humanによって記録されたApprovalが、
現在の対象Artifactに対して有効である
```

ことを意味する。

`is_valid = false`は、

```text
現在の対象Artifactについて、
そのApproval Recordを有効なHuman Approvalとして使用できない
```

ことを意味する。

### Common Use

`ApprovalValidationService`は、特定のApproval UseCase専用とはせず、少なくとも以下のHuman Approvalの検証で共通して利用可能な仕組みとする。

```text
Specification Approval
Implementation Plan Approval
Critical Change Approval
Final Approval
```

各Approvalで必要となる追加の検証条件は異なるが、保存されたApproval Recordと現在の承認対象Artifactとの同一性および整合性を確認する基本責務は共通とする。

### Responsibility Boundary

責務境界は、以下とする。

```text
Human
= Artifactの内容を確認し、Approval Decisionを行う

Application Layer
= Approval Validationが必要な時点を制御し、
  Validation Resultに基づいて後続工程への進行可否を制御する

ApprovalRecordService
= Humanの判断をApproval Recordとして構築する

ApprovalRecordRepository
= Approval Recordを保存・読み出しする

ApprovalValidationService
= 保存されたApproval Recordが
  現在のArtifactに対して有効かを検証する
```

`ApprovalValidationService`は、承認対象Artifactの内容が要求として適切であるか、設計として妥当であるか、またはHumanが承認すべきかを判断してはならない。

また、無効なApproval Recordを自動的に有効化したり、Human Approvalを推定または補完したりしてはならない。

### Invalid Approval

以下の場合、現在のArtifactに対する有効なApprovalとして扱ってはならない。

```text
Approval Recordが存在しない

decisionが承認を示していない

Approval Recordと対象Artifactの対応関係を確認できない

現在のArtifact Hashを計算できない

artifact_hashとcurrent_hashが一致しない

Approval固有の追加検証条件を満たさない
```

Approval Validationに失敗した場合、Application Layerは、そのApprovalを前提とする後続工程へ進行させてはならない。

必要な場合は、Humanへ再承認を求める工程または適切な修正工程へ処理を返す。

### Separation of Decision and Validation

Human Approvalの判断とApproval Validationは、明確に区別する。

```text
Human
「このArtifactを承認する」
        ↓
Approval Record
        ↓
時間経過・工程進行
        ↓
ApprovalValidationService
「この承認記録は、
 今のArtifactにも有効か？」
```

`ApprovalValidationService`が行うのはHuman Decisionの再評価ではなく、Humanが承認した対象と現在の対象が同一であることの検証である。

この責務分離により、Humanによる意思決定を維持しながら、承認後にArtifactが変更された場合や、異なるArtifactに過去のApproval Recordが誤って使用されることを防止する。