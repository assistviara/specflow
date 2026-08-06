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

# 15. Open Issues Before Formal Specification

正式Specification策定前に、以下を決定する必要がある。

1. Application Layerを配置するPythonパッケージ
2. UseCaseの命名規則
3. UseCase入力・出力DTOの形式
4. 承認記録の保存形式
5. 状態管理の保存形式
6. Implementation Evidenceの正式なフォーマット
7. Codexの停止・再開方式
8. Source CodeおよびGit Diffの取得方法
9. Review用Promptの入力上限と分割方法
10. TDDを必須とする範囲
11. 修正ループの最大回数
12. HumanがSpecificationを承認済みと判断する方法
13. ChatGPT RunnerとCodex Runnerの具体的な割り当て方法

これらは、Humanの判断なしに実装段階で補完してはならない。


