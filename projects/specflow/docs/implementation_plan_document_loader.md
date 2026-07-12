# Implementation Plan

Version: 0.1.0

---

## 1. Plan概要

### 対象プロジェクト

SpecFlow

### 対象機能

Codex Plan生成機能のうち、正式文書を読み込む基盤処理

### Planの状態

ready

### 今回の実装範囲

今回は、次の文書をUTF-8で読み込む処理のみ実装する。

- Constitution
- Principles
- Specification
- Plan Prompt Template
- Project Metadata
- Decisions

Codex CLIの実行、UIボタン、Plan保存処理は今回実装しない。

---

## 2. 対応する要件

| 要件ID | 要件概要 | 今回の対応 |
|---|---|---|
| REQ-001 | Constitutionを読み込む | 対応する |
| REQ-002 | Principlesを読み込む | 対応する |
| REQ-003 | Specificationを読み込む | 対応する |
| REQ-004 | Plan Promptを読み込む | テンプレート読込まで対応する |
| REQ-005 | Codex CLIを実行する | 今回は対象外 |
| REQ-006 | Implementation Planを保存する | 今回は対象外 |
| REQ-007 | 実行ログを保存する | 今回は対象外 |
| REQ-008 | Plan工程でコードを変更しない | Codex未実行のため該当なし |

---

## 3. 変更予定ファイル

### 新規作成

- `core/document_loader.py`
  - MarkdownおよびJSONファイルを読み込む
  - ファイルの存在、空ファイル、文字コードを検証する
  - Codex、Flask、ログ保存には関与しない

- `tests/test_document_loader.py`
  - 正常系と異常系を確認する

### 変更

- なし

### 削除

- なし

---

## 4. document_loader.pyの責務

`document_loader.py`の責務は、指定された正式文書を安全に読み込み、文字列または辞書として返すことに限定する。

次の処理は行わない。

- Promptへの値の差し込み
- Codex CLIの実行
- Planの保存
- ログの保存
- Flask画面の操作
- state.jsonの更新

---

## 5. 実装予定の関数

### `load_text_file(path)`

指定されたテキストファイルをUTF-8で読み込む。

以下の場合は、分かりやすい例外を発生させる。

- ファイルが存在しない
- パスがファイルではない
- 内容が空
- UTF-8で読み込めない

### `load_json_file(path)`

指定されたJSONファイルをUTF-8で読み込み、辞書として返す。

以下の場合は、分かりやすい例外を発生させる。

- ファイルが存在しない
- 内容が空
- JSON形式が不正

### `load_common_documents(base_dir)`

以下を読み込む。

- `constitution/constitution.md`
- `constitution/principles.md`

### `load_project_documents(base_dir, project_name)`

以下を読み込む。

- `projects/<project_name>/docs/specification.md`
- `projects/<project_name>/docs/decisions.md`
- `projects/<project_name>/project.json`

### `load_plan_prompt_template(base_dir)`

以下を読み込む。

- `prompt_templates/plan_prompt_template.md`

---

## 6. エラー設計

独自例外として、次を用意する。

```text
DocumentLoadError
```

エラーには最低限、次を含める。

- 対象ファイル
- エラーの種類
- 利用者が確認すべき内容

不明なエラーを握りつぶさない。

---

## 7. テスト計画

### 正常系

- Constitutionを読み込める
- Principlesを読み込める
- Specificationを読み込める
- Decisionsを読み込める
- Project MetadataをJSONとして読み込める
- Plan Prompt Templateを読み込める
- 日本語が文字化けしない

### 異常系

- ファイルが存在しない
- ファイルが空
- JSON形式が不正
- ディレクトリをファイルとして指定する
- UTF-8以外で読み込めない

### 既存機能への影響確認

- Flaskのプロジェクト一覧が表示される
- Specificationの保存機能が動作する
- 既存ファイルを変更しない

---

## 8. 変更禁止事項

- Constitutionを変更しない
- Principlesを変更しない
- Specificationを変更しない
- Prompt Templateを変更しない
- project.jsonを変更しない
- state.jsonを変更しない
- 既存のFlask処理を変更しない
- 外部ライブラリを追加しない

---

## 9. 完了条件

- `core/document_loader.py`が作成されている
- 正式文書をUTF-8で読み込める
- JSONファイルを辞書として読み込める
- 読み込み失敗時に原因を判別できる
- テストがすべて成功する
- 既存ファイルが意図せず変更されていない

---

## 10. Plan結論

- Plan状態：ready
- 実装へ進めるか：進められる
- 人間の承認が必要か：必要
- 理由：SpecFlow最初のPython実装であり、責務の範囲を確認してから着手するため