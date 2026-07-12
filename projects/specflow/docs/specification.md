# Specification

Version: 0.1.0

---

# 1. 基本情報

## プロジェクト名

SpecFlow

## 機能名

Codex Plan生成

## 仕様作成日

2026-07-12

## 仕様作成者

たけしゃん

---

# 2. 背景

現在は、

ChatGPTで仕様書を作成し、

Codexへプロンプトをコピーし、

Planを生成している。

その後、

生成されたPlanを

ChatGPTへ渡してレビューを行っている。

この工程は品質は高いが、

人間によるコピー＆ペーストが多く、

作業効率が低下している。

---

# 3. 目的

SpecFlowから

Codex Plan生成を実行し、

人間のコピー作業をなくす。

Codexには

Constitution

Principles

Specification

Prompt

をまとめて渡し、

implementation_plan.mdを生成できるようにする。

---

# 4. 利用者

・開発者

・仕様作成者

---

# 5. 現在の状態

現在は

ChatGPT

↓

Codex

↓

ChatGPT

という手作業で

プロンプトを受け渡している。

---

# 6. 実装後の状態

利用者は

Generate Plan

ボタンを押すだけで

Codex Planを生成できる。

Planは

implementation_plan.md

へ保存される。

実行ログは

latest.txt

へ保存される。

---

# 7. 前提条件

### PRE-001 Codex CLIが利用できる

実行環境にCodex CLIがインストールされ、
コマンドラインから実行できること。

### PRE-002 Python実行環境が利用できる

SpecFlowを起動するPython仮想環境が作成され、
必要な依存ライブラリがインストールされていること。

### PRE-003 project.jsonが存在する

対象プロジェクトのルート管理フォルダに
`project.json`
が存在し、正常なJSONとして読み込めること。

### PRE-004 target_pathが有効である

`project.json`に記載された
`target_path`
が存在するディレクトリを指していること。

### PRE-005 Constitutionが存在する

共通ファイルである
`constitution/constitution.md`
が存在し、空ではないこと。

### PRE-006 Principlesが存在する

共通ファイルである
`constitution/principles.md`
が存在し、空ではないこと。

### PRE-007 Specificationが存在する

対象プロジェクトの
`docs/specification.md`
が存在し、空ではないこと。

### PRE-008 Plan Promptが存在する

共通プロンプトである
`prompts/plan_prompt.md`
が存在し、空ではないこと。

# 8. 機能要件

## 必須要件

### REQ-001 Constitutionの読み込み

SpecFlowは、共通ファイルである
`constitution/constitution.md`
を読み込めること。

### REQ-002 Principlesの読み込み

SpecFlowは、共通ファイルである
`constitution/principles.md`
を読み込めること。

### REQ-003 Specificationの読み込み

SpecFlowは、対象プロジェクトの
`docs/specification.md`
を読み込めること。

### REQ-004 Plan Promptの読み込み

SpecFlowは、
`prompts/plan_prompt.md`
を読み込めること。

### REQ-005 Codex CLIの実行

SpecFlowは、対象プロジェクトのパスを作業ディレクトリとして、
Codex CLIによるPlan生成を実行できること。

### REQ-006 Implementation Planの保存

Codexが生成したPlanを、
対象プロジェクトの
`docs/implementation_plan.md`
へ保存できること。

### REQ-007 実行ログの保存

Codex CLIの標準出力、標準エラー、実行結果を、
対象プロジェクトの
`logs/latest.txt`
へ保存できること。

### REQ-008 ソースコードを変更しない

Plan生成工程では、
Codexは対象プロジェクトのソースコードを変更してはならない。

## 任意要件

なし

# 9. 操作の流れ

```text
Generate Plan ボタン

        ↓

Constitution読込

        ↓

Principles読込

        ↓

Specification読込

        ↓

Prompt読込

        ↓

Codex実行

        ↓

implementation_plan.md保存

        ↓

latest.txt保存
```

---

# 10. 入力

|入力|内容|
|------|------|
|Constitution|constitution.md|
|Principles|principles.md|
|Specification|specification.md|
|Prompt|plan_prompt.md|

---

# 11. 出力

|出力|保存先|
|------|------|
|Plan|implementation_plan.md|
|ログ|latest.txt|

---

# 12. エラー時

以下の場合、

処理を停止する。

- Constitutionが読めない
- Principlesが読めない
- Specificationが空
- Promptが存在しない
- Codex実行失敗

停止理由を画面へ表示する。

---

# 13. 人間の承認が必要な事項

なし

今回はPlan生成のみ行う。

---

# 14. 変更禁止事項

- Constitution
- Principles
- specification.md
- 既存コード

CodexはPlanのみ生成する。

コードを変更してはならない。

---

# 15. 対象外

今回は実装しない。

- Code生成
- Review
- Repair
- Git操作
- 自動コミット

---

# 16. 影響範囲

UI

Generate Planボタン追加

---

# 17. 完了条件

- Generate Planボタンが表示される
- Codexが起動する
- implementation_plan.mdが生成される
- latest.txtへログ保存される
- コードは変更されない

---

# 18. テスト観点

## 正常系

Generate PlanでPlan生成できる

## 異常系

Promptが無い

Codexが存在しない

Specificationが空

## 既存機能

既存画面が正常表示される

---

# 19. 未決定事項

Codex CLIのオプション設計

---

# 20. 補足

これは

SpecFlow最初のSpecificationである。

SpecFlow自身を

SpecFlowで育てる

第一歩となる。