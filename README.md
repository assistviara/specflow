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

Version 0.1.0では、正式文書を安全に読み込む基盤処理まで実装しています。

実装済み：

- MarkdownファイルのUTF-8読み込み
- JSONファイルの読み込み
- ファイル不存在、空ファイル、不正JSONの検知
- 独自例外`DocumentLoadError`
- Constitutionの読み込み
- Principlesの読み込み
- Specificationの読み込み
- Decisionsの読み込み
- Project Metadataの読み込み
- Plan Prompt Templateの読み込み
- pytestによるテスト

テスト結果：

```text
8 passed
```

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

次の開発対象は`Template Engine`です。

目的は、以下をテンプレートへ差し込み、完成版のPlan Promptを生成することです。

- Constitution
- Principles
- Specification
- Decisions
- Project Metadata
- Plan Prompt Template

この段階では、まだCodex CLIは実行しません。

---

## 9. 今後の予定

- Template Engineの実装
- 完成版Plan Promptの生成
- Codex CLIの実行
- Implementation Planの自動保存
- 実行ログの保存
- Plan承認UI
- 実装実行
- Review自動生成
- Repair Prompt生成
- Git差分確認
- 複数プロジェクト管理

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