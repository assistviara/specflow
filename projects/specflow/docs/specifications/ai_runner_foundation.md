# Specification

Version: 0.1.0

---

# 1. 基本情報

## プロジェクト名

SpecFlow

## 機能名

AI Runner Foundation

## 仕様作成日

2026-08-02

## 仕様作成者

たけしゃん

---

# 2. 責務（Responsibility）

AI Runner Foundationは、

SpecFlowが生成したPromptを
AIへ実行依頼し、

実行結果を
共通形式で返すための
実行基盤である。

AI Runner Foundationは、

AI実行以外の責務を持たない。

## 実施すること

- Promptを受け取る
- AIを実行する
- 実行結果を共通形式で返す
- 実行失敗を共通形式で返す

## 実施しないこと

- Specificationの読み込み
- Promptの生成
- 生成結果のレビュー
- Humanによる承認
- Git操作
- state.jsonの更新

# 3. 背景

現在のSpecFlowでは、

Prompt生成と
AI実行が分離されている。

しかし、

AIごとに実行方法が異なるため、

AI固有の実装が
上位コンポーネントへ
影響を与える可能性がある。

SpecFlowでは、

AIの種類に依存しない
共通実行基盤を設けることで、

Prompt生成などの
上位コンポーネントから

AI固有の実装を分離する。

また、

AI実行結果を
共通形式で提供することで、

Reviewおよび
Human承認工程が、

AIの種類に依存せず
共通の処理を行えるようにする。

# 4. 目的

SpecFlowから

AI実行を

共通の方法で提供し、

AI実行結果を

共通形式で扱えるようにする。

これにより、

AIの種類による違いを

上位コンポーネントから分離し、

実装変更の影響範囲を

最小化する。

# 5. 利用者

- Prompt生成機能
- Review機能
- 開発者

# 6. 入力

- Prompt

# 7. 出力

- AI実行結果

# 8. 機能要件

## 必須要件

### REQ-001 Promptの受け取り

AI Runner Foundationは、

AI実行対象となる
Promptを受け取れること。

### REQ-002 Promptの検証

### REQ-002 Promptの検証

AI Runner Foundationは、

Promptが
入力条件を満たすことを
確認できること。

入力条件を満たさないPromptを
AIへ渡してはならない。

### REQ-003 AIの実行

AI Runner Foundationは、

受け取ったPromptを
利用可能なAIへ渡し、

AI実行を開始できること。

### REQ-004 実行成功結果の返却

AI実行に成功した場合、

生成された内容と
実行成功を示す情報を、

AIの種類に依存しない
共通形式で返せること。

### REQ-005 実行失敗結果の返却

AI実行に失敗した場合、

失敗したことと
確認可能なエラー内容を、

AIの種類に依存しない
共通形式で返せること。

### REQ-006 AI固有処理の分離

AIごとに異なる実行方法が、

Prompt生成機能や
後続のReview機能へ

直接影響しないこと。

## 任意要件

なし

# 9. エラー時

以下の場合は、

AIを実行せず、
または実行を中止し、

失敗したことと
確認可能なエラー内容を返す。

- Promptが文字列ではない
- Promptが空である
- Promptが空白のみである
- AIを利用できない
- AI実行中にエラーが発生した
- AIから有効な実行結果を取得できない

エラー発生時も、

AIの種類に依存しない
共通形式で結果を返す。

エラーを握りつぶしてはならない。

# 10. 対象外

Version 0.1では、

以下は実装しない。

- Promptの生成
- Promptのレビュー
- AI実行結果のレビュー
- Humanによる承認
- Git操作
- state.jsonの更新
- AI実行結果の保存
- AIごとの実装最適化

# 11. 完了条件

以下を満たした場合、

AI Runner Foundationは
完成とする。

- Promptを受け取りAIを実行できる
- AI実行結果を共通形式で返せる
- AI実行失敗を共通形式で返せる
- AI固有の違いが上位コンポーネントへ影響しない
- pytestが成功する

# 12. テスト観点

## 正常系

- Promptを受け取りAIを実行できる
- AI実行結果を共通形式で取得できる
- AI実行成功を共通形式で返せる

## 異常系

- Promptが空である
- Promptが空白のみである
- Promptが文字列ではない
- AIを利用できない
- AI実行中にエラーが発生する
- AIから有効な実行結果を取得できない

## 既存機能

- Prompt生成機能へ影響しない
- Review機能へ影響しない

# 13. 関連文書

Constitution

→ constitution/constitution.md

Principles

→ constitution/principles.md

Implementation Guidelines

→ constitution/implementation_guidelines.md

Architecture

→ projects/specflow/docs/architecture.md

# Closing

AI Runner Foundationは、

単にAIを呼び出すための
部品ではない。

SpecFlowにおいて、

AI実行を共通化し、

AIの種類に依存しない
開発基盤を提供する
中核コンポーネントである。

AI Runner Foundationは、

SpecFlowにおける

AI実行の唯一の入口とする。