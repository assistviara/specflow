Specification

Version: 0.1.0

Status: Ready

1. 基本情報
プロジェクト

SpecFlow

機能名

Prompt Builder

バージョン

0.1.0

作成日

2026-07-12

作成者

たけしゃん

2. 概要

Prompt Builderは、

Template本文とContextから、
完成したPromptを生成する
SpecFlow共通Engineである。

Prompt Builderは
Template Engineを利用して
Promptを生成し、

その結果を
後続Engineが利用しやすい形で
返却する。

Prompt Builder自身は

Promptを解釈しない
Templateを変更しない
Documentを読み込まない
Promptを保存しない

責務を超える処理は行わない。

3. 責務（Responsibility）

Prompt Builderの責務は

Prompt生成のみ

である。

実施すること
Template本文を受け取る
Contextを受け取る
Template Engineへ展開処理を委譲する
PromptResultを生成する
Prompt生成状態を保持する
実施しないこと
Document読込
Prompt保存
Prompt履歴管理
Codex実行
Review生成
state.json更新
Git操作
ログ保存
Template構文解析
Variable展開

これらは
他Engineの責務とする。

4. 背景

SpecFlowでは、

Document Loaderによって
正式文書を取得できる。

Template Engineによって
Template展開も実装されている。

しかし、

Prompt生成を担当する
共通Engineは存在しない。

Plan Prompt、

Review Prompt、

Repair Prompt、

Implementation Prompt

はいずれも

Template
      +
Context
      ↓
Prompt

という同じ構造を持つ。

そのため、

Prompt生成処理を
Prompt Builderへ集約する。

5. 目的

Prompt Builderは、

Template Engineの結果を

後続Engineが利用できる
共通形式へ変換することを目的とする。

生成結果には

Prompt本文
未定義変数
未使用Context
Warnings
実行可能状態

を保持する。

これにより、

Codex Runnerや
Review Runnerなどは、

Prompt生成方法を意識することなく、

PromptResultだけを扱えばよい。

6. 用語
用語	説明
Template	Promptの雛形となるMarkdown
Context	Templateへ差し込む値
Prompt	AIへ渡す完成した文章
PromptResult	Prompt生成結果を保持するオブジェクト
Template Engine	Template展開を担当するEngine
Prompt Builder	Prompt生成を担当するEngine
7. 利用者

Prompt Builderを利用するコンポーネント

現在

Plan Generator
Review Generator
Codex Runner

将来

Claude Runner
ChatGPT Runner
Gemini Runner
Workflow Engine
8. 前提条件
PRE-001

Template Engineが利用可能であること。

PRE-002

STL Version 1.0へ準拠すること。

PRE-003

Template本文は
呼出元が用意する。

Prompt Builderは
Templateを読み込まない。

PRE-004

Contextは

dict[str, object]

として渡される。

PRE-005

Document Loaderが
正式文書取得を担当する。

Prompt Builderは
Documentを取得しない。

# 9. 機能要件
REQ-001

PromptResultを返す。

戻り値は

PromptResult

とする。

REQ-002

Prompt本文を保持する。

content: str
REQ-003

未定義変数一覧を保持する。

undefined_variables: list[str]
REQ-004

未使用Context一覧を保持する。

unused_context: list[str]
REQ-005

Warning一覧を保持する。

warnings: list[str]
REQ-006

Prompt実行可能状態を判定できること。

is_ready: bool

Version 0.1では、

未定義変数が存在しなければ

True

とする。

REQ-007

Template EngineをDIできること。

REQ-008

Template Engineが指定されない場合は、
標準Template Engineを利用する。

REQ-009

build()は

Template本文
Context

のみ受け取る。

REQ-010

Template展開は
Template Engineへ委譲する。

Prompt Builderは

Template展開を独自実装しない。

# 10. Public API

Prompt Builderは、
次のPublic APIを公開する。

## PromptBuilder

通常利用

```python
builder = PromptBuilder()

result = builder.build(
    template=template_text,
    context=context,
)
```

---

Template Engineを差し替える場合

```python
builder = PromptBuilder(
    template_engine=custom_template_engine,
)
```

---

## 公開メソッド

```python
build(
    template: str,
    context: dict[str, object],
) -> PromptResult
```

---

# 11. PromptResult

Prompt Builderは、
文字列ではなく
PromptResultを返却する。

## 保持する情報

```python
content: str
undefined_variables: list[str]
unused_context: list[str]
warnings: list[str]
```

## Property

```python
is_ready: bool
```

## 判定条件

Version 0.1では、

```python
len(undefined_variables) == 0
```

であれば

```python
is_ready is True
```

とする。

## Purpose

Prompt本文だけではなく、

- Prompt本文
- 生成状態
- 警告情報

を一つのオブジェクトとして管理する。

---

# 12. 入力

|入力項目|型|必須|説明|
|---|---|:---:|---|
|template|str|〇|Template本文|
|context|dict[str, object]|〇|Templateへ差し込む値|

---

# 13. 出力

|出力項目|型|説明|
|---|---|---|
|Prompt生成結果|PromptResult|Prompt本文と生成状態を保持する|

---

# 14. エラー設計

Prompt Builderは、

Template Engineが発生させた例外を
握りつぶさない。

## ERROR-001

Template Engineが

```python
TemplateRenderError
```

を送出した場合、

Prompt Builderは
その例外をそのまま呼出元へ伝播する。

---

## ERROR-002

Prompt Builderは、
推測による補完を行わない。

---

## ERROR-003

Prompt Builderは、
空文字への置換を行わない。

---

## ERROR-004

Prompt Builder自身は、
独自例外を生成しない。

Version 0.1では、
Template Engineが発生させた例外を
そのまま利用する。

---

# 15. 依存関係

Prompt Builderの依存方向は
次とする。

```text
Document Loader
        │
        ▼
Template Engine
        │
        ▼
Prompt Builder
        │
        ▼
Codex Runner
```

## Dependency Rule

Prompt Builderは
Template Engineへ依存する。

Template Engineは
Prompt Builderを知らない。

循環依存は禁止する。

---

# 16. 設計判断

## DESIGN-001

### PromptResultを返す

Prompt Builderの戻り値は

```python
str
```

ではなく、

```python
PromptResult
```

とする。

#### 理由

Prompt本文だけでは、

- 実行可能か
- 警告があるか
- 未定義変数があるか

を判定できないため。

---

## DESIGN-002

### Template EngineをDI可能にする

Prompt Builderは、
Template Engineを
外部から受け取れる設計とする。

#### 標準利用

```python
builder = PromptBuilder()
```

#### 差し替え

```python
builder = PromptBuilder(
    template_engine=fake_engine,
)
```

#### 理由

DIを採用することで、

- テスト容易性
- Engine差し替え
- 将来の拡張性

を実現する。

---

## DESIGN-003

### build()は文字列を受け取る

Prompt Builderは、
Templateファイルを受け取らない。

入力は

- Template本文
- Context

のみとする。

#### 理由

Document読込は
Document Loaderの責務である。

Prompt Builderは
Prompt生成だけを担当する。

---

## DESIGN-004

### Template展開はTemplate Engineへ委譲する

Prompt Builderは、
Variable展開や構文解析を
独自実装しない。

Template展開は
Template Engineへ委譲する。

#### 理由

責務を明確に分離し、

Engine同士の独立性を維持するため。

---

# 17. API利用例

## 通常利用

```python
builder = PromptBuilder()

result = builder.build(
    template=template,
    context=context,
)

if result.is_ready:
    print(result.content)
```

---

## DI利用

```python
builder = PromptBuilder(
    template_engine=FakeTemplateEngine(),
)

result = builder.build(
    template=template,
    context=context,
)
```

---

# 18. 対象外（Out of Scope）

Version 0.1では、
次の機能は実装対象外とする。

- Document Loaderの実装変更
- Template Engineの実装変更
- Promptファイルの保存
- Prompt履歴管理
- Promptキャッシュ
- Codex CLIの実行
- Claude Runnerとの連携
- ChatGPT Runnerとの連携
- Gemini Runnerとの連携
- Workflow Engineとの連携
- Git操作
- state.json更新
- ログ保存
- 非同期処理
- マルチスレッド処理

これらは
将来のVersionで実装する。

---

# 19. 完了条件（Definition of Done）

Prompt Builderは、
次の条件を満たした場合に
完成と判定する。

## 実装

- PromptBuilderクラスが存在する
- PromptResultクラスが存在する
- build()メソッドを公開している
- Template Engineへ処理を委譲している
- Prompt Builder自身はTemplate展開を実装していない

---

## 動作

- Promptを生成できる
- PromptResultを返す
- Prompt本文を保持できる
- 未定義変数を保持できる
- 未使用Contextを保持できる
- Warningを保持できる
- is_readyが正しく判定される

---

## DI

- Template EngineをDIできる
- 標準Template Engineを利用できる
- Fake Template Engineへ差し替えられる

---

## 品質

- pytestがすべて成功する
- 既存テストが失敗しない
- 責務分離が維持されている
- 循環依存が存在しない

---

# 20. テスト観点

## 正常系

- Promptを生成できる
- PromptResultを返す
- contentが正しい
- is_readyがTrueになる
- Warningが空である
- 未定義変数が空である

---

## Warning系

- 未使用Contextを保持できる
- Warningを保持できる

---

## Error系

- Template Engineの例外を呼出元へ伝播する
- Prompt Builderが例外を握りつぶさない

---

## DI

- Fake Template Engineを利用できる
- Fake Template Engineのrender()が呼ばれる
- Fake Engineの結果をPromptResultへ変換できる

---

## 回帰テスト

次のテストがすべて成功する。

- Document Loader
- Template Engine
- Prompt Builder

---

# 21. 関連文書

## Constitution

- constitution.md
- principles.md
- implementation_guidelines.md

---

## Architecture

- architecture.md

---

## Specification

- specification_template_engine.md

---

## Template

- template_language.md

---

## Review

- review_template_engine_001.md

---

## Decision

- decision_template_engine.md

---

# 22. 今後の拡張予定

Prompt Builderは、
Version 1.x以降で
次のPrompt生成をサポートする予定である。

- Plan Prompt
- Review Prompt
- Repair Prompt
- Implementation Prompt

さらに、
Prompt Builderを共通Engineとして利用し、

- Codex Runner
- Claude Runner
- ChatGPT Runner
- Gemini Runner

から同一インターフェースで利用できるようにする。

---

# 23. 変更履歴

| Version | 内容 |
|---------|------|
| 0.1.0 | Prompt Builder初版仕様 |

---

# Closing

Prompt Builderは、

Promptを生成するEngineであり、

Promptを解釈するEngineではない。

Prompt Builderは、
Template Engineを利用して
Promptを生成し、

その生成結果を
PromptResultとして
後続Engineへ受け渡す責務のみを持つ。

SpecFlowでは、

各Engineが
一つの責務だけを持ち、

一方向の依存関係を維持することで、

変更に強く、
レビューしやすく、
継続的に成長できる
開発基盤を目指す。

Prompt Builderは、
SpecFlow全体のPrompt生成を担う
共通Engineとして
長期的に利用されることを前提とする。