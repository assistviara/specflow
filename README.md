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

T8内②では一覧の「新しいプロジェクト・既存開発物の登録」から`/control/projects/new`を開けます。
未完成の基本方針でも作成でき、既存開発物の登録には参照と明示確認が必要です。
作成後は`/control/projects/<Project UUID>`で基本方針を項目別に保存・確認できます。
入力だけでは確認済みになりません。古い画面・再送は拒否されるため、現在の画面を再表示してください。
作成後に一部の保存・確認が失敗した場合は、作成済みProjectへ戻り、現在値と確認状態を確認して続けます。
基本方針の開始条件が成立しても、この画面ではWorkflowを開始しません。
Constitution変更時の進行中Workflowに対する判断材料は画面へ返しますが、判断の永続管理や状態遷移は行いません。

T8内③では`/`がHuman Controlのホームです。SQLiteから現在進行中のProjectと、明示的に寝かせた日時順の最大3件を表示します。
`/control/projects/sleeping`で全Sleeping Projectを開き、明示確認して「進行中にする」を選べます。
Project画面にも「進行中にする」「寝かせる」を追加しています。閲覧だけではFocusは変わりません。
Active切替は既存serviceに委譲し、以前のActiveをSleepingにしますが、新しい明示Sleep日時は記録しません。
tokenは対象・操作・現在Activeの表示内容に結び付け、POST時に再読込します。古い画面や再送は拒否されます。
判断待ち・再開情報・過去Intent・Reminderの内容は未接続と表示し、未実装画面へのリンクは作りません。
従来のフォルダ一覧は`/legacy`へ移し、既存の`/projects/<project_name>`は保持しています。HomeのProject authorityには使いません。

T8内④ではProject画面の一覧からWorkflowを明示的に開けます。0件でも新規開始せず、1件でも複数件でも選択を永続化しません。
`/control/projects/<Project UUID>/workflows/<Workflow UUID>`は既存T5 Resumeの正式情報再検証とT6のHuman Intent表示に接続します。
正式Approval保存先を`SPECFLOW_APPROVALS_DIR`、Review / Final検証に必要なEvidence保存先を`SPECFLOW_EVIDENCE_DIR`で明示してください。
既存のJSON repositoryを読み取りに使用し、保存先の探索・作成・Approval生成は行いません。未設定や情報不足はSTOP / Human Handoffです。
埋め込み起動では`create_app(db_path, approvals_dir=..., evidence_dir=...)`で同じ依存先を渡せます。
同一processの実Outputは既存runtime holderから受け取り、再起動後はT5が対応する正式checkpointだけを検証します。Outputを保存・推測復元しません。
「前回ここまで」はT5の表示時の結果です。「次に考えていたこと」はWorkflowごとの最新Intentで、空欄は変更なし、削除は別の明示操作です。
「今日はここまで」は同期操作がUIへ戻った後のT6 End Workです。POST後に`/end-work`へ移動し、正式情報を再確認します。GETだけではEnd Workを実行しません。
End WorkはWorkflow取消・Focus変更ではありません。Activeの場合だけ「進行中のままにする」「寝かせる」を別途明示操作できます。
Sleepingの暗黙Activateはありません。次工程の実行接続は後続対応であり、この画面から処理を自動開始しません。

T8内⑤では`/control/reminders`で全ProjectのReminderを、`/control/projects/<Project UUID>/reminders`でProjectのReminderを確認できます。
HomeはActive Projectの一覧への導線と全一覧への導線を提供し、Sleepingの内容を現在のReminderとして代替表示しません。
Workflow画面からはそのWorkflowとの関連で絞り込めます。登録画面では文脈を候補として示すだけで、Workflowを初期選択しません。
Humanが内容と既存5種類の1つを明示入力し、残しておくと確認するとT7で直接登録します。locationは任意の自由入力です。
Workflow関連は任意で、選択と明示確認および所属検証が必要です。関連解除も明示POSTのみで、内容・Project・由来は保持します。
由来はHuman直接登録とAI提案をHumanが保存したものを区別して表示しますが、今回の登録入口はHuman直接登録だけです。
Reminder削除、AI Candidate生成、priority、実行指示への変換はありません。登録・解除はform tokenと最新の対象情報でstale・再送・対象不一致を拒否します。

`require_repository()`でDB利用可否を確認し、`target(project_id, workflow_id)`でUUID・所属を確認します。
後続serviceでも所属・正式Artifactを再検証してください。

form token基盤は`runtime.forms.issue/consume`を利用します。tokenはform本文で渡し、URLへ含めません。
操作・UUID・session・server側で再取得したrevisionへ紐付け、一回のPOSTで消費します。
再表示した同一対象のformは以前のtokenを無効にします。`revision`にPOSTされたhashをそのまま渡してはいけません。
tokenの検証成功はApprovalや実行許可ではなく、既存serviceの検証が引き続き必要です。
実業務POSTは既存Human Control UIからApplication Layerへ接続します。

`runtime.outputs`は実`WorkflowObservation`のコピーをWorkflow UUID別に保持するprocess内メモリです。
`put/get/clear`を提供し、不明Workflowは`None`を返します。DB保存・Output合成・再起動後の復元はしません。
実Workflowの起動には管理DB以外の実行設定も必要です。
標準起動は明示設定からproduction factoryを構成し、不足時は実行操作をSTOPします。
modelは固定せず、runnerの動的選択やfallbackは行いません。
設定一覧、外部AI送信・費用・Git変更・Final Mergeの影響、およびT9隔離環境については
[Human Control実行用Web接続](human_control/README.md)を参照してください。
起動だけでAI実行・Workflow開始・Approval作成・Git変更は行いません。
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
