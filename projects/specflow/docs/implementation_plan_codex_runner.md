# Implementation Plan: Codex Runner

## 1. Purpose

REQ-005〜REQ-008を実装するため、
Codex CLIを利用してImplementation Planを生成する
Codex Runnerを実装する。

本実装では、Codex CLIとの連携に必要な最小限の機能を対象とし、
Promptの入力、CLI実行、Implementation Planの保存、
および実行ログの保存までを実装する。

## 2. Scope

今回実装する対象は以下とする。

- CodexRunnerクラス
- Codex CLI呼び出し処理
- Promptの標準入力
- Implementation Plan保存
- 実行ログ保存

## 3. Design

### 3.1 Responsibilities

CodexRunnerは、以下の責務を持つ。

- Promptを受け取る
- Codex CLIを実行する
- 実行結果を取得する
- Implementation Planを保存する
- 実行ログを保存する

CodexRunnerは、単一責任の原則に従い、Codex CLIの実行に関する処理のみを担当する。

そのため、以下の処理は責務に含めない。

- Specificationや関連文書の読み込み
- Promptの生成
- Promptテンプレートの管理
- Reviewの生成
- Git操作
- 複数コンポーネントの実行順序の制御

### 3.2 Public API

CodexRunnerは、Promptとプロジェクトディレクトリを受け取り、
Codex CLIを実行する`run()`メソッドを提供する。

```python
result = runner.run(
    prompt=prompt,
    project_path=project_path,
)
```

#### Parameters

| Name | Description |
|------|-------------|
| `prompt` | Codex CLIへ標準入力として渡すPrompt |
| `project_path` | Codex CLIを実行する対象プロジェクトのルートディレクトリ |

#### Returns

`run()`は、Codex CLIの実行結果を表す`CodexRunResult`を返す。

`CodexRunResult`は、少なくとも以下の情報を保持する。

- 実行結果（成功／失敗）
- 終了コード
- 標準出力
- 標準エラー
- Implementation Planの保存先
- 実行ログの保存先

### 3.3 Processing Flow

CodexRunnerは、以下の順序で処理を実行する。

1. Promptとプロジェクトディレクトリを受け取る
2. Codex CLIを実行する
3. Codex CLIの実行結果を取得する
4. Implementation Planの出力を確認する
5. 実行ログを保存する
6. 実行結果を呼び出し元へ返す

### 3.4 Error Handling

CodexRunnerは、Codex CLIの実行および出力処理で発生したエラーを検出し、
呼び出し元へ通知する。

以下のエラーを対象とする。

- 入力値が不正である
- Codex CLIを起動できない
- Codex CLIの実行に失敗する
- Implementation Planを取得できない
- 実行ログを保存できない

CodexRunnerは、発生したエラーを握りつぶさず、
呼び出し元が失敗を判定できる形で通知する。

Codex CLIの実行後にエラーが発生した場合も、
取得できた実行結果は可能な範囲でログへ保存する。

### 3.5 Logging

CodexRunnerは、Codex CLIの実行履歴および障害解析のため、
実行内容および実行結果を`logs/latest.txt`へ保存する。

実行ログには、以下の情報を記録する。

- 実行日時
- 対象プロジェクトディレクトリ
- 実行したコマンド
- 実行結果（成功／失敗）
- 終了コード
- 標準出力
- 標準エラー
- docs/implementation_plan.mdを保存できたか

Codex CLIの実行に失敗した場合も、
取得できた実行結果を可能な範囲でログへ保存する。

Prompt本文は実行コマンドへ含めず、
標準入力として渡したことを記録する。

認証情報や環境変数などの機密情報は、
実行ログへ保存しない。

## 4. Implementation Steps

## 5. Test Plan

## 6. Out of Scope