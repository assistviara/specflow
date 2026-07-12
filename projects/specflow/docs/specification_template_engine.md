# Specification

Version: 0.1.0

---

# 1. 基本情報

## プロジェクト名

SpecFlow

## 機能名

Template Engine

## 仕様作成日

2026-07-12

## 仕様作成者

たけしゃん

---

# 2. 責務（Responsibility）

Template Engineは、

TemplateとContextから
成果物（Artifact）を生成するコンポーネントである。

Template Engineは、
生成処理以外の責務を持たない。

## 実施すること

- Templateの検証
- Contextとの照合
- Templateの展開
- 警告情報の生成
- RenderResultの生成

## 実施しないこと

- Documentの読込
- ファイル保存
- Codex CLIの実行
- state.jsonの更新
- Git操作
- Templateの変更

---

# 3. 背景

現在は、

Promptを手作業で組み立てている。

SpecFlowでは、

Templateを利用して
再現可能なPrompt生成を行う。

---

# 4. 目的

TemplateとContextから、

同一入力に対して

常に同じ成果物を生成できること。

---

# 5. 利用者

- 開発者
- SpecFlow Engine

---

# 6. 入力

Template

Context(Dictionary)

詳細は

SpecFlow Template Language Version1.0

を参照。

---

# 7. 出力

RenderResult

RenderResultは、

生成結果と

Warning情報を保持する。

詳細なデータ構造は

Implementation Planで決定する。

---

# 8. Public API

Version0.1では、

TemplateEngineクラスを提供する。

公開メソッド

```python
render(template, context)
```

戻り値

```text
RenderResult
```

公開API以外は

内部実装とする。

---

# 9. エラー

以下の場合は

処理を停止する。

- Templateが空
- Contextが辞書ではない
- Template読込失敗
- Validation失敗

エラー内容は

利用者が理解できる形式で返す。

---

# 10. 関連文書

Template文法

→ docs/template_language.md

設計方針

→ constitution/implementation_guidelines.md

システム構造

→ architecture.md

---

# 11. 対象外

Version0.1では

次は実装しない。

- 条件分岐
- 繰り返し
- Template継承
- フィルター
- 外部Template読込
- Pythonコード実行

---

# 12. 完了条件

- Templateを展開できる
- Contextを適用できる
- Warningを返せる
- Templateを変更しない
- pytestが成功する

---

# 13. テスト観点

## 正常系

- 変数が置換される
- Warningなし

## 異常系

- 未定義変数
- Context不正
- Template空

## 既存機能

Document Loaderへ影響しない。

---

# Closing

Template Engineは

Promptを生成するためだけの部品ではない。

SpecFlowにおける

Template展開の共通Engineである。