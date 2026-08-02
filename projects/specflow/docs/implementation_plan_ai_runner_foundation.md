# Implementation Plan

Version: 0.1.0

---

# 1. 基本情報

## プロジェクト名

SpecFlow

## 対象機能

AI Runner Foundation

## Plan作成日

2026-08-02

## 作成者

たけしゃん

---

# 2. 対象Specification

AI Runner Foundation

Version 0.1.0

# 3. Specificationの理解

AI Runner Foundationは、

Promptを受け取り、

利用可能なAIへ実行を依頼し、

AI実行結果を
共通形式で返す
実行基盤である。

Specificationでは、

AI実行の責務のみを定義している。

本Implementation Planでは、

Specificationを満たすための

- データ構造
- クラス構成
- 処理フロー
- エラー処理

を設計する。

Prompt生成、

Review、

Human承認は、

本Implementation Planの対象外とする。

# 4. 設計方針

AI Runner Foundationは、

AIごとの実行方法の違いを
共通インターフェースの背後へ分離する。

上位コンポーネントは、

利用するAI固有の実行方法を
意識せず、

共通の入力形式で
AI実行を依頼し、

共通の出力形式で
結果を受け取る。

AI Runner Foundationは、

以下の要素に責務を分離する。

- AI実行時の入力データ
- AI実行結果のデータ
- AI Runnerの共通インターフェース
- AI固有のRunner
- Prompt生成結果からAI実行入力への変換
- AI実行処理の委譲
- AI Runnerの生成

各要素は、

一つの責務だけを持ち、

上位コンポーネントが
AI固有の実装へ直接依存しない構造とする。

# 5. コンポーネント構成

本Implementation Planでは、

AI Runner Foundationを

以下のコンポーネントへ分割する。

|コンポーネント|責務|
|--------------|-----------------------------|
|AIRequest|AI実行入力を保持する|
|AIResponse|AI実行結果を保持する|
|AIRunner|AI実行の共通インターフェース|
|DummyAIRunner|テスト用AI実装|
|OpenAIAPIRunner|OpenAI Responses API実装|
|PromptAdapter|PromptResultをAI入力へ変換する|
|AIService|AI実行処理を委譲する|
|Runner生成関数|利用するAI Runnerを生成する|

# 6. データ構造

本Implementation Planでは、

AI Runner Foundationで利用する
共通データ構造として、

AIRequestおよび
AIResponseを定義する。

これらのデータ構造は、

AIの種類に依存せず、

上位コンポーネントと
AI Runnerとの間で
共通に利用する。

---

## 6.1 データ受け渡し

```text
PromptResult
      │
      ▼
PromptAdapter
      │
      ▼
AIRequest
      │
      ▼
AIService
      │
      ▼
AI固有Runner
（AIRunnerインターフェースを実装）
      │
      ▼
AIResponse
```

AI Runner Foundationでは、

PromptResultを
PromptAdapterが変換し、

AIRequestとして
AIServiceへ渡す。

AIServiceは、

AIRunnerインターフェースを実装した
AI固有Runnerへ
AI実行を委譲する。

AI固有Runnerは、

AI実行結果を
AIResponseとして返す。

---

## 6.2 AIRequest

### 責務

AIRequestは、

AI実行時の入力データを保持する。

### 保持する項目

|項目|型|説明|
|----|---|----------------------------|
|prompt|str|AIへ渡すPrompt|

### 制約

- `prompt`は文字列であること
- `prompt`は空でないこと
- `prompt`は空白のみでないこと
- 作成後は内容を変更できないこと

---

## 6.3 AIResponse

### 責務

AIResponseは、

AI実行結果を保持する。

### 保持する項目

|項目|型|説明|
|----|---|------------------------------|
|content|str|AIが生成した内容|
|success|bool|実行成功可否|
|error_message|str \| None|失敗理由|

### 成功時

|項目|値|
|----|--------------------------|
|success|True|
|content|AI生成結果|
|error_message|None|

### 失敗時

|項目|値|
|----|--------------------------|
|success|False|
|content|空文字を許容|
|error_message|エラー内容|

### 制約

- `content`は文字列であること
- `success`は真偽値であること
- `error_message`は文字列または`None`であること
- 成功時は`error_message`を保持してはならない
- 失敗時は`error_message`を必須とする
- 作成後は内容を変更できないこと

# 7. コンポーネント関連図

AI Runner Foundationを構成する
主要コンポーネントの関係を
以下に示す。

```text
                 PromptResult
                      │
                      ▼
               PromptAdapter
                      │
                      ▼
                  AIRequest
                      │
                      ▼
                  AIService
                      │
                      ▼
        AIRunnerインターフェース
              △               △
              │               │
     DummyAIRunner   OpenAIAPIRunner
              │               │
              └───────┬───────┘
                      ▼
                 AIResponse
```

## コンポーネント間の役割

|コンポーネント|役割|
|--------------|--------------------------------|
|PromptAdapter|PromptResultをAIRequestへ変換する|
|AIRequest|AI実行時の入力データを保持する|
|AIService|AI実行処理をAIRunnerへ委譲する|
|AIRunner|AI実行の共通インターフェースを提供する|
|DummyAIRunner|テスト用AI実装を提供する|
|OpenAIAPIRunner|OpenAI Responses APIを利用したAI実装を提供する|
|AIResponse|AI実行結果を保持する|

AI Runner Foundationでは、

上位コンポーネントは
AIServiceのみを利用する。

AI固有の実装は、

AIRunnerインターフェースの
背後へ隠蔽される。

これにより、

AIの種類による違いは、

上位コンポーネントへ
影響を与えない構造とする。

# 8. 処理フロー

## 8.1 正常時

AI Runner Foundationは、

以下の順序で処理を実行する。

```text
PromptResult
      │
      ▼
PromptAdapter
      │
      ▼
AIRequest
      │
      ▼
AIService
      │
      ▼
AI固有Runner
（AIRunnerインターフェースを実装）
      │
      ▼
AIResponse
      │
      ▼
呼び出し元へ返却
```

### 処理手順

1. PromptResultを受け取る
2. PromptAdapterがAIRequestへ変換する
3. AIServiceがAI実行を開始する
4. AIServiceが、AIRunnerインターフェースを実装したAI固有Runnerへ処理を委譲する
5. AI固有RunnerがAIを実行する
6. AI固有RunnerがAIResponseを生成する
7. AIServiceがAIResponseを呼び出し元へ返す

---

## 8.2 入力不正時

Promptが入力条件を満たさない場合は、

AIを実行せず、
入力内容に応じた例外を返す。

```text
PromptまたはPromptResult
      │
      ▼
入力検証
      │
      ▼
TypeErrorまたはValueError
```

### 入力エラー

- Promptが文字列ではない場合は`TypeError`とする
- Promptが空または空白のみの場合は`ValueError`とする
- PromptResultが実行可能な状態ではない場合は`ValueError`とする
- 入力不正時はAIを実行しない

---

## 8.3 AI実行失敗時

AI実行中にエラーが発生した場合は、

AI固有Runnerが
エラーを共通形式へ変換する。

```text
AI固有Runner
      │
      ▼
AI実行エラー
      │
      ▼
AIResponse
success=False
      │
      ▼
AIService
      │
      ▼
呼び出し元へ返却
```

### AI実行エラー

- AI実行中の例外は失敗したAIResponseへ変換する
- エラー内容を`error_message`へ保持する
- AI実行エラーを握りつぶしてはならない
- AIの種類にかかわらず共通形式で返す

# 9. 変更対象ファイル

本Implementation Planでは、

既存実装との適合確認および
必要な差分修正の対象として、

以下のファイルを扱う。

|ファイル|役割|変更内容|
|---------|-------------------------------|----------------------------|
|core/ai/ai_request.py|AI実行入力|入力データ構造|
|core/ai/ai_response.py|AI実行結果|出力データ構造|
|core/ai/ai_runner.py|共通インターフェース|AI Runner抽象基底|
|core/ai/ai_service.py|AI実行委譲|Runner呼び出し|
|core/ai/prompt_adapter.py|Prompt変換|PromptResult→AIRequest|
|core/ai/dummy_runner.py|テスト実装|Dummy AI|
|core/ai/openai_api_runner.py|OpenAI実装|Responses API|
|core/ai/openai_client_factory.py|OpenAIクライアント生成|OpenAIクライアントの生成|
|core/ai/runner_builder.py|Runner生成|OpenAI Runner生成関数|
|tests/test_ai_request.py|入力テスト|AIRequest|
|tests/test_ai_response.py|出力テスト|AIResponse|
|tests/test_ai_runner.py|AIRunnerテスト|抽象インターフェースの確認|
|tests/test_ai_service.py|AIServiceテスト|委譲確認|
|tests/test_dummy_runner.py|Dummy Runnerテスト|Dummy実装|
|tests/test_openai_api_runner.py|OpenAI Runnerテスト|API実装|
|tests/test_openai_client_factory.py|Client Factoryテスト|OpenAIクライアント生成の確認|
|tests/test_prompt_adapter.py|PromptAdapterテスト|Prompt変換|
|tests/test_runner_builder.py|Runner生成テスト|Runner生成|
|tests/test_ai_execution_pipeline.py|統合テスト|Prompt生成からAI実行までの確認|

本Implementation Planでは、

原則として、

上記以外のファイルは
変更対象としない。

追加の変更が必要となった場合は、

Implementation Planを更新し、

人間の承認を得るものとする。

# 10. テスト計画

本Implementation Planでは、

AI Runner Foundationが
Specificationを満たしていることを
確認するため、

以下の観点でテストを実施する。

---

## 10.1 単体テスト

各コンポーネントの責務を
個別に検証する。

|対象|確認内容|
|------|------------------------------|
|AIRequest|入力データの検証|
|AIResponse|実行結果データの検証|
|AIRunner|共通インターフェースであること|
|PromptAdapter|PromptResultからAIRequestへの変換|
|DummyAIRunner|テスト用AI実装|
|OpenAIAPIRunner|OpenAI Responses API実装|
|OpenAIClientFactory|OpenAIクライアント生成|
|AIService|AI実行処理の委譲|
|Runner生成関数|OpenAI Runnerを正しく構築できること|

---

## 10.2 統合テスト

Prompt生成結果から
AI実行までの
一連の流れを検証する。

```text
PromptResult
      │
      ▼
PromptAdapter
      │
      ▼
AIRequest
      │
      ▼
AIService
      │
      ▼
AI固有Runner
（AIRunnerインターフェースを実装）
      │
      ▼
AIResponse
```

確認項目

- Prompt生成結果をAIへ渡せること
- AI実行結果を取得できること
- 共通形式で結果を返せること

---

## 10.3 異常系テスト

### 入力不正

以下の場合に、
AIを実行せず、
適切な例外を返すことを確認する。

- Promptが文字列ではない
- Promptが空である
- Promptが空白のみである
- PromptResultが実行可能な状態ではない

### AI実行失敗

以下の場合に、
失敗したAIResponseを返すことを確認する。

- AI実行中に例外が発生する
- AIから有効な実行結果を取得できない

AI実行失敗時は、

- `success`が`False`であること
- `error_message`に確認可能な失敗理由があること
- AIの種類に依存しない共通形式であること

を確認する。

---

## 10.4 回帰テスト

AI Runner Foundationの追加により、

既存機能へ影響がないことを確認する。

確認対象

- Prompt生成機能
- Template Engine
- Plan Prompt Generator
- 既存テストがすべて成功すること

# 11. 完了条件

本Implementation Planは、

以下の条件をすべて満たした時点で
完了とする。

- AIRequestおよびAIResponseが設計どおり実装されていること
- AIRunnerインターフェースを通じてAI実行を行えること
- AI固有Runnerが共通インターフェースを実装していること
- PromptAdapterからAIRequestへの変換が行えること
- AIServiceがAI実行を適切に委譲できること
- AI実行結果をAIResponseとして共通形式で返却できること
- AI実行失敗時に共通形式でエラーを返却できること
- 単体テスト、統合テスト、異常系テスト、回帰テストが成功すること
- Specificationの要求事項をすべて満たしていること
- 実装内容が本Implementation Planと整合していること

# Closing

AI Runner Foundationは、

単にAIを呼び出すための
コンポーネントではない。

SpecFlowにおいて、

AI実行を共通化し、

AI固有の実装を
上位コンポーネントから分離する
実行基盤である。

本Implementation Planは、

AI Runner Foundationの
設計指針を示すものであり、

以後の実装、

レビュー、

保守は、

本Implementation Planに従って
実施する。