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
```

Application Layerは、AIが自律的に開発を完結させるための層ではない。

Humanの判断と承認を各工程の境界として維持しながら、現在手作業で行っているAI間の成果物受け渡しを自動化する。

---

# 2. Version 1 Scope

## 2.1 AI Role

SpecFlow Version 1では、AIの役割を次に限定する。

| 役割                    | 担当      |
| --------------------- | ------- |
| Implementation Plan生成 | ChatGPT |
| Codex用Prompt生成        | ChatGPT |
| 実装                    | Codex   |
| テスト作成・実行              | Codex   |
| 実装レビュー                | ChatGPT |
| 最終判断・承認               | Human   |

汎用的なAIRunnerの構造は維持する。

ただし、Version 1の実行構成では、Claude、Gemini、Local LLM等を使用しない。

これらは将来の拡張対象とする。

---

## 2.2 MVP Boundary

Version 1 MVPは、次の一本の開発フローを実行可能にする。

```text
HumanがSpecificationを作成
        ↓
ChatGPTがImplementation Plan Draftを生成
        ↓
HumanがPlanを承認または差し戻し
        ↓
ChatGPTがCodex用Promptを生成
        ↓
Codexが実装とテストを実行
        ↓
Implementation Evidenceを保存
        ↓
ChatGPTがレビュー
        ↓
Humanが最終承認または差し戻し
```

Version 1では、複数のAIを動的に選択する高度な機能、複数ユーザー管理、並列実装、高度なGit自動化は必須としない。

---

# 3. Application Layer Responsibility

Application Layerは、以下を担当する。

* HumanまたはUIからUseCase実行要求を受け取る
* 現在の開発状態を確認する
* 次に実行可能なUseCaseを制御する
* 必要なEngineおよびAI Runnerを呼び出す
* 各工程の成果物を次工程へ受け渡す
* Human承認を記録する
* Human未承認時に次工程への進行を停止する
* 実装証拠をReview工程へ渡す
* Review不適合時に修正工程へ戻す
* 実行結果と状態遷移を呼び出し元へ返す

---

# 4. Non-Responsibility

Application Layerは、以下を直接実装しない。

* Markdown文書の解析
* Prompt Templateの展開
* AI Provider固有の通信
* Codexの内部実装処理
* テストコードの具体的な生成
* Specificationの内容変更
* Implementation Planの内容決定
* Review結果の最終判断
* Humanに代わる承認

これらは、それぞれ既存Engine、AI Runner、またはHumanの責務とする。

---

# 5. Version 1 MVP Overall Flow

## 5.1 Main Flow

```text
[Human]
Specificationを作成・選択
        ↓
[Application Layer]
Plan生成UseCaseを開始
        ↓
[ChatGPT]
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
[ChatGPT]
Codex用Implementation Promptを生成
        ↓
[Application Layer]
実装開始要求をCodexへ渡す
        ↓
[Codex]
テスト作成
        ↓
テスト失敗確認
        ↓
必要最小限の実装
        ↓
テスト実行
        ↓
Implementation Evidence生成
        ↓
[Application Layer]
Review用入力を構築
        ↓
[ChatGPT]
Specification・Plan・Code・Test・Logをレビュー
        ↓
[Application Layer]
最終承認待ちへ遷移
        ↓
[Human]
最終承認 または 差し戻し
```

---

## 5.2 TDD Position

Version 1では、Codexの実装手順としてTDDを基本とする。

```text
Specification
    ↓
期待動作をテストとして表現
    ↓
テスト失敗を確認
    ↓
必要最小限の実装
    ↓
テスト成功を確認
    ↓
既存テストを実行
```

TDDはSpecificationに代わるものではない。

Specificationが唯一の正本であり、TestはSpecificationを検証可能な形で表現した成果物として扱う。

---

# 6. Required UseCases

## UC-01 Load Development Input

### Purpose

開発対象となるSpecificationおよび関連文書を受け取る。

### Input

* Constitution
* Principles
* Specification
* Decisions
* Implementation Plan Template
* Plan Prompt Template
* Project Metadata

### Output

* 読み込み対象情報
* 入力検証結果
* 開発対象識別情報

### Notes

Version 1では、ファイル選択またはPath指定による入力を許容する。

Project Loaderが未実装であるため、Project全体の自動読み込みは必須としない。

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

生成物はDraftであり、Human承認前に実装工程へ渡してはならない。

---

## UC-03 Request Plan Approval

### Purpose

Implementation Plan DraftをHumanへ提示し、判断を受け取る。

### Human Actions

* 承認
* 修正依頼
* 中止

### Approval Record

* 対象Plan
* 判断
* 判断日時
* コメント
* 修正依頼内容

---

## UC-04 Revise Implementation Plan

### Purpose

Humanからの修正依頼を基にImplementation Plan Draftを再生成する。

### Input

* 現在のImplementation Plan Draft
* Humanの修正理由
* 元のSpecification
* 関連文書

### Output

* 修正版Implementation Plan Draft
* 変更点
* 前版との対応情報

### Transition

修正版生成後は、再びPlan承認待ちへ戻る。

---

## UC-05 Generate Codex Implementation Prompt

### Purpose

承認済みImplementation Planを基にCodex用Promptを生成する。

### Input

* 承認済みSpecification
* 承認済みImplementation Plan
* 実装対象Path
* TDD実行ルール
* 完了条件
* 停止条件
* Log出力要件

### Output

* Codex用Implementation Prompt

### Rule

未承認のImplementation PlanからPromptを生成してはならない。

---

## UC-06 Execute Codex Implementation

### Purpose

Codexを使用して、承認済みPlanに沿った実装とテストを行う。

### Processing

```text
Codex用Prompt
    ↓
テスト作成
    ↓
失敗確認
    ↓
実装
    ↓
対象テスト実行
    ↓
既存テスト実行
```

### Output

* Codex実行結果
* Implementation Evidence
* Human確認要求
* 成功または失敗

### Rule

CodexはSpecificationまたはPlanにない変更を行ってはならない。

---

## UC-07 Request Critical Change Approval

### Purpose

Codex実行中に重要な変更が必要になった場合、処理を停止してHuman承認を求める。

### Critical Changes

* DB変更
* 認証変更
* 権限変更
* 外部API変更
* 依存ライブラリ変更
* PKL互換性を損なう変更
* データ消失の可能性がある変更
* その他の破壊的変更
* SpecificationまたはPlanに記載されていない変更

### Human Actions

* 承認して続行
* 修正を依頼
* 実装を中止
* SpecificationまたはPlanの再検討へ戻す

### Rule

Human承認前に重要変更を実行してはならない。

---

## UC-08 Collect Implementation Evidence

### Purpose

Codexによる実装の証拠を収集し、Review工程へ渡せる形にする。

### Output

Implementation Evidenceを生成する。

詳細は第9章に定義する。

---

## UC-09 Review Implementation

### Purpose

ChatGPTが以下を照合し、実装適合性を評価する。

* Specification
* 承認済みImplementation Plan
* Source Code
* Test Code
* Test Result
* Implementation Evidence

### Output

* Review Report
* 適合または不適合
* 不適合箇所
* 根拠
* 修正対象
* 修正工程の返却先
* Humanへの確認事項

### Rule

ReviewはSpecification自体を変更してはならない。

---

## UC-10 Request Final Approval

### Purpose

Review ReportをHumanへ提示し、最終判断を受け取る。

### Human Actions

* 最終承認
* 実装修正へ戻す
* Plan修正へ戻す
* Specification再検討へ戻す
* 中止

---

## UC-11 Resume Correction

### Purpose

Review不適合またはHuman差し戻しを受け、適切な修正工程へ戻す。

### Return Destination

| 問題                    | 戻り先             |
| --------------------- | --------------- |
| Specification不足・矛盾    | Specification策定 |
| Implementation Plan不備 | Plan修正          |
| Codex用Prompt不備        | Prompt再生成       |
| 実装不備                  | Codex再実装        |
| テスト不足・誤り              | Test修正          |
| 判断不能                  | Human判断         |

---

# 7. Human Approval Points

Version 1では、少なくとも以下のHuman承認ポイントを設ける。

## Approval Point 1: Specification

SpecificationはHumanが作成または承認する。

Application Layerは、未承認Specificationを実装工程へ渡してはならない。

---

## Approval Point 2: Implementation Plan

ChatGPTが生成したImplementation Plan DraftをHumanが確認する。

Humanが承認するまでCodex用Prompt生成へ進んではならない。

---

## Approval Point 3: Critical Change

Codex実行中に重要変更が必要になった場合、Human承認を求める。

承認されない場合、変更を実行してはならない。

---

## Approval Point 4: Final Review

ChatGPTによるReview ReportをHumanが確認する。

Human承認前に開発工程をCompletedとしてはならない。

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

```text
Codex Implementation
    ↓
Test Failure または Review不適合
    ↓
修正指示生成
    ↓
Codex再実装
    ↓
再テスト
    ↓
再レビュー
```

修正時は、元のSpecificationと承認済みPlanを引き続き基準とする。

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

Version 1では、修正回数を記録する。

自動で無制限に再試行してはならない。

再試行回数の上限値は、正式Specificationまたは設定で定義する。

上限到達時はHumanへ判断を返す。

---

# 9. Implementation Evidence / Log

## 9.1 Purpose

Implementation Evidenceは、Codexが何を行ったかをReview可能にするための証拠である。

単なるデバッグログではなく、Specification、Plan、Code、Testを結びつける追跡情報として扱う。

---

## 9.2 Required Information

Version 1では、少なくとも以下を記録する。

* Codexへ渡したPrompt
* Codexの実行結果
* 変更したファイル
* ファイルごとの変更概要
* 実行したコマンド
* 作成または変更したテスト
* 対象テスト結果
* 既存テスト結果
* エラー内容
* 警告内容
* 未完了事項
* Humanへ確認した事項
* Humanの回答
* 実行開始・終了情報
* 使用したSpecification
* 使用したImplementation Plan

---

## 9.3 Version 1 Format

Version 1では、`log.txt`を利用可能とする。

ただし、Review工程で安定して利用できるよう、一定の章構造を持たせる。

```text
# Implementation Evidence

## Input
- Specification
- Implementation Plan
- Codex Prompt

## Changed Files

## Commands Executed

## Tests Created or Updated

## Test Results

## Errors

## Warnings

## Human Approval Requests

## Unfinished Items

## Codex Summary
```

将来はJSON等の構造化形式へ拡張できる。

Version 1では、読みやすさと実装容易性を優先し、テキスト形式を許容する。

---

## 9.4 Review Input

Review工程には、少なくとも以下を渡す。

```text
Specification
Approved Implementation Plan
Source CodeまたはGit Diff
Test Code
Test Result
Implementation Evidence / Log
```

Logのみを根拠にレビューしてはならない。

可能な範囲で、実際のCode、Diff、Test Resultと照合する。

---

## 9.5 Immutability

Review開始後、対象となるImplementation Evidenceを上書きしてはならない。

再実装を行った場合は、新しいEvidenceを生成し、版または実行IDで区別する。

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
final_approval_pending
        ↓
completed
```

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

```text
implementing
        ↓
critical_approval_pending
        ├── 承認
        │      ↓
        │  implementing
        │
        ├── 修正
        │      ↓
        │  correction_requested
        │
        └── 中止
               ↓
           cancelled
```

---

## 10.5 Review Failure Transition

```text
reviewing
        ↓
review_failed
        ↓
correction_requested
        ├── Specification修正
        ├── Plan修正
        ├── Prompt修正
        ├── Implementation修正
        └── Test修正
```

修正完了後は、問題の種類に応じた工程へ戻る。

---

## 10.6 Final Rejection Transition

```text
final_approval_pending
        ↓
correction_requested
        ↓
指定された修正工程
```

Humanによる最終承認がない限り、`completed`へ遷移してはならない。

---

# 11. Application Layer Structure

Version 1では、Application Layerを一つの巨大なクラスにしない。

HumanまたはUIの操作単位でUseCaseを分割する。

概念的な構成は次のとおりとする。

```text
Application Layer
├── LoadDevelopmentInput
├── GenerateImplementationPlan
├── ApproveImplementationPlan
├── ReviseImplementationPlan
├── GenerateCodexPrompt
├── ExecuteImplementation
├── ApproveCriticalChange
├── CollectImplementationEvidence
├── ReviewImplementation
├── ApproveFinalResult
└── ResumeCorrection
```

各UseCaseは、必要な既存EngineまたはServiceを利用する。

UseCaseは、他のUseCaseの内部処理を直接書き換えてはならない。

---

# 12. Existing Component Usage

現在実装済みの以下のコンポーネントは再利用する。

* `PlanPromptGenerator`
* `PromptAdapter`
* `AIRequest`
* `AIResponse`
* `AIService`
* `AIRunner`
* `OpenAIAPIRunner`
* `CodexRunner`

以下は未実装であるため、Version 1の前提として扱わない。

* `ProjectLoader`
* `ReviewRunner`
* `StateManager`

これらは、正式Specification策定後に必要性と責務を定義する。

---

# 13. Error and Stop Conditions

以下の場合、Application Layerは処理を停止する。

* 必要な正式文書が存在しない
* Specificationが未承認
* Implementation Planが未承認
* Prompt生成に失敗した
* PromptResultがAI実行可能でない
* ChatGPTまたはCodex実行に失敗した
* Codexが重要変更の必要性を報告した
* Testが失敗した
* Implementation Evidenceが不足している
* Reviewに必要な成果物が不足している
* Specificationに不足・矛盾・不明確さがある
* Human判断が必要である

停止時は、少なくとも以下を返す。

* 停止理由
* 現在の状態
* 影響範囲
* 次に必要なHuman操作
* 再開可能な工程

---

# 14. MVP Completion Conditions

SpecFlow Version 1 MVPは、以下を満たした場合に完成とする。

* UIまたは呼び出し元からSpecificationを指定できる
* ChatGPTがImplementation Plan Draftを生成できる
* HumanがPlanを承認または差し戻しできる
* 承認済みPlanからCodex用Promptを生成できる
* CodexがTDDを基本として実装とテストを行える
* CodexのImplementation Evidenceを保存できる
* Specification、Plan、Code、Test、LogをChatGPTへ渡せる
* ChatGPTがReview Reportを生成できる
* Humanが最終承認または差し戻しできる
* Review不適合時に適切な修正工程へ戻れる
* Human承認なしに次工程へ進まない
* 各工程と承認の履歴を追跡できる

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
GenerateImplementationPlanUseCase
ApproveImplementationPlanUseCase
ReviseImplementationPlanUseCase
GenerateCodexPromptUseCase
ExecuteImplementationUseCase
CollectImplementationEvidenceUseCase
ReviewImplementationUseCase
ApproveFinalResultUseCase
ResumeCorrectionUseCase
```

対応するPythonファイル名はsnake_caseとし、クラス名と対応関係が分かる名称とする。

例：

```text
generate_implementation_plan_use_case.py
approve_implementation_plan_use_case.py
revise_implementation_plan_use_case.py
generate_codex_prompt_use_case.py
execute_implementation_use_case.py
collect_implementation_evidence_use_case.py
review_implementation_use_case.py
approve_final_result_use_case.py
resume_correction_use_case.py
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

## 15.7 Open Issues

正式Specification策定前に、以下の事項を引き続き決定する必要がある。

1. Codexの停止・再開方式
2. Source CodeおよびGit Diffの取得方法
3. Review用Promptの入力上限と分割方法
4. TDDを必須とする範囲
5. 修正ループの最大回数
6. HumanがSpecificationを承認済みと判断する方法
7. ChatGPT RunnerとCodex Runnerの具体的な割り当て方法

これらの未決事項は、Humanの判断なしに実装段階で補完してはならない。