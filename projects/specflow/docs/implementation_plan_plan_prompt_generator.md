# Implementation Plan

Version: 0.1.0

Status: Draft

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