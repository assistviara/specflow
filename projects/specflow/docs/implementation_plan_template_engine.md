# Implementation Plan

Version: 0.1.0

---

## 1. Plan概要

### 対象プロジェクト

SpecFlow

### 対象機能

Template Engine

### 対象Specification

`specification_template_engine.md` Version 0.1.0

### 関連文書

- `docs/template_language.md` Version 1.0
- `constitution/implementation_guidelines.md` Version 1.0
- `projects/specflow/docs/architecture.md` Version 0.1.0

### Planの状態

ready

### 今回の実装範囲

Template文字列とContextを受け取り、STL Version 1.0に従って変数を置換し、`RenderResult`として結果を返す処理を実装する。

今回は、次の機能に限定する。

- Template内の変数抽出
- Contextとの照合
- 変数の置換
- 未定義変数の検出
- 未使用Contextの検出
- `None`値の検出
- 警告情報の生成
- `RenderResult`の返却

---

## 2. 今回実装しないもの

- Templateファイルの読み込み
- 生成結果のファイル保存
- Codex CLIの実行
- Prompt固有の処理
- `state.json`の更新
- Git操作
- 条件分岐
- 繰り返し
- Template継承
- フィルター
- Python式の評価
- `eval()`または`exec()`の利用

---

## 3. Public API

Version 0.1では、次のクラスを公開する。

### `TemplateEngine`

利用例：

```python
engine = TemplateEngine()

result = engine.render(
    template=template_text,
    context=context,
)
```

### 公開メソッド

```python
render(template: str, context: dict[str, object]) -> RenderResult
```

`render()`以外の処理は、原則として内部実装とする。

---

## 4. RenderResult

Template展開結果を表すデータクラスとして、`RenderResult`を実装する。

保持する項目：

```python
content: str
undefined_variables: list[str]
unused_context: list[str]
warnings: list[str]
```

### 各項目の意味

- `content`
  - 変数置換後の文字列

- `undefined_variables`
  - Templateには存在するが、Contextに存在しない変数名

- `unused_context`
  - Contextには存在するが、Templateでは使用されなかったキー

- `warnings`
  - 未定義変数、`None`値、未使用Contextなどの警告文

---

## 5. エラー設計

独自例外として、次を実装する。

```text
TemplateRenderError
```

次の場合は処理を停止する。

### TEMPLATE_EMPTY

Templateが空文字または空白のみである。

### INVALID_CONTEXT

Contextが辞書形式ではない。

### INVALID_VARIABLE_NAME

Template内にSTL Version 1.0の命名規則に反する変数がある。

エラーには最低限、次を含める。

- エラー種別
- 原因
- 利用者が確認すべき内容

---

## 6. 変数の抽出

STL Version 1.0の変数記法を対象とする。

```text
{{VARIABLE_NAME}}
```

有効な変数名：

```text
[A-Z][A-Z0-9_]*
```

例：

```text
{{PROJECT_NAME}}
{{PROJECT_VERSION}}
{{REQ_001}}
```

無効な例：

```text
{{project_name}}
{{PROJECT NAME}}
{{1_PROJECT}}
{{プロジェクト名}}
```

変数抽出には正規表現を使用する。

---

## 7. 置換ルール

### Contextに値が存在する場合

値を文字列へ変換して置換する。

例：

```python
{
    "PROJECT_NAME": "SpecFlow",
    "PROJECT_VERSION": "0.1.0",
}
```

### Contextに値が存在しない場合

変数は元の形のまま残す。

```text
{{UNKNOWN_VARIABLE}}
```

空文字には置換しない。

変数名を`undefined_variables`へ追加する。

### Contextの値が`None`の場合

変数は元の形のまま残す。

警告を追加する。

推測による値の補完は行わない。

---

## 8. 内部処理

`TemplateEngine`は、内部で次の処理を行う。

### `_validate_template(template)`

- Templateが文字列であることを確認する
- 空でないことを確認する
- 変数名の形式を確認する

### `_validate_context(context)`

- Contextが辞書であることを確認する

### `_extract_variables(template)`

- Template内の変数名を抽出する
- 重複を除いて返す

### `_render_content(template, context, variables)`

- Contextに存在する変数を置換する
- 未定義変数と`None`値は元の記法を残す

### `_build_result(...)`

- `RenderResult`を生成する

内部メソッド名は、実装時に意味が変わらない範囲で調整できる。

---

## 9. 変更予定ファイル

### 新規作成または実装

- `core/template_engine.py`
  - `TemplateEngine`
  - `RenderResult`
  - `TemplateRenderError`

- `tests/test_template_engine.py`
  - 正常系テスト
  - 異常系テスト
  - 警告情報のテスト

### 変更

- なし

### 削除

- なし

---

## 10. テスト計画

### 正常系

- 1つの変数を置換できる
- 複数の変数を置換できる
- 同じ変数が複数回出てもすべて置換される
- 数値を文字列へ変換して置換できる
- `Path`を文字列へ変換して置換できる
- 変数がないTemplateをそのまま返せる
- 元のTemplate文字列が変更されない

### 未定義変数

- Contextにない変数がTemplate内に残る
- `undefined_variables`へ変数名が入る
- 警告が生成される

### 未使用Context

- Templateで使用されなかったContextキーを検出できる
- `unused_context`へキーが入る
- 警告が生成される

### `None`値

- `None`を空文字へ変換しない
- 元の変数記法が残る
- 警告が生成される

### 異常系

- 空Templateで`TemplateRenderError`
- 空白だけのTemplateで`TemplateRenderError`
- 辞書以外のContextで`TemplateRenderError`
- 不正な変数名で`TemplateRenderError`

### 既存機能への影響確認

```powershell
python -m pytest -q
```

を実行し、既存のDocument Loaderテストを含めてすべて成功すること。

---

## 11. 変更禁止事項

- `document_loader.py`を変更しない
- Constitutionを変更しない
- Principlesを変更しない
- Implementation Guidelinesを変更しない
- Template Languageを変更しない
- Specificationを変更しない
- 外部ライブラリを追加しない
- ファイル読み書きを実装しない
- Codex CLIを呼び出さない

---

## 12. 完了条件

- `TemplateEngine`を生成できる
- `render()`でTemplateを展開できる
- 戻り値が`RenderResult`である
- 未定義変数を推測せず残せる
- 未使用Contextを検出できる
- `None`値を警告できる
- 不正入力を明確な例外として返せる
- Templateの元データを変更しない
- 外部ライブラリを追加していない
- 新規テストと既存テストがすべて成功する

---

## 13. リスク

| リスク | 影響 | 対応 |
|---|---|---|
| 正規表現が不正な変数を見逃す | STL規則に反するTemplateが処理される | 正常・異常パターンをテストする |
| 置換順によって結果が変わる | 再現性が失われる | 変数単位で決定的に置換する |
| `None`が空文字になる | 欠落に気付かない | 元の変数を残して警告する |
| Contextの値の型によって例外になる | 生成処理が停止する | 原則`str()`で明示変換する |

---

## 14. 人間確認事項

- `RenderResult`を`dataclass`として実装する方針を採用する
- 未定義変数と`None`値は、元の変数記法を残す
- 未使用Contextはエラーではなく警告とする

---

## 15. Plan結論

- Plan状態：ready
- 実装へ進めるか：人間承認後に進める
- 人間の承認が必要か：必要
- 実装対象：`core/template_engine.py`
- テスト対象：`tests/test_template_engine.py`