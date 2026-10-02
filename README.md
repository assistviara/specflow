# SpecFlow

SpecFlowは、仕様書を唯一の正本として、人間とAIが協調しながらソフトウェア開発を進めるための開発オーケストレーターです。

AIに直接コードを書かせることだけを目的とせず、以下の開発工程を標準化し、履歴として残します。

```text
Constitution
    ↓
Principles
    ↓
Specification
    ↓
Implementation Plan
    ↓
Decision
    ↓
Implementation
    ↓
Test
    ↓
Review
```

---

## 1. SpecFlowの目的

これまでの開発では、次のような作業を人間が手動で行っていました。

```text
ChatGPTで仕様作成
    ↓
Codex向けPrompt作成
    ↓
Codexで実装
    ↓
実行ログをChatGPTへ渡す
    ↓
レビュー
    ↓
修正Prompt作成
    ↓
Codexで修正
```

SpecFlowは、この受け渡しを自動化しながら、人間の判断と承認を開発工程に残すことを目的としています。

---

## 2. 基本思想

SpecFlowでは、AIを主体とは考えません。

AIは、提案、分析、実装、レビューを担当する優秀な部下です。

目的、価値、仕様、最終判断、責任は人間が持ちます。

主な考え方は次のとおりです。

- 人間が主体である
- 仕様書を唯一の正本とする
- 実装前にPlanを作る
- 人間の承認後に実装する
- 必要最小限の変更に限定する
- テストとレビューを完了条件とする
- Prompt、Plan、Decision、Reviewも開発資産として残す
- 知識だけでなく、実践を通して学ぶ

詳細は以下を参照してください。

```text
constitution/constitution.md
constitution/principles.md
constitution/implementation_guidelines.md
```

---

## 3. 現在の開発状況

現在は、Application Layer実装開始前の設計ベースラインが`main`へMerge済みの状態です。

現在の設計ベースライン：

```text
d7df90d Merge pull request #32 from assistviara/developer
```

完了済み：

- Application Layer Specification v0.2.0-draftの設計作業
- Application Layer Implementation Plan v0.1.0-draftの作成
- Implementation PlanのPhase 1からPhase 7までの定義
- Phase 7のPurpose、Scope、Implementation Targets 1-8、Tests 1-8、Completion Conditions 1-8の最終横断監査
- Technical Retry、Correction、Human Approval、Evidence、Review、Final Approval、Merge、completedの責務境界の横断確認
- Pull Request #32による`main`へのMerge

次の主要作業は、承認済みImplementation Planに基づくApplication Layer Phase 1 Implementationの開始です。

次セッションでは、実装開始前に`SESSION_CONTEXT.md`を確認してください。

---

## 4. ディレクトリ構成

```text
specflow_starter/
├─ constitution/
│  ├─ constitution.md
│  ├─ principles.md
│  └─ implementation_guidelines.md
│
├─ core/
│  ├─ __init__.py
│  ├─ document_loader.py
│  ├─ template_engine.py
│  ├─ codex_runner.py
│  ├─ review_runner.py
│  ├─ state_manager.py
│  └─ その他の将来用モジュール
│
├─ document_templates/
│  └─ specification_template.md
│
├─ prompt_templates/
│  ├─ README.md
│  ├─ plan_prompt_template.md
│  ├─ implement_prompt_template.md
│  ├─ review_prompt_template.md
│  └─ repair_prompt_template.md
│
├─ prompts/
│  ├─ plan_prompt.md
│  ├─ implement_prompt.md
│  ├─ review_prompt.md
│  └─ repair_prompt.md
│
├─ projects/
│  └─ specflow/
│     ├─ project.json
│     ├─ state.json
│     ├─ docs/
│     │  ├─ specification.md
│     │  ├─ implementation_plan.md
│     │  ├─ decisions.md
│     │  ├─ architecture.md
│     │  └─ spec_change_proposal.md
│     ├─ logs/
│     └─ reviews/
│
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  └─ project_detail.html
│
├─ tests/
│  └─ test_document_loader.py
│
├─ app.py
├─ requirements.txt
└─ README.md
```

---

## 5. アーキテクチャ

SpecFlow Engineは、次の責務に分離します。

```text
Document Loader
    ↓
Template Engine
    ↓
Codex Runner
    ↓
Review Runner
```

### Document Loader

正式文書を読み込みます。

### Template Engine

テンプレートへ文書とプロジェクト情報を差し込み、完成版Promptを生成します。

### Codex Runner

Codex CLIを実行し、生成結果を取得します。

### Review Runner

Specification、Plan、実装、テスト結果を比較します。

詳細は以下を参照してください。

```text
projects/specflow/docs/architecture.md
```

---

## 6. セットアップ

### 仮想環境の作成

```powershell
python -m venv .venv
```

### PowerShellでの有効化

```powershell
.venv\Scripts\Activate.ps1
```

### 依存ライブラリのインストール

```powershell
python -m pip install -r requirements.txt
```

### Flaskの起動

Phase 8A T8内①では、Human Control DBのpathを明示します。通常起動は既存DBを開くだけで、DB作成・移行は行いません。
初回だけ、未使用のpathを指定して独立した初期化操作を実行してください。親フォルダは事前に用意します。

```powershell
python -m flask --app app init-human-control-db --path C:\path\to\human-control.sqlite3
$env:SPECFLOW_HUMAN_CONTROL_DB = 'C:\path\to\human-control.sqlite3'
python app.py
```

`C:\path\to\...`はHumanが指定する実際の保存先へ置き換えます。既存ファイルは初期化で上書きしません。
DB未指定・未存在・旧schema・別application DB・open失敗時はHTTP 503で対象pathと安全な理由を表示し、操作を停止します。
失敗した初期化の対象ファイルも自動削除しません。既存DBを消して起動し直す処理やmigrationはありません。

テストや依存接続では`create_app(db_path)`で明示できます。`app.extensions['human_control']`がruntimeです。
`require_repository()`でDB利用可否を確認し、`target(project_id, workflow_id)`でUUID・所属を確認します。
後続serviceでも所属・正式Artifactを再検証してください。

form token基盤は`runtime.forms.issue/consume`を利用します。tokenはform本文で渡し、URLへ含めません。
操作・UUID・session・server側で再取得したrevisionへ紐付け、一回のPOSTで消費します。
再表示した同一対象のformは以前のtokenを無効にします。`revision`にPOSTされたhashをそのまま渡してはいけません。
tokenの検証成功はApprovalや実行許可ではなく、既存serviceの検証が引き続き必要です。
実業務POSTへの接続は後続T8単位で行います。

`runtime.outputs`は実`WorkflowObservation`のコピーをWorkflow UUID別に保持するprocess内メモリです。
`put/get/clear`を提供し、不明Workflowは`None`を返します。DB保存・Output合成・再起動後の復元はしません。
正式な実行用Adapterの接続は後続単位です。T8内①は8画面完成やWorkflow実行を提供しません。
既存legacy画面は残っており、SQLite Projectの管理画面としては扱いません。
直接起動ではdebug/reloaderと並行request処理を無効にしています。

```powershell
python app.py
```

ブラウザで以下を開きます。

```text
http://127.0.0.1:5000
```

---

## 7. テスト

テストは、現在有効になっているPython環境から実行します。

```powershell
python -m pytest -q
```

`pytest -q`だけで実行すると、別のPython環境に入っているpytestが起動する場合があります。

---

## 8. 現在の開発対象

次の開発対象は`Application Layer Phase 1`です。

実装前に、以下を確認します。

- Constitution / Project Rules
- 最新のSession Context
- Application Layer Specification
- Application Layer Implementation Plan
- Gitの現在状態

Phase 1では、承認済みImplementation PlanのPurpose、Scope、Implementation Targets、Tests、Completion Conditionsに従って、TDDで実装を開始します。

---

## 9. 今後の予定

- Application Layer Phase 1 Implementation
- Application Layer Phase 2 Implementation
- Application Layer Phase 3 Implementation
- Application Layer Phase 4 Implementation
- Application Layer Phase 5 Implementation
- Application Layer Phase 6 Implementation
- Application Layer Phase 7 Integration & MVP Completion

---

## 10. 開発記録

開発時の判断や気付きは、Notionの「SpecFlow開発記録」に保存しています。

開発記録には、何を実装したかだけでなく、なぜその設計にしたのかを残します。

---

## Closing

SpecFlowは、コードを自動生成することだけを目的としません。

人間の経験、判断基準、仕様、承認、レビューを形式知として残し、AIが再現可能な形で実行できる開発環境を目指します。

> コードを書く前に、判断基準を形式知化する。  
> 再現性はコードではなく、ルールから生まれる。
