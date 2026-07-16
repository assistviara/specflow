# Implementation Plan

Version: 0.1.0

Status: Ready

---

# 1. 基本情報

## 対象プロジェクト

SpecFlow

## 対象機能

Plan Prompt Generator

## 対象Specification

`projects/specflow/docs/specification_plan_prompt_generator.md`

Version: 0.1.0

## 実装対象

- `core/plan_prompt_generator.py`
- `tests/test_plan_prompt_generator.py`

---

# 2. 実装目的

Plan Prompt Generatorを実装し、

- Constitution
- Principles
- Specification
- Decisions
- Project Metadata
- Plan Prompt Template

を取得してContextへまとめ、

Prompt Builderを利用して
Plan作成用Promptを生成できるようにする。

Plan Prompt Generatorは、
複数の既存Engineを接続する
オーケストレーションEngineとして実装する。

---

# 3. 実装範囲

今回の実装範囲は次とする。

## 実装するもの

- `PlanPromptGenerator`
- `generate()`
- Document Loaderへの接続
- Prompt Builderへの接続
- Context構築
- Project MetadataのJSON文字列化
- Document LoaderのDI
- Prompt BuilderのDI
- 標準依存の利用
- 例外伝播
- 単体テスト

## 実装しないもの

- Codex CLIの実行
- AI APIの実行
- Promptの保存
- Implementation Planの保存
- Reviewの実行
- `state.json`の更新
- ログ保存
- Git操作
- GitHub操作
- 非同期処理
- キャッシュ
- 複数プロジェクトの一括処理

---

# 4. 対応要件

| 要件ID | 要件 | 対応方針 |
|---|---|---|
| REQ-001 | 共通文書を取得する | Document Loaderを利用する |
| REQ-002 | プロジェクト文書を取得する | Document Loaderを利用する |
| REQ-003 | Plan Prompt Templateを取得する | Document Loaderを利用する |
| REQ-004 | Contextを構築する | Generator内で辞書を作成する |
| REQ-005 | 必須Contextを含める | 5項目を明示的に格納する |
| REQ-006 | Prompt Builderへ渡す | `build()`を呼び出す |
| REQ-007 | 展開処理を委譲する | 変数置換を実装しない |
| REQ-008 | PromptResultを返す | Prompt Builderの戻り値を返す |
| REQ-009 | Document LoaderをDIする | コンストラクタで受け取る |
| REQ-010 | Prompt BuilderをDIする | コンストラクタで受け取る |
| REQ-011 | 標準依存を利用する | 未指定時に標準実装を生成する |
| REQ-012 | generate()を公開する | Public APIとして実装する |
| REQ-013 | 例外を伝播する | try/exceptで握りつぶさない |
| REQ-014 | 正式文書を変更しない | 読み取り専用で扱う |
| REQ-015 | Promptを保存しない | 戻り値として返すだけにする |

---

# 5. 実装方針

Plan Prompt Generatorは、
次の順序で処理を行う。

```text
generate()
      ↓
共通文書を取得
      ↓
プロジェクト文書を取得
      ↓
Plan Prompt Templateを取得
      ↓
Project MetadataをJSON文字列へ変換
      ↓
Contextを構築
      ↓
Prompt Builderへ渡す
      ↓
PromptResultを返す
```

処理は一本道とし、
Version 0.1では分岐処理を設けない。

---

# 6. Document Loaderの接続方針

既存の`core/document_loader.py`は、
関数として次を公開している。

```python
load_common_documents(...)
load_project_documents(...)
load_plan_prompt_template(...)
```

Plan Prompt Generatorでは、
これらを利用できる依存オブジェクトを
コンストラクタから受け取る。

標準利用時は、
既存関数を呼び出す小さなAdapterを使用する。

テスト時は、
同じインターフェースを持つ
Fake Document Loaderへ差し替える。

---

# 7. Prompt Builderの接続方針

Prompt Builderは、
コンストラクタから注入できるものとする。

標準利用時は、
既存の`PromptBuilder`を利用する。

テスト時は、
Fake Prompt Builderへ差し替える。

Plan Prompt Generatorは、
Prompt Builderへ次を渡す。

```python
template
context
```

戻り値として受け取った
`PromptResult`をそのまま呼出元へ返す。

---

# 8. Context構築方針

Contextは、
次のキーを持つ辞書として構築する。

```python
{
    "CONSTITUTION": constitution,
    "PRINCIPLES": principles,
    "SPECIFICATION": specification,
    "DECISIONS": decisions,
    "PROJECT_METADATA": project_metadata_json,
}
```

Project Metadataは、
次の形式でJSON文字列へ変換する。

```python
json.dumps(
    project_metadata,
    ensure_ascii=False,
    indent=2,
)
```

Context構築時に、
正式文書の内容を変更しない。

---

# 9. 公開クラス

## PlanPromptGenerator

Plan Prompt生成工程を調整する
オーケストレーションコンポーネントとして実装する。

```python
class PlanPromptGenerator:
    def __init__(
        self,
        document_loader: DocumentLoaderProtocol | None = None,
        prompt_builder: PromptBuilderProtocol | None = None,
    ) -> None:
        ...
```

依存が指定されない場合は、

- 標準Document Loader Adapter
- 標準Prompt Builder

を使用する。

---

# 10. DocumentLoaderProtocol

Plan Prompt Generatorが必要とする
Document Loaderの最小インターフェースを定義する。

```python
class DocumentLoaderProtocol(Protocol):
    def load_common_documents(
        self,
        base_dir: Path,
    ) -> dict[str, str]:
        ...

    def load_project_documents(
        self,
        base_dir: Path,
        project_name: str,
    ) -> dict[str, object]:
        ...

    def load_plan_prompt_template(
        self,
        base_dir: Path,
    ) -> str:
        ...
```

Plan Prompt Generatorは、
具体的なDocument Loader実装ではなく、
このProtocolへ依存する。

---

## Protocolを利用する理由

既存の`core/document_loader.py`は、
関数群として実装されている。

一方、Plan Prompt Generatorでは、

- 標準実装
- Fake Document Loader
- 将来の別実装

を同じ方法で利用できる必要がある。

そのため、
Generatorが必要とする操作だけを
Protocolとして定義する。

---

# 11. DocumentLoaderAdapter

既存のDocument Loader関数を
`DocumentLoaderProtocol`へ適合させるため、
小さなAdapterを実装する。

```python
class DocumentLoaderAdapter:
    def load_common_documents(
        self,
        base_dir: Path,
    ) -> dict[str, str]:
        return load_common_documents(base_dir)

    def load_project_documents(
        self,
        base_dir: Path,
        project_name: str,
    ) -> dict[str, object]:
        return load_project_documents(
            base_dir,
            project_name,
        )

    def load_plan_prompt_template(
        self,
        base_dir: Path,
    ) -> str:
        return load_plan_prompt_template(base_dir)
```

Adapterは、
既存関数の呼出しだけを担当する。

次の処理は行わない。

- ファイルパスの再定義
- 読込処理の再実装
- 独自Validation
- 独自例外への変換
- 文書内容の変更
- Context構築

---

## Adapterの配置

Version 0.1では、
Plan Prompt Generator専用の小さなAdapterとして、

```text
core/plan_prompt_generator.py
```

内へ配置する。

将来、複数Generatorで再利用する必要が生じた場合は、
独立モジュールへの分離を検討する。

Version 0.1では、
先回りして別ファイルへ分割しない。

---

# 12. PromptBuilderProtocol

Plan Prompt Generatorが必要とする
Prompt Builderの最小インターフェースを定義する。

```python
class PromptBuilderProtocol(Protocol):
    def build(
        self,
        template: str,
        context: dict[str, object],
    ) -> PromptResult:
        ...
```

Plan Prompt Generatorは、
具体的な`PromptBuilder`クラスではなく、
`build()`を提供するオブジェクトを利用する。

---

## Protocolを定義する理由

テスト時に、
Fake Prompt Builderを注入できるようにするため。

また、Plan Prompt Generatorが
Prompt Builderの内部実装へ
依存しないようにするため。

---

# 13. 公開メソッド

## generate()

```python
def generate(
    self,
    base_dir: Path,
    project_name: str,
) -> PromptResult:
    ...
```

処理順序は次とする。

```text
1. 共通文書を取得する
        ↓
2. プロジェクト文書を取得する
        ↓
3. Plan Prompt Templateを取得する
        ↓
4. Project MetadataをJSON文字列へ変換する
        ↓
5. Contextを構築する
        ↓
6. Prompt Builderのbuild()を呼び出す
        ↓
7. PromptResultを返す
```

---

# 14. 取得データ

## 共通文書

`load_common_documents()`の戻り値から、
次を取得する。

```python
constitution = common_documents["constitution"]
principles = common_documents["principles"]
```

---

## プロジェクト文書

`load_project_documents()`の戻り値から、
次を取得する。

```python
specification = project_documents["specification"]
decisions = project_documents["decisions"]
project_metadata = project_documents["project_metadata"]
```

キー名称は、
既存Document Loaderの実際の戻り値と一致させる。

Implementation前に、
既存実装および既存テストで
キー名称を確認する。

---

## Template

`load_plan_prompt_template()`から、
Plan Prompt Template本文を取得する。

```python
template = self._document_loader.load_plan_prompt_template(
    base_dir
)
```

---

# 15. Project Metadataの変換

Project Metadataは、
辞書のままPrompt Builderへ渡さず、
整形済みJSON文字列へ変換する。

```python
project_metadata_json = json.dumps(
    project_metadata,
    ensure_ascii=False,
    indent=2,
)
```

変換後の値を、

```python
"PROJECT_METADATA"
```

としてContextへ格納する。

---

# 16. Context構築

Contextは、
`generate()`内で次のように構築する。

```python
context: dict[str, object] = {
    "CONSTITUTION": constitution,
    "PRINCIPLES": principles,
    "SPECIFICATION": specification,
    "DECISIONS": decisions,
    "PROJECT_METADATA": project_metadata_json,
}
```

Contextへ格納するキーは、
Plan Prompt Templateの変数名と一致させる。

Plan Prompt Generatorは、
Templateに存在しない独自キーを
推測して追加しない。

---

# 17. Prompt Builderへの委譲

構築したTemplateとContextを、
Prompt Builderへ渡す。

```python
return self._prompt_builder.build(
    template=template,
    context=context,
)
```

Plan Prompt Generatorは、
Prompt Builderから返された
`PromptResult`を加工せずに返す。

次の処理は行わない。

- Prompt本文の書換え
- Warningの削除
- 未定義変数の補完
- `is_ready`の独自判定
- Promptの保存

---

# 18. エラー設計

Plan Prompt Generatorは、
依存コンポーネントが発生させた例外を
握りつぶさない。

## Document Loaderの例外

次の処理で発生した例外は、
そのまま呼出元へ伝播する。

- 共通文書取得
- プロジェクト文書取得
- Template取得

---

## Prompt Builderの例外

`build()`が発生させた例外は、
そのまま呼出元へ伝播する。

---

## KeyError

Document Loaderの戻り値に
必要なキーが存在しない場合、

Version 0.1では
推測補完を行わない。

既存の`KeyError`を
そのまま伝播させる。

独自例外への変換は、
将来Versionで必要性を検討する。

---

## JSON変換エラー

Project Metadataが
JSONへ変換できない値を含む場合、

`json.dumps()`が発生させた例外を
そのまま伝播する。

---

# 19. 変更予定ファイル

## 新規作成

### `core/plan_prompt_generator.py`

次を実装する。

- `DocumentLoaderProtocol`
- `DocumentLoaderAdapter`
- `PromptBuilderProtocol`
- `PlanPromptGenerator`
- `generate()`
- Context構築
- Project MetadataのJSON文字列化

---

### `tests/test_plan_prompt_generator.py`

次をテストする。

- 標準依存の利用
- Fake Document LoaderのDI
- Fake Prompt BuilderのDI
- 文書取得
- Template取得
- Context構築
- JSON文字列化
- PromptResultの返却
- 例外伝播

---

## 変更しないファイル

- `core/document_loader.py`
- `core/template_engine.py`
- `core/prompt_builder.py`
- `app.py`
- `state.json`
- 既存のテストファイル
- Constitution
- Principles
- Implementation Guidelines
- Plan Prompt Template

---

# 20. Protocol採用の設計判断

## DESIGN-PLAN-001

Plan Prompt Generatorは、
具体的な依存クラスではなく、

- `DocumentLoaderProtocol`
- `PromptBuilderProtocol`

へ依存する。

### 理由

- Fake実装へ差し替えられる
- Generator単体をテストできる
- 既存実装との結合を弱められる
- 将来の実装変更へ対応しやすい
- Prompt BuilderのDI設計と統一できる

---

## DESIGN-PLAN-002

既存Document Loader関数は、
AdapterでProtocolへ適合させる。

### 理由

既存の`core/document_loader.py`を変更せず、
Plan Prompt Generatorから
依存オブジェクトとして利用するため。

---

## DESIGN-PLAN-003

AdapterはVersion 0.1では、
`core/plan_prompt_generator.py`内へ配置する。

### 理由

現時点で利用者が
Plan Prompt Generatorだけであり、

独立モジュール化すると
責務以上にファイル構成が増えるため。

再利用が発生した時点で
分離を検討する。

# 21. 実装順序

実装は、次の順序で進める。

```text
1. Protocolを定義する
        ↓
2. DocumentLoaderAdapterを実装する
        ↓
3. PlanPromptGeneratorを実装する
        ↓
4. Fake依存を用意する
        ↓
5. 単体テストを書く
        ↓
6. 回帰テストを実行する
        ↓
7. Reviewを実施する
```

一度にすべてを実装せず、
各責務を小さく確認しながら進める。

---

# 22. テスト計画

## 正常系

- `PlanPromptGenerator`を生成できる
- 標準Document Loaderを利用できる
- 標準Prompt Builderを利用できる
- Constitutionを取得できる
- Principlesを取得できる
- Specificationを取得できる
- Decisionsを取得できる
- Project Metadataを取得できる
- Plan Prompt Templateを取得できる
- Contextを正しく構築できる
- Prompt Builderが呼び出される
- `PromptResult`が返される

---

## Context

- `CONSTITUTION`が正しく格納される
- `PRINCIPLES`が正しく格納される
- `SPECIFICATION`が正しく格納される
- `DECISIONS`が正しく格納される
- `PROJECT_METADATA`が正しく格納される
- Project MetadataがJSON文字列へ変換される
- 日本語がUnicodeエスケープされず保持される
- JSONがインデント付きで整形される
- Templateに不要なキーを推測して追加しない

---

## DI

- Fake Document Loaderを注入できる
- Fake Prompt Builderを注入できる
- 注入したDocument Loaderが呼び出される
- 注入したPrompt Builderが呼び出される
- `base_dir`が正しく渡される
- `project_name`が正しく渡される
- TemplateとContextが正しく渡される

---

## Adapter

- `load_common_documents()`が既存関数へ委譲される
- `load_project_documents()`が既存関数へ委譲される
- `load_plan_prompt_template()`が既存関数へ委譲される
- Adapterが独自の読込処理を持たない
- Adapterが例外を変換しない

---

## 異常系

- 共通文書取得時の例外が伝播する
- プロジェクト文書取得時の例外が伝播する
- Template取得時の例外が伝播する
- Prompt Builderの例外が伝播する
- 必須キー不足時の`KeyError`が伝播する
- JSON変換時の例外が伝播する
- 例外を握りつぶさない
- 不足情報を推測補完しない

---

## 責務確認

- Template展開を独自実装していない
- Prompt本文を書き換えていない
- Promptを保存していない
- Implementation Planを保存していない
- AIを実行していない
- `state.json`を更新していない
- ログを保存していない
- Git操作を行っていない

---

## 回帰テスト

次のテストをすべて実行する。

- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator

実行コマンド：

```powershell
python -m pytest -q
```

---

# 23. テストファイル構成

`tests/test_plan_prompt_generator.py`には、
最低限次のテストを用意する。

```text
test_can_create_plan_prompt_generator
test_generate_returns_prompt_result
test_generate_uses_standard_dependencies
test_generate_uses_injected_document_loader
test_generate_uses_injected_prompt_builder
test_generate_builds_expected_context
test_generate_converts_project_metadata_to_json
test_generate_preserves_japanese_in_project_metadata
test_generate_returns_prompt_builder_result_unchanged
test_generate_propagates_document_loader_error
test_generate_propagates_prompt_builder_error
test_generate_propagates_missing_key_error
test_adapter_delegates_to_document_loader_functions
```

実際のテスト名は、
実装時に既存命名規則へ合わせて調整してよい。

ただし、
テスト観点を削除してはならない。

---

# 24. リスク

| リスク | 影響 | 対応 |
|---|---|---|
| Document Loaderの戻り値キーが想定と異なる | Context構築時に失敗する | 実装前に既存コードとテストを確認する |
| Template変数名とContextキーが一致しない | 未定義変数が発生する | TemplateとContextの対応をテストする |
| Project MetadataのJSON変換で型エラーが発生する | Prompt生成に進めない | 例外伝播をテストする |
| Adapterへ責務が追加される | Document Loaderと責務が重複する | 委譲だけに限定する |
| Protocolが実装と不一致になる | DIした依存を利用できない | Fakeと標準実装の両方で確認する |
| PromptResultを加工して返す | Prompt Builderとの契約が崩れる | 同一オブジェクトを返すことをテストする |
| Generatorが巨大化する | 保守性が低下する | Context構築と接続責務だけに限定する |
| 既存ファイルを変更する | 回帰不具合が発生する | 新規2ファイルを中心に実装する |

---

# 25. 変更禁止事項

今回、次を変更してはならない。

- `core/document_loader.py`
- `core/template_engine.py`
- `core/prompt_builder.py`
- `app.py`
- `state.json`
- Constitution
- Principles
- Implementation Guidelines
- 既存Specification
- 既存Decision
- 既存Review
- `prompt_templates/plan_prompt_template.md`
- 既存テストの期待値

外部ライブラリも追加しない。

変更が必要になった場合は、
現在のPlanを中断し、
SpecificationまたはPlanの変更手続きを行う。

---

# 26. 完了条件

## 実装

- [ ] `core/plan_prompt_generator.py`が作成されている
- [ ] `DocumentLoaderProtocol`が定義されている
- [ ] `DocumentLoaderAdapter`が実装されている
- [ ] `PromptBuilderProtocol`が定義されている
- [ ] `PlanPromptGenerator`が実装されている
- [ ] `generate()`が公開されている

---

## DI

- [ ] Document LoaderをDIできる
- [ ] Prompt BuilderをDIできる
- [ ] 未指定時に標準依存を利用できる
- [ ] Fake依存で単体テストできる

---

## Context

- [ ] 必須5項目を含むContextを構築できる
- [ ] Project MetadataをJSON文字列へ変換できる
- [ ] 日本語を保持できる
- [ ] ContextキーがTemplate変数名と一致する

---

## 動作

- [ ] Plan Prompt Templateを取得できる
- [ ] Prompt Builderへ処理を委譲できる
- [ ] `PromptResult`を返せる
- [ ] PromptResultを加工していない
- [ ] 例外を握りつぶしていない

---

## 品質

- [ ] 新規テストがすべて成功する
- [ ] 既存テストがすべて成功する
- [ ] 循環依存が存在しない
- [ ] 仕様外の変更がない
- [ ] 外部ライブラリを追加していない
- [ ] Reviewを実施している

---

# 27. 実装後のレビュー観点

Reviewでは、最低限次を確認する。

- Specificationへ適合しているか
- Implementation Planへ適合しているか
- Decisionの承認範囲を守っているか
- Protocolが必要最小限か
- Adapterが委譲以外の処理を持っていないか
- Generatorの責務がContext構築と接続に限定されているか
- Prompt BuilderへTemplateとContextを正しく渡しているか
- PromptResultを加工していないか
- 例外を握りつぶしていないか
- テストが正常系・異常系・DIをカバーしているか
- 仕様外変更がないか

Review文書は、次の命名規則で保存する。

```text
reviews/review_plan_prompt_generator_001.md
```

---

# 28. 人間確認事項

次の設計を承認対象とする。

- `PlanPromptGenerator`を新規実装する
- Document LoaderとPrompt BuilderをDI可能にする
- Protocolを利用して依存の最小契約を定義する
- 既存Document Loader関数をAdapterで包む
- Adapterを`core/plan_prompt_generator.py`内へ配置する
- Context構築をGeneratorの責務とする
- Project Metadataを整形済みJSON文字列へ変換する
- Prompt Builderの戻り値を加工せず返す
- 依存コンポーネントの例外をそのまま伝播する
- 新規実装と新規テストの2ファイルに変更を限定する

---

# 29. Plan結論

- Plan状態：Ready
- 実装へ進めるか：人間承認後に進める
- 人間の承認：必要
- 新規実装：`core/plan_prompt_generator.py`
- 新規テスト：`tests/test_plan_prompt_generator.py`
- 既存ファイル変更：なし
- 外部ライブラリ追加：なし

---

# 30. 変更履歴

| Version | 内容 |
|---|---|
| 0.1.0 | Plan Prompt Generator初版Implementation Plan |

---

# Closing

本Implementation Planは、

Plan Prompt Generatorを
小さく、安全に実装するための
具体的な実装方針を定義する。

Plan Prompt Generatorは、

- Document Loader
- Prompt Builder

を接続し、

正式文書からContextを構築して、
Plan作成用Promptを生成する
オーケストレーションEngineである。

実装は、

- Protocol
- Adapter
- DI
- 単体テスト

を利用し、

既存Engineを変更せずに進める。

本Planは、
人間の承認後に実装へ移行する。