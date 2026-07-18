# Decisions

## DEC-004 Plan Prompt Generator実装Planの承認

- 決定日：2026-07-18
- 決定者：たけしゃん
- 対象Plan：`implementation_plan_plan_prompt_generator.md` Version 0.1.0
- 対象機能：Plan Prompt Generator
- 判定：APPROVED

### 承認内容

以下の範囲に限定して実装を承認する。

- `core/plan_prompt_generator.py`の新規作成
- `tests/test_plan_prompt_generator.py`の新規作成
- `PlanPromptGenerator`を実装する
- `generate()`を公開APIとする
- `DocumentLoaderProtocol`を定義する
- `PromptBuilderProtocol`を定義する
- 既存Document Loader関数を利用する`DocumentLoaderAdapter`を実装する
- `DocumentLoaderAdapter`を`core/plan_prompt_generator.py`内へ配置する
- Document LoaderをDI可能にする
- Prompt BuilderをDI可能にする
- 依存未指定時は標準Document Loader Adapterおよび標準Prompt Builderを利用する
- Constitution、Principles、Specification、Decisions、Project Metadataを取得する
- Plan Prompt Templateを取得する
- 必須5項目を含むContextを構築する
- Project Metadataを整形済みJSON文字列へ変換する
- Prompt BuilderへTemplateとContextを渡す
- Prompt Builderが返した`PromptResult`を加工せず返す
- Document Loader、Prompt Builder、`KeyError`、JSON変換時の例外をそのまま呼出元へ伝播する
- 正常系、DI、Context構築、Adapter委譲、異常系のテストを実装する
- 既存テストを含む回帰テストを実行する

### 今回承認しないもの

- `core/document_loader.py`の変更
- `core/template_engine.py`の変更
- `core/prompt_builder.py`の変更
- `app.py`の変更
- 既存テストの変更
- Plan Prompt Templateの変更
- Codex CLIの実行
- AI APIの実行
- Promptのファイル保存
- Implementation Planの自動保存
- Reviewの実行
- `state.json`の更新
- ログ保存
- Git操作
- GitHub操作
- 非同期処理
- キャッシュ
- 複数プロジェクトの一括処理
- 外部ライブラリの追加
- 不足文書の推測生成
- 独自Template展開

### 承認理由

Plan Prompt Generatorの責務が、

- 正式文書の取得
- Contextの構築
- Prompt Builderへの委譲
- PromptResultの返却

に限定されている。

また、

- Protocolによる最小契約
- Adapterによる既存関数との接続
- DIによる単体テスト
- 例外の非隠蔽
- 既存Engineを変更しない方針

が明確である。

変更範囲が新規2ファイルに限定されており、
既存機能へ与える影響も小さい。

そのため、
Implementation Plan Version 0.1.0に基づく実装へ進むことを承認する。

---

# Closing

本Decisionにより、

Plan Prompt Generator Version 0.1.0の実装を承認する。

実装は、
承認された範囲内に限定し、

完了後は、

```text
python -m pytest -q