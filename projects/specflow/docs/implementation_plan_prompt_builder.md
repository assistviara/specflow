# Implementation Plan

Version: 0.1.0

Status: Ready

---

# 1. 基本情報

## 対象プロジェクト

SpecFlow

## 対象機能

Prompt Builder

## 対象Specification

`specification_prompt_builder.md` Version 0.1.0

## 実装対象

- `core/prompt_builder.py`
- `tests/test_prompt_builder.py`

---

# 2. 実装目的

Template Engineの展開結果を受け取り、

後続処理が安全に利用できる
`PromptResult`へ変換する。

Prompt Builderは、

- 文書を読み込まない
- Templateを独自展開しない
- Promptを保存しない
- AIを実行しない

という責務境界を維持する。

---

# 3. 対応要件

| 要件ID | 要件 | 対応方針 |
|---|---|---|
| REQ-001 | PromptResultを返す | dataclassとして実装する |
| REQ-002 | Prompt本文を保持する | RenderResult.contentを引き継ぐ |
| REQ-003 | 未定義変数を保持する | RenderResultから引き継ぐ |
| REQ-004 | 未使用Contextを保持する | RenderResultから引き継ぐ |
| REQ-005 | Warningを保持する | RenderResultから引き継ぐ |
| REQ-006 | is_readyを提供する | propertyとして計算する |
| REQ-007 | Template EngineをDIできる | コンストラクタで受け取る |
| REQ-008 | 標準Engineを利用する | 未指定時にTemplateEngineを生成する |
| REQ-009 | 本文とContextを受け取る | build()の引数として定義する |
| REQ-010 | 展開処理を委譲する | TemplateEngine.render()を呼び出す |

---

# 4. 公開クラス

## PromptResult

`dataclass`として実装する。

```python
@dataclass(frozen=True)
class PromptResult:
    content: str
    undefined_variables: list[str]
    unused_context: list[str]
    warnings: list[str]
```

次のpropertyを提供する。

```python
@property
def is_ready(self) -> bool:
    return not self.undefined_variables
```

`is_ready`は保存せず、
保持している情報から計算する。

---

## PromptBuilder

Template Engineを利用して
PromptResultを生成する。

```python
class PromptBuilder:
    def __init__(
        self,
        template_engine: TemplateEngine | None = None,
    ) -> None:
        ...
```

Template Engineが指定されない場合は、
標準の`TemplateEngine`を使用する。

---

# 5. 公開メソッド

```python
def build(
    self,
    template: str,
    context: dict[str, object],
) -> PromptResult:
    ...
```

処理の流れは次とする。

```text
TemplateとContextを受け取る
        ↓
TemplateEngine.render()へ渡す
        ↓
RenderResultを受け取る
        ↓
PromptResultへ変換する
        ↓
呼出元へ返す
```

---

# 6. 依存性注入

通常利用では、標準Engineを使用する。

```python
builder = PromptBuilder()
```

テストや将来の差し替えでは、
外部からEngineを渡せるようにする。

```python
builder = PromptBuilder(
    template_engine=fake_engine,
)
```

Prompt Builderは、
渡されたEngineが持つ`render()`を利用する。

---

# 7. エラー設計

Template Engineが発生させた

```python
TemplateRenderError
```

は、そのまま呼出元へ伝播させる。

Prompt Builderは、

- 例外を握りつぶさない
- 空文字で代替しない
- 推測による補完を行わない
- Version 0.1では独自例外を追加しない

---

# 8. 変更予定ファイル

## 実装

- `core/prompt_builder.py`
  - `PromptResult`
  - `PromptBuilder`
  - `build()`
  - Template EngineのDI

## テスト

- `tests/test_prompt_builder.py`
  - 標準Engine利用
  - PromptResult変換
  - is_ready判定
  - DI
  - 例外伝播
  - 回帰テスト

## 変更しないファイル

- `core/document_loader.py`
- `core/template_engine.py`
- `app.py`
- 既存Specification
- Constitution
- Principles
- Implementation Guidelines

---

# 9. テスト計画

## 正常系

- PromptBuilderを生成できる
- 標準Template Engineを利用できる
- build()がPromptResultを返す
- contentが正しく引き継がれる
- undefined_variablesが引き継がれる
- unused_contextが引き継がれる
- warningsが引き継がれる

## is_ready

- 未定義変数がなければTrue
- 未定義変数があればFalse

## DI

- Fake Template Engineを注入できる
- Fake Engineのrender()が呼ばれる
- Fake Engineの結果をPromptResultへ変換できる

## 異常系

- TemplateRenderErrorが呼出元へ伝播する
- Prompt Builderが例外を握りつぶさない

## 回帰テスト

```powershell
python -m pytest -q
```

を実行し、次がすべて成功すること。

- Document Loader
- Template Engine
- Prompt Builder

---

# 10. 対象外

今回、次は実装しない。

- 文書読み込み
- Templateファイル読み込み
- Promptファイル保存
- Codex CLI実行
- Review生成
- ログ保存
- State更新
- Git操作
- キャッシュ
- 非同期処理

---

# 11. 完了条件

- [ ] `core/prompt_builder.py`が実装されている
- [ ] `PromptResult`がdataclassである
- [ ] `PromptBuilder`がTemplate Engineを利用している
- [ ] `build()`がPromptResultを返す
- [ ] `is_ready`が正しく判定される
- [ ] 標準Template Engineを利用できる
- [ ] Template EngineをDIできる
- [ ] 例外が正しく伝播する
- [ ] 新規テストが成功する
- [ ] 既存テストがすべて成功する
- [ ] 仕様外の変更が行われていない

---

# 12. リスク

| リスク | 影響 | 対応 |
|---|---|---|
| RenderResultとPromptResultの転記漏れ | 警告情報が失われる | 全フィールドをテストする |
| is_readyの判定誤り | 不完全なPromptがAIへ渡る | True・Falseの両方をテストする |
| DIしたEngineを使わない | テストや差し替えができない | Fake Engineで呼出しを検証する |
| Prompt Builderが展開処理を持つ | 責務が重複する | build()内でrender()以外の展開を行わない |

---

# 13. 人間確認事項

次の設計を承認対象とする。

- PromptResultをdataclassとする
- is_readyは未定義変数の有無から計算する
- Template EngineをDI可能にする
- 未指定時は標準Template Engineを使用する
- Template Engineの例外をそのまま伝播する

---

# 14. Plan結論

- Plan状態：Ready
- 実装へ進めるか：人間承認後に進める
- 人間の承認：必要
- 新規実装：`core/prompt_builder.py`
- 新規テスト：`tests/test_prompt_builder.py`