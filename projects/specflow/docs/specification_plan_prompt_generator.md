# Specification

Version: 0.1.0

Status: Draft

---

# 1. 基本情報

## プロジェクト

SpecFlow

## 機能名

Plan Prompt Generator

## バージョン

0.1.0

## 作成日

2026-07-14

## 作成者

たけしゃん

---

# 2. 概要

Plan Prompt Generatorは、

Implementation Planの作成に必要な正式文書を収集し、

Plan Prompt Templateへ渡すContextを構築して、

Prompt Builderを利用して
Plan作成用Promptを生成する
オーケストレーションEngineである。

Plan Prompt Generatorは、

- 正式文書を読み込む
- Contextを構築する
- Prompt Builderへ処理を委譲する
- PromptResultを返す

ことを担当する。

Plan Prompt Generator自身は、

- Templateを展開しない
- Codex CLIを実行しない
- Implementation Planを保存しない
- 正式文書を変更しない

責務を超える処理は行わない。

---

# 3. 責務（Responsibility）

Plan Prompt Generatorの責務は、

**Plan作成用Promptの生成工程を調整すること**

である。

## 実施すること

- Plan Prompt Templateを取得する
- Constitutionを取得する
- Principlesを取得する
- Specificationを取得する
- Decisionsを取得する
- Project Metadataを取得する
- 取得した情報からContextを構築する
- Prompt BuilderへTemplateとContextを渡す
- PromptResultを返す
- 標準依存または外部から注入された依存を利用する

## 実施しないこと

- Template展開を独自実装しない
- Codex CLIを実行しない
- Implementation Planを保存しない
- Reviewを実行しない
- Specificationを変更しない
- Constitutionを変更しない
- Principlesを変更しない
- Decisionsを変更しない
- `state.json`を更新しない
- Git操作を行わない
- ログを保存しない

これらは、
他のEngineまたは後続工程の責務とする。

---

# 4. 背景

SpecFlowでは、

Document Loaderによって
正式文書を安全に読み込める。

Template Engineによって
TemplateをContextで展開できる。

Prompt Builderによって
Template Engineの結果を
PromptResultとして扱える。

しかし現在は、

Plan作成に必要な正式文書を集め、

Plan Prompt Templateへ渡すContextを構築し、

Prompt Builderへ処理を委譲する
共通コンポーネントが存在しない。

そのため、

```text
Document Loader
        ↓
Context構築
        ↓
Prompt Builder
        ↓
Plan Prompt
```

という一連の処理を調整する
Plan Prompt Generatorを実装する。

---

# 5. 目的

Plan Prompt Generatorの目的は、

Implementation Planの作成に必要な情報を
一つのContextへまとめ、

Plan Promptを
再現可能な方法で生成することである。

これにより、

呼出元は

```text
base_dir
project_name
```

を指定するだけで、

必要な正式文書を反映した
Plan作成用Promptを取得できる。

また、

Document LoaderとPrompt Builderを
DI可能にすることで、

外部ファイルや実際のTemplate Engineに
過度に依存せず、

Plan Prompt Generator単体を
テストできるようにする。

---

# 6. 用語

| 用語 | 説明 |
|---|---|
| Plan Prompt | Implementation Planを作成するAIへ渡すPrompt |
| Plan Prompt Template | Plan Promptの雛形となるTemplate |
| Context | Templateへ差し込む正式文書およびメタデータ |
| Project Metadata | `project.json`に保存されたプロジェクト情報 |
| Document Loader | 正式文書を読み込むコンポーネント |
| Prompt Builder | TemplateとContextからPromptResultを生成するコンポーネント |
| Plan Prompt Generator | Plan Prompt生成工程を調整するコンポーネント |
| PromptResult | Prompt本文と検査情報を保持する結果オブジェクト |

---

# 7. 利用者

Plan Prompt Generatorを利用するものは、
次のとおりである。

## 現在

- SpecFlow Engine
- 開発者
- テストコード

## 将来

- Flask UI
- Codex Runner
- Workflow Engine
- CLI
- 他のAI Runner

---

# 8. 前提条件

## PRE-001

Document Loaderが利用可能であること。

---

## PRE-002

Prompt Builderが利用可能であること。

---

## PRE-003

Plan Prompt Templateが存在すること。

標準配置は次とする。

```text
prompt_templates/plan_prompt_template.md
```

---

## PRE-004

対象プロジェクトの正式文書が
規定された場所に存在すること。

対象には最低限、
次を含む。

- Constitution
- Principles
- Specification
- Decisions
- Project Metadata

---

## PRE-005

呼出元は、

```python
base_dir: Path
project_name: str
```

を指定すること。

---

## PRE-006

Template展開規則は
Template EngineおよびSTLに従うこと。

Plan Prompt Generatorは
独自の展開規則を持たない。

---

# 9. 機能要件

## REQ-001

Plan Prompt Generatorは、
Plan作成に必要な共通文書を取得できること。

対象は次とする。

- Constitution
- Principles

---

## REQ-002

Plan Prompt Generatorは、
対象プロジェクトの正式文書を取得できること。

対象は次とする。

- Specification
- Decisions
- Project Metadata

---

## REQ-003

Plan Prompt Generatorは、
Plan Prompt Templateを取得できること。

---

## REQ-004

取得した正式文書から
Contextを構築できること。

---

## REQ-005

Contextには最低限、
次の情報を含めること。

```text
CONSTITUTION
PRINCIPLES
SPECIFICATION
DECISIONS
PROJECT_METADATA
```

---

## REQ-006

Plan Prompt TemplateとContextを
Prompt Builderへ渡すこと。

---

## REQ-007

Template展開を
Prompt Builderへ委譲すること。

Plan Prompt Generatorは
変数置換を独自実装しない。

---

## REQ-008

戻り値は、

```python
PromptResult
```

とすること。

---

## REQ-009

Document Loaderを
外部からDIできること。

---

## REQ-010

Prompt Builderを
外部からDIできること。

---

## REQ-011

依存が指定されない場合は、
標準のDocument Loaderおよび
Prompt Builderを利用すること。

---

## REQ-012

公開メソッドは、

```python
generate(
    base_dir: Path,
    project_name: str,
) -> PromptResult
```

とすること。

---

## REQ-013

Document LoaderまたはPrompt Builderが
例外を発生させた場合、

Plan Prompt Generatorは
例外を握りつぶさず、
呼出元へ伝播すること。

---

## REQ-014

Plan Prompt Generatorは、
読み込んだ正式文書を変更しないこと。

---

## REQ-015

Plan Prompt Generatorは、
生成したPromptを
ファイルへ保存しないこと。

---

# 10. Public API

Plan Prompt Generatorは、
次のPublic APIを公開する。

## PlanPromptGenerator

通常利用

```python
generator = PlanPromptGenerator()

result = generator.generate(
    base_dir=base_dir,
    project_name=project_name,
)
```

---

Document Loaderおよび
Prompt Builderを差し替える場合

```python
generator = PlanPromptGenerator(
    document_loader=fake_document_loader,
    prompt_builder=fake_prompt_builder,
)
```

---

## 公開メソッド

```python
generate(
    base_dir: Path,
    project_name: str,
) -> PromptResult
```

---

# 11. Context

Plan Prompt Generatorは、

取得した正式文書から
Prompt Builderへ渡すContextを構築する。

Version 0.1では、
最低限次の項目を保持する。

```python
{
    "CONSTITUTION": "...",
    "PRINCIPLES": "...",
    "SPECIFICATION": "...",
    "DECISIONS": "...",
    "PROJECT_METADATA": "...",
}
```

Contextの構造は
Prompt Builderから独立して管理する。

Prompt Builderは、
Contextの意味を解釈しない。

---

# 12. 入力

|入力項目|型|必須|説明|
|---|---|:---:|---|
|base_dir|Path|〇|SpecFlowルートディレクトリ|
|project_name|str|〇|対象プロジェクト名|

---

# 13. 出力

|出力項目|型|説明|
|---|---|---|
|Prompt生成結果|PromptResult|Plan Prompt生成結果|

---

# 14. エラー設計

Plan Prompt Generatorは、

Document Loaderおよび
Prompt Builderが送出した例外を
握りつぶさない。

---

## ERROR-001

Document Loaderが例外を送出した場合、

そのまま呼出元へ伝播する。

---

## ERROR-002

Prompt Builderが例外を送出した場合、

そのまま呼出元へ伝播する。

---

## ERROR-003

Plan Prompt Generator自身は、

Version 0.1では
独自例外を生成しない。

---

## ERROR-004

推測による補完を行わない。

不足している正式文書がある場合も、
自動生成は行わない。

---

# 15. 依存関係

Plan Prompt Generatorの依存方向は
次とする。

```text
Document Loader
        │
        ▼
Plan Prompt Generator
        │
        ▼
Prompt Builder
        │
        ▼
Template Engine
```

---

## Dependency Rule

Plan Prompt Generatorは、

- Document Loader
- Prompt Builder

へ依存する。

Document Loaderおよび
Prompt Builderは、

Plan Prompt Generatorを知らない。

循環依存は禁止する。

---

# 16. 設計判断

## DESIGN-001

### PromptResultを返す

Plan Prompt Generatorの戻り値は

```python
PromptResult
```

とする。

#### 理由

Prompt Builderと
戻り値を統一し、

後続Engineが
共通インターフェースで利用できるようにする。

---

## DESIGN-002

### Context構築を担当する

Plan Prompt Generatorは、

正式文書から
Contextを構築する責務を持つ。

#### 理由

Document Loaderは
文書取得だけを担当し、

Prompt Builderは
Template展開だけを担当する。

責務を明確に分離するため。

---

## DESIGN-003

### Document LoaderをDI可能にする

Document Loaderは
外部から注入できるものとする。

#### 理由

Fake Loaderを利用し、

Plan Prompt Generator単体を
テストできるようにするため。

---

## DESIGN-004

### Prompt BuilderをDI可能にする

Prompt Builderは
外部から注入できるものとする。

#### 理由

Fake Prompt Builderを利用し、

Prompt生成処理から独立して
Generatorをテストできるようにするため。

---

## DESIGN-005

### generate()のみ公開する

Version 0.1では、

公開APIは

```python
generate()
```

のみとする。

#### 理由

呼出方法を単純化し、

将来の拡張でも
互換性を維持しやすくするため。

---

# 17. API利用例

通常利用

```python
generator = PlanPromptGenerator()

result = generator.generate(
    base_dir=base_dir,
    project_name="specflow",
)

if result.is_ready:
    print(result.content)
```

---

DI利用

```python
generator = PlanPromptGenerator(
    document_loader=FakeDocumentLoader(),
    prompt_builder=FakePromptBuilder(),
)

result = generator.generate(
    base_dir=base_dir,
    project_name="specflow",
)
```

## DESIGN-006

### Project MetadataはJSON文字列としてContextへ格納する

Document Loaderが返したProject Metadataは、

整形済みJSON文字列へ変換して
Contextへ格納する。

変換には次を使用する。

```python
json.dumps(
    project_metadata,
    ensure_ascii=False,
    indent=2,
)
```

#### 理由

Pythonの辞書表現ではなく、

- 日本語を保持できる
- AIが読みやすい
- 出力形式を再現できる

形式でPromptへ含めるため。

# 18. 依存コンポーネント

Plan Prompt Generatorは、
次のコンポーネントを利用する。

- Document Loader
- Prompt Builder

Document Loaderは、
Plan Promptの生成に必要な正式文書を取得する。

Prompt Builderは、
Plan Prompt TemplateとContextから
`PromptResult`を生成する。

Plan Prompt Generatorは、
これらのコンポーネントを外部から注入できること。

依存が指定されない場合は、
標準のDocument Loaderおよび
Prompt Builderを利用すること。

依存コンポーネントの具体的な接続方法は、
Implementation Planで定義する。

---

## Dependency Rule

依存方向は次とする。

```text
Document Loader
        │
        ▼
Plan Prompt Generator
        │
        ▼
Prompt Builder

# 19. 対象外（Out of Scope）

Version 0.1では、
次の機能は実装対象外とする。

- Codex CLIの実行
- AI APIの実行
- Implementation Planの自動保存
- Promptのファイル保存
- Prompt履歴管理
- Reviewの実行
- Review Promptの生成
- Repair Promptの生成
- Implementation Promptの生成
- `state.json`の更新
- ログ保存
- Git操作
- GitHub操作
- 非同期処理
- キャッシュ
- 複数プロジェクトの一括処理
- 独自Template展開
- 不足文書の推測生成

---

# 20. 完了条件（Definition of Done）

Plan Prompt Generatorは、
次の条件を満たした場合に完成と判定する。

## 実装

- `PlanPromptGenerator`クラスが存在する
- `generate()`メソッドを公開している
- Document Loader Adapterが存在する
- Document LoaderをDIできる
- Prompt BuilderをDIできる
- 未指定時は標準依存を利用する

---

## 文書取得

- Constitutionを取得できる
- Principlesを取得できる
- Specificationを取得できる
- Decisionsを取得できる
- Project Metadataを取得できる
- Plan Prompt Templateを取得できる

---

## Context

- 必要なContextを構築できる
- `CONSTITUTION`を含む
- `PRINCIPLES`を含む
- `SPECIFICATION`を含む
- `DECISIONS`を含む
- `PROJECT_METADATA`を含む
- Project Metadataが整形済みJSON文字列である

---

## Prompt生成

- TemplateとContextをPrompt Builderへ渡す
- `PromptResult`を返す
- Template展開を独自実装していない
- Promptをファイルへ保存していない
- AIを実行していない

---

## 品質

- Document Loaderの例外が伝播する
- Prompt Builderの例外が伝播する
- Fake Loaderを利用したテストが成功する
- Fake Prompt Builderを利用したテストが成功する
- 新規テストがすべて成功する
- 既存テストがすべて成功する
- 循環依存が存在しない
- 仕様外変更が行われていない

---

# 21. テスト観点

## 正常系

- PlanPromptGeneratorを生成できる
- 標準依存を利用できる
- 必要な正式文書を取得できる
- Plan Prompt Templateを取得できる
- Contextを正しく構築できる
- Prompt Builderが呼び出される
- `PromptResult`が返される

---

## Context

- Constitutionが正しく格納される
- Principlesが正しく格納される
- Specificationが正しく格納される
- Decisionsが正しく格納される
- Project MetadataがJSON文字列へ変換される
- 日本語がエスケープされず保持される
- JSONがインデント付きで整形される

---

## DI

- Fake Document Loaderを注入できる
- Fake Prompt Builderを注入できる
- 注入したLoaderが呼ばれる
- 注入したPrompt Builderが呼ばれる
- TemplateとContextが正しく渡される

---

## 異常系

- Document Loaderの例外が呼出元へ伝播する
- Prompt Builderの例外が呼出元へ伝播する
- 不足文書を推測補完しない
- 例外を握りつぶさない

---

## 責務確認

- Template展開を独自実装していない
- Codex CLIを実行していない
- Promptを保存していない
- Implementation Planを保存していない
- `state.json`を更新していない
- Git操作を行っていない

---

## 回帰テスト

次のテストがすべて成功する。

- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator

実行コマンドは次とする。

```powershell
python -m pytest -q
```

---

# 22. 関連文書

## Constitution

- `constitution/constitution.md`
- `constitution/principles.md`
- `constitution/implementation_guidelines.md`

---

## Architecture

- `projects/specflow/docs/architecture.md`

---

## Specification

- `projects/specflow/docs/specification.md`
- `projects/specflow/docs/specification_template_engine.md`
- `projects/specflow/docs/specification_prompt_builder.md`

---

## Template

- `docs/template_language.md`
- `prompt_templates/plan_prompt_template.md`

---

## Decision

- `projects/specflow/docs/decision_document_loader.md`
- `projects/specflow/docs/decision_template_engine.md`
- `projects/specflow/docs/decision_prompt_builder.md`

---

## Review

- `reviews/review_document_loader_001.md`
- `reviews/review_template_engine_001.md`
- `reviews/review_prompt_builder_001.md`

---

# 23. 今後の拡張予定

将来Versionでは、
次の機能を検討する。

- Plan Promptのファイル保存
- Prompt生成履歴の管理
- CLIからの実行
- Flask UIからの実行
- Codex Runnerとの接続
- 他のAI Runnerとの接続
- 複数Specificationへの対応
- Context構築ルールの共通化
- Prompt種別ごとの共通Generator基盤
- Workflow Engineとの統合

これらは、
Version 0.1の実装範囲には含めない。

---

# 24. 変更履歴

| Version | 内容 |
|---|---|
| 0.1.0 | Plan Prompt Generator初版仕様 |

---

# Closing

Plan Prompt Generatorは、

正式文書を読み込み、
Contextを構築し、
Prompt Builderへ処理を委譲する
オーケストレーションEngineである。

Document Loaderは文書取得を担当し、

Prompt Builderは
Template展開とPromptResult生成を担当する。

Plan Prompt Generatorは、

それらのEngineを接続し、

Implementation Plan作成用Promptを
再現可能な方法で生成する責務を持つ。

Plan Prompt Generator自身は、

AIを実行せず、
Promptを保存せず、
正式文書を変更しない。

SpecFlowは、

小さなEngineを
明確な責務と一方向の依存関係で接続することで、

AIによるソフトウェア開発を
安全にオーケストレーションする。

