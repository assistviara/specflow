# SpecFlow Template Language

Version: 1.0

---

## 1. 目的

SpecFlow Template Language（STL）は、

Templateへ正式文書やプロジェクト情報を差し込み、
Promptなどの成果物を生成するための
SpecFlow専用テンプレート言語である。

STLは汎用プログラミング言語ではない。

テンプレート内の変数を、
指定された値へ安全に置換することだけを目的とする。

---

## 2. 基本文法

変数は、二重波括弧で表現する。

```text
{{VARIABLE_NAME}}
```

例：

```text
{{PROJECT_NAME}}
{{CONSTITUTION}}
{{PRINCIPLES}}
{{SPECIFICATION}}
```

---

## 3. 変数名

変数名は、次の規則に従う。

- 英大文字を使用する
- 単語の区切りにはアンダースコアを使用する
- 数字は先頭に使用しない
- 空白を含めない
- 日本語を使用しない

正しい例：

```text
{{PROJECT_NAME}}
{{PROJECT_VERSION}}
{{TARGET_PATH}}
```

使用しない例：

```text
{{project_name}}
{{ProjectName}}
{{PROJECT NAME}}
{{プロジェクト名}}
```

---

## 4. Context

Templateへ差し込む値は、
Contextと呼ばれる辞書形式のデータとして渡す。

Pythonでの例：

```python
context = {
    "PROJECT_NAME": "SpecFlow",
    "PROJECT_VERSION": "0.1.0",
    "CONSTITUTION": "Constitutionの本文",
}
```

Template Engineは、
Template内の変数名とContextのキーを照合する。

---

## 5. 置換

Template内の変数と同名の値がContextに存在する場合、
その値へ置換する。

Template：

```text
プロジェクト名：{{PROJECT_NAME}}
```

Context：

```python
{
    "PROJECT_NAME": "SpecFlow"
}
```

生成結果：

```text
プロジェクト名：SpecFlow
```

---

## 6. 未定義変数

Template内の変数がContextに存在しない場合、
空文字へ置換してはならない。

未定義変数はTemplate内にそのまま残す。

例：

```text
{{UNKNOWN_VARIABLE}}
```

さらに、Template Engineは
未定義変数の一覧を警告情報として返す。

推測による値の補完は禁止する。

---

## 7. 未使用Context

Contextに値が存在していても、
Template内で使用されていない場合はエラーとしない。

ただし、未使用Contextを確認できるよう、
一覧として返すことができる設計とする。

---

## 8. Templateの不変性

Template Engineは、
元のTemplateファイルを変更してはならない。

Templateは正本である。

生成結果は、別のファイルへ保存する。

例：

```text
plan_prompt_template.md
        ↓
Template Engine
        ↓
plan_prompt.md
```

---

## 9. 値の扱い

Contextの値は、原則として文字列へ変換して使用する。

次の値を扱う場合は、
文字列へ明示的に変換する。

- 数値
- 真偽値
- Path
- 日付
- バージョン番号

`None`は自動的に空文字へ変換しない。

`None`が渡された場合は、
値が未設定であることを警告する。

---

## 10. Version 1.0の対象範囲

Version 1.0で対応するのは、
単純な変数置換だけである。

```text
{{VARIABLE_NAME}}
```

---

## 11. Version 1.0の対象外

以下はVersion 1.0では実装しない。

- 条件分岐
- 繰り返し
- 関数呼び出し
- 数式
- フィルター
- Template同士の継承
- Templateの埋め込み
- 外部コードの実行
- Python式の評価

例として、次のような文法はまだ使用しない。

```text
{{IF CONDITION}}
{{FOR ITEM IN ITEMS}}
{{VALUE | upper}}
```

---

## 12. 安全性

STLは、Template内の文字列置換だけを行う。

次の処理は禁止する。

- `eval()`の使用
- `exec()`の使用
- TemplateからのPythonコード実行
- Templateからのコマンド実行
- Templateからのファイル操作
- 未定義変数の推測補完

---

## 13. エラーと警告

### エラー

次の場合は処理を停止する。

- Templateが空
- Contextが辞書形式ではない
- 変数名の形式が不正
- Templateを読み込めない

### 警告

次の場合は生成結果とともに警告を返す。

- 未定義変数がある
- Contextの値が`None`
- 使用されなかったContextがある

---

## 14. Template Engineの出力

Template Engineは、少なくとも次を返す。

- 生成された文字列
- 未定義変数一覧
- 未使用Context一覧
- 警告一覧

概念例：

```python
{
    "content": "生成されたPrompt",
    "undefined_variables": [],
    "unused_context": [],
    "warnings": [],
}
```

実際のPython上のデータ構造は、
Implementation Planで決定する。

---

## 15. 想定する変数

Plan Promptでは、主に次を使用する。

```text
{{CONSTITUTION}}
{{PRINCIPLES}}
{{SPECIFICATION}}
{{DECISIONS}}
{{PROJECT_NAME}}
{{TARGET_PATH}}
{{PROJECT_DESCRIPTION}}
{{PROJECT_VERSION}}
```

今後、必要に応じて追加する。

---

## 16. 設計原則

STLは、次の原則に従う。

- 単純であること
- 人間が読めること
- 推測しないこと
- 元のTemplateを変更しないこと
- AI製品に依存しないこと
- 同じ入力から同じ結果を生成できること

---

## Closing

SpecFlow Template Languageは、

高度なプログラムを書くための言語ではない。

人間が定めたルールと正式文書を、
AIへ再現可能な形で渡すための共通言語である。