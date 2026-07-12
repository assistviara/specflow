# Decisions

## DEC-003 Prompt Builder実装Planの承認

- 決定日：2026-07-12
- 決定者：たけしゃん
- 対象Plan：`implementation_plan_prompt_builder.md` Version 0.1.0
- 対象機能：Prompt Builder
- 判定：APPROVED

### 承認内容

以下の範囲に限定して実装を承認する。

- `core/prompt_builder.py`の新規作成
- `tests/test_prompt_builder.py`の新規作成
- `PromptResult`をdataclassとして実装する
- `PromptBuilder`をクラスとして実装する
- `build()`を公開APIとする
- Template Engineの展開結果を`PromptResult`へ変換する
- `is_ready`を未定義変数の有無から計算する
- Template EngineをDI可能にする
- Template Engine未指定時は標準の`TemplateEngine`を使用する
- Template Engineの例外をそのまま呼出元へ伝播する

### 今回承認しないもの

- Document Loaderの変更
- Template Engineの変更
- ファイル読込
- Promptファイル保存
- Codex CLIの実行
- Review生成
- ログ保存
- `state.json`の更新
- Git操作
- キャッシュ
- 非同期処理
- 外部ライブラリの追加

### 承認理由

Prompt Builderの責務が、
Template Engineの結果を後続処理向けの
`PromptResult`へ変換することに限定されている。

公開API、依存方向、例外処理、テスト範囲が明確であり、
既存機能へ影響を与えずに小さく実装・検証できるため、
実装へ進むことを承認する。