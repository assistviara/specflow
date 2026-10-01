# Phase 8A Human Control UI MVP — Implementation Plan

Version: 0.1.0-draft

Status: Draft / Human Approval Pending

## 1. Plan概要 / Purpose

- 対象プロジェクト：SpecFlow
- 対象機能：Phase 8A Human Control UI MVP
- 作成日：2026-10-01
- Plan状態：`human_review_required`
- 調査基準：`developer` / `b268773c23ea18516dc2b35fad47629534ebf785`
- Phase 7 Application Layer MVP baseline：`68c827ec14c1e1a190878470a14187dfa0277140`
- 根拠Specification：[Phase 8A Specification v0.2.0](../specification_phase8a_human_control_ui_mvp_v0.2.0.md)（Human Approved）
- Human Decisions：Specification §15の8A-01・8A-02、[Decision Artifact](../decision_phase8a_human_control_ui_mvp.md)の8A-03～8A-13
- 既存契約：[Application Layer Specification](application_layer_specification_v0.2.0-draft.md)、[Application Layer Implementation Plan](application_layer_implementation_plan_v0.1.0-draft.md)

既存Application Layerの外側にHuman Controlを追加し、Humanが内部工程を記憶せず、必要な判断に集中できるようにする。本書は実装順序・責務・検証対象を示すDraftであり、Human Plan Approval、実装開始許可、runtime Approval Recordではない。

本書のTarget番号は実装計画上の区分であり、新しいHuman Decision番号やWorkflow Stateではない。以下の変更予定パスはリポジトリルート基準の計画案であり、今回作成するコードではない。

## 2. Specificationの理解 / Scope

### 2.1 対象範囲

Project作成・既存開発物の明示登録、Project Constitution確認、Project / Workflow UUIDと関連管理、Active / Sleeping、正式Artifactからの再開・進捗再構成、Human Intent、End Work、Human直接登録Reminder、8画面、既存Application Layerへの接続、Stop / Human Handoffを対象とする。

Projectは育てていく開発対象、FeatureはProjectが提供する機能、Workflowは一回のSpecificationを起点とする変更・追加・修正等の開発単位である。一つのWorkflowが複数Featureにまたがることを妨げない。Featureの独立CRUD modelは作らない。

SQLiteは「どれを見るか」、Application Layerは「それが正しいか」、Humanは「どうするか」を担当する。正式State、承認、Evidence、Review、Git結果をSQLiteの管理情報で置き換えない。

### 2.2 Out of Scope

- Phase 8B Specification Dialogue、自然言語からのSpecification Draft生成、AIによるConstitution作成。
- Reminder Candidateの自動発見・自動生成、advanced AI consistency checking、優先順位決定。
- multi-user、authentication / authorization、role管理、concurrent editing、PC間完全同期。
- 過去のPhase 1～8A履歴・Workflowの自動移行、Feature CRUD model。
- dynamic runner selection、automatic fallback、advanced rebase、automatic conflict resolution、multi-repository support。
- Phase 7再実装、Evidence storage architecture再設計、Final Approval差し戻し後の未定義経路の拡張。
- 新frontend framework、不要なAPI分離、ORM・汎用database abstraction。

複数ProjectのHuman Control管理を、複数Repositoryを統合制御する機能へ拡張しない。実行時は既存Use Caseが要求する一つの対象Repositoryとその正式入力を扱う。

## 3. 現状調査

### 3.1 Webと保存

`app.py`はFlaskを使用し、`/`と`/projects/<project_name>`を提供する。`templates/base.html`、`index.html`、`project_detail.html`にJinja / HTML / CSSがある。現行POSTは固定パスのSpecificationを書き換えるだけで、Application Layerへ接続されていない。これを承認済みArtifact編集の入口として流用しない。

`project.json`とProjectディレクトリは存在するが、Phase 8AのProject / Workflow modelではない。`core/project_loader.py`、`core/state_manager.py`は空ファイルであり再利用済み管理基盤として数えない。現行ローカルStateの`specification_editing`等をPhase 8A Workflowへ自動変換しない。

Current State / History / Approval / Evidence等にはJSON等のfilesystem保存実装がある。Phase 8A用SQLite実装、Focus、Human Intent、Reminderは存在しない。

### 3.2 再利用する契約

| 領域 | 既存実装 | Phase 8Aの接続責務 |
| --- | --- | --- |
| Entry | `application/workflow_entry.py` | Specification、保存済みApproval ID、State / History参照を渡す |
| Plan | `application/plan_workflow.py` | `generate / decide / revise / generate_prompt`へ既存条件を満たす入力を渡す |
| Implementation | `application/implementation_workflow.py` | 承認済みPlan / Prompt、TDD根拠、対象Repository等を受け渡す |
| Evidence | `application/evidence_workflow.py` | 保存されたEvidenceとReview Inputを受け渡す |
| Review | `application/review_workflow.py` | Review / Correction / Handoff結果を保持・提示する |
| Final Approval | `application/final_approval_workflow.py` | 対象提示、明示判断、既存checkpoint再開・Retry契約へ接続 |
| State / History | `application/current_state_repository.py`、`state_transition_history.py` | 正式保存先を参照し、UIが独自遷移を作らない |
| Approval | `core/approval_record_service.py`、`approval_validation.py`、`infrastructure/json_approval_record_repository.py` | Human判断を既存契約へ渡し、現在Artifactに対する検証を委譲 |
| Trace | `application/workflow_trace.py` | Output列・正式State / Historyに基づく読み取り専用表示 |
| Merge / Completed | `application/merge_preconditions.py`、`merge_execution.py`、`technical_merge_retry.py`、`phase_six_completion.py` | 既存Final Approval経路を利用し、別Merge経路を作らない |

Workflow Traceは実行許可ではない。Final Approval用checkpointは全工程共通の復元機構ではない。Stateだけから不足する上流Outputを捏造できない。State保存後にHistory保存が失敗する可能性もあり、UIで成功を補完しない。

## 4. 前提条件の確認

| ID | 前提条件 | 状態 | 根拠 |
| --- | --- | --- | --- |
| PRE-01 | SpecificationがHuman Approved | PASS | Specification v0.2.0 |
| PRE-02 | 8A-01～8A-13が確定 | PASS | Specification §15 / Decision Artifact |
| PRE-03 | Phase 7基準点が現在HEADの祖先 | PASS | `68c827e` → `b268773` |
| PRE-04 | Web基盤を再利用できる | PASS | Flask / Jinja / HTML / CSS |
| PRE-05 | 全工程に永続checkpointがある | FAIL | Final Approvalには専用機構、他工程は共通機構なし |
| PRE-06 | 不明な再開・未定義差し戻しをSTOPできる | PASS | 8A-08、8A-13 |
| PRE-07 | 本PlanのHuman Approval | UNKNOWN | 本書はDraft、実装開始不可 |

PRE-05を隠さず、再構成できる契約のみ接続する。正常な再開可能例と安全なSTOP例を別々に検証する。すべてをSTOPにするだけでResume要件を満たした扱いにはしない。

## 5. 要件対応表 / Architecture

### 5.1 責務境界

```text
Human
  ↓ 明示操作・判断
Flask / Jinja UI
  ↓ 入力変換・対象特定
Human Control outer layer
  ├─ SQLite: UUID、関連参照、Focus、確認状態、Intent、Reminder
  └─ 既存Application Layer: 検証、State遷移、Artifact、実行、承認境界
```

SQLiteから得たpath、hash、Approval IDはindexであり、承認・安全性の証明ではない。画面表示用情報と実行判断を分離し、処理実行前に既存契約で再検証する。AI結果からHuman Decisionを生成しない。

SQLiteの最低限の論理情報は、Project UUID / name、Constitutionの3項目と各項目のHuman確認状態、FocusとSleeping操作日時、Workflow UUID / Project UUID / name、Specification path / hash / Approval IDとの関連、正式Artifactへの参照、Human Intent、Reminderである。確認を受けた内容と現在内容を対応させる。SQLiteに正式State値・Approval全文・Evidence全文等の複製を保存しない。

Reminderには本文、必須Project UUID、任意Workflow UUID、性質の分類、任意の実行場所、登録由来を持たせる。Workflow関連が別Projectを指す状態を許容しない。分類は不具合・改善案・新機能候補・将来構想・要検討を区別し、重要度・priority・実装承認へ変換しない。

新規永続化はPython標準SQLite接続で扱う計画とし、ORMや別database serviceを追加しない。保存先は明示的に渡す構成とし、特定PCの絶対パスを埋め込まない。既存Artifactの保存形式・検証責務は維持する。

### 5.2 要件とTargets

| ID | 根拠 | 対応方針 | Target | 検証 |
| --- | --- | --- | --- | --- |
| R-01 | §2–4、8A-01/05/10 | 未完成Project、項目別確認、既存Project明示登録 | T1–T2 | 作成・Gate・reconfirmation・移行なし |
| R-02 | §2/14、8A-06 | immutable UUID、Project所属、起点関連、Featureと分離 | T1/T4 | rename・複数Workflow分離 |
| R-03 | §6/8.1/8.6 | 明示Focus切替、最大Active 1、最近Sleeping最大3 | T3 | 原子的切替・日時順・正式State不変 |
| R-04 | §8.4/10/12、8A-06/08/13 | 正式Artifact再検証、既存契約のみ実行、不明はHandoff | T4–T5/T8 | 正常再開・missing/mismatch/non-unique |
| R-05 | §7/8.5、8A-04/07 | 事実再構成、Intent保存、操作完了後のEnd Work | T5–T6 | Intent非実行・UI復帰後の終了選択・終了後の新工程非開始 |
| R-06 | §8.8/9、8A-02/09/12 | Human直接Reminder、Project必須、Workflow任意、由来分離 | T7 | 関連確認・未承認Candidate非正式化 |
| R-07 | §8/12、8A-13 | 8画面、Human判断、既存差し戻しHandoff | T8 | route / 表示 / 判断 / 差し戻し |
| R-08 | §10/11、8A-03/11 | SQLite index、既存JSON等維持、runtime Git除外維持 | T1/T4/T9 | authority分離・保存失敗・Git境界 |
| R-09 | §14 | TDD・Phase 7 regression・MVP監査 | T1–T9 | Initial FAIL→Target PASS→Full PASS |

### 5.3 8画面への接続

| 画面 | 表示・操作 | 根拠と接続 |
| --- | --- | --- |
| 起動画面 | 判断待ち、Active、最近Sleeping最大3件、Reminder、Project作成入口 | SQLiteの対象indexと正式Trace / Handoff。不存在を正常完了と表示しない |
| 新Project作成 | name、Purpose / Values / Rules、未完成保存、既存開発物の明示登録 | T2。作成時にWorkflow承認を生成しない。作業なしとGate不足を表示 |
| Project開発 | Focus、現在Workflow、Workflow履歴、Constitution、前回の事実、Intent | T2–T5。「続き」と「新しい作業」を別操作にする |
| Workflow作業 | Specification、Plan判断、Implementation / Review / Final Approval | T4–T5。既存契約に必要な情報・判断を提示 |
| 作業終了 | 到達事実、再開可能地点または不足、Intent入力、Focus選択 | T6。正常なsession終了でありCancellationではない |
| Sleeping一覧 | Project一覧・参照・明示Active復帰 | T3。Focus変更はState変更ではない |
| Human判断 | 原因、判断理由、材料、既存契約上の選択肢、不足情報 | T8。明示判断後に同じWorkflowの結果表示へ戻る |
| 思い出しておくこと | Human直接登録、分類、Project、任意Workflow・場所、関連再提示 | T7。Workflow候補はHumanが確認・解除する |

新frontend framework、REST API層、browser自動起動機構は追加しない。既存のlocal server起動とURLを開く手順を利用する。

## 6. 変更予定ファイル

以下はDraftとしての配置案。既存パッケージの責務を移動せず、外側に小さいHuman Controlパッケージを追加する。

### 6.1 新規作成予定

| パス | 責務 |
| --- | --- |
| `human_control/__init__.py` | 外側パッケージ |
| `human_control/models.py` | Project / Workflow identity、Constitution確認、Intent、Reminderの管理情報 |
| `human_control/sqlite_repository.py` | Human Control管理情報のSQLite保存・取得 |
| `human_control/projects.py` | Project作成・明示登録・Constitution Gate・Focus |
| `human_control/workflows.py` | Workflow所属・起点関連・正式参照の分離 |
| `human_control/application_adapter.py` | 既存DTO / Use Caseへの変換・依存接続。新しい承認・遷移規則を持たない |
| `human_control/resume.py` | 正式情報に基づく表示・再開入力の再構成、不成立時のHandoff |
| `human_control/work_session.py` | 操作完了・UI復帰後のEnd Work、Human Intent。並行受付機構は持たない |
| `human_control/reminders.py` | Human直接登録・関連・分類・由来の境界 |
| `templates/project_new.html`、`workflow.html`、`end_work.html`、`sleeping_projects.html`、`human_decision.html`、`reminders.html` | 既存2画面と合わせた8画面 |
| `tests/test_human_control_*.py` | T1～T9に対応する単体・route・integrationテスト |

### 6.2 変更予定

- `app.py`：既存Flask起点から外側Use Caseを構成・呼び出す。固定Specification上書きを新Workflow操作と混同させない。
- `templates/base.html`、`index.html`、`project_detail.html`：既存表示基盤を再利用し、8画面に必要な導線・情報を追加。
- `.gitignore`：新local保存先とSQLite付随ファイルがGit管理へ漏れないことを確認し、必要範囲のみ追加。既存Evidence除外は維持。
- `README.md`：承認後の実装に対応するlocal起動・保存・利用手順のみ更新。

既存`application/`、`core/`、既存`infrastructure/`のPhase 7契約変更は予定しない。既存Testsは維持する。削除・既存履歴移行は予定しない。今回の作業では上記コード・設定・テストを作成／変更しない。

## 7. 実装順序 / Targets

各TargetはPlan承認後、対象の失敗テスト→最小実装→対象テスト→関連Regressionの順で進める。後続Targetは先行Targetの成立を前提とする。

### T1. Human Control persistence / identity

- 根拠：R-02/R-08、8A-03/06/11。
- UUIDとHuman-facing nameを分離し、Workflowの単一Project所属、正式Artifactへのindex、SQLite責務を定義・実装する。
- local DBと既存JSON Artifactを分離する。初期化はPhase 8A管理用の新規storageのみで、旧データmigrationは行わない。
- DB保存失敗を成功表示しない。SQLite更新とfilesystem処理を単一transactionが保証するかのように扱わない。
- 完了条件：rename後もidentity保持、複数Workflowの関連分離、index変更で承認やStateが成立しない、永続化失敗を検出できる。

### T2. Project / Constitution / Existing registration

- 根拠：R-01、8A-01/05/10。
- Projectは3項目が未完成でも保存できる。空欄・unknownをHuman確認済みにしない。「現時点では特になし」の明示確認を有効とする。
- 変更項目だけをreconfirmation pendingとし、3項目すべて確認されるまで新Workflow開始を拒否する。
- 進行中Workflowがある場合、変更後Constitution・現在Workflow・判断材料を提示する。変更の重要性や継続可否を推測しない。既存Stateを自動変更しない。
- 既存開発物はHumanの登録操作で新Project UUIDを得る。以前のWorkflowを生成せず、Git / Artifactをそのまま残す。
- 完了条件：Project Creation GateとNew Workflow Start Gateが独立し、旧Project自動探索を登録承認と扱わない。

### T3. Active / Sleeping

- 根拠：R-03、§6。
- Humanの明示操作で最大1件をActiveにする。切替元のSleeping化と切替先のActive化が矛盾しないようにSQLite更新をまとめる。
- 最近SleepingはHumanの［寝かせる］操作日時を根拠に新しい順で最大3件。単なる更新日時で代用しない。
- 新規作成・単なる閲覧を暗黙のFocus切替にしない。Activeなしも最大1件の制約内である。
- 完了条件：Focusの切替・保存失敗・再読込を検証し、正式State / History / Approval / Evidenceに変更がない。

### T4. Workflow起点 / Phase 7 adapter

- 根拠：R-02/R-04/R-08、8A-06。
- Workflow UUID、所属Project、Specification reference / hash / Approval ID、State / History等への参照を対応付ける。各Workflowの保存対象を混線させない。
- Humanが指定した既存Specificationと実際のApproval Recordを用い、`WorkflowEntryUseCase`の検証へ接続する。本文の`Human Approved`表記やSQLiteの値だけで承認を生成しない。
- 既存Use Caseが要求するConstitution等の文書、対象Repository、TDD根拠、approved scope、source/test選択等を正式入力から受け渡す。一意に取得できない情報は不足として返し、初期値やAI推測で埋めない。
- Plan生成からFinal Approvalまでの既存入口を接続し、成立したOutputと実際のArtifact参照を区別して保持する。承認待ちはHumanへ返す。安全で委任済みの後続処理に不要なNext操作を追加しない。
- 完了条件：既存正常経路に接続できること、変更済みSpecification・無効Approval・所属不一致で下流処理が呼ばれないこと。

### T5. Resume / Work continuity projection

- 根拠：R-04/R-05、8A-04/08/13。
- UUIDで対象を特定し、実際のState / History / ArtifactとApprovalを読み、既存契約が要求する同一性・整合性を再検証する。
- 「前回ここまで」は読み取れた正式事実から表示時に再構成する。Humanの手入力やSQLiteへの正式State複製を使わない。
- 同一process内の成立済みOutputがある場合も実Artifactを再確認する。再起動後は既存Repository / checkpointで復元できる情報だけを使用する。Final Approvalには既存checkpoint復元を利用する。
- 未保存の上流Outputが必要、参照missing、hash mismatch、対象non-unique、State/History不整合等は未解決内容・理由・必要なHuman判断を提示してSTOPする。State文字列から成功Outputを合成しない。汎用checkpoint保存方式を新設してPhase 7を再設計しない。
- 過去Intentは過去のHumanの意思として再表示するのみで、現在の選択や実行要求として扱わない。
- Final Approval差し戻しは既存判断・返却先・不足情報を表示してHandoff。`final_approval_pending`からPlan修正へ独自に遷移させない。8A-13の正常な終了範囲であり、Workflowの`completed`を意味しない。
- 完了条件：正常な継続・checkpoint再開・安全な非再開を区別でき、Active / Sleepingで検証原則が変わらない。

### T6. End Work / Human Intent

- 根拠：R-05、8A-04/07。
- 現在の操作が完了してUIへ戻った後、Humanが［今日はここまで］を選択できるようにする。End Work後は新しい工程を自動開始しない。
- 不可分単位は既存Use Case呼び出しの責務境界を利用し、内部の承認・Merge・Correction処理を途中で分割しない。呼び出しが返っても保存失敗等があれば成功と表示しない。
- 実行中の既存Use Caseを強制終了しない。実行中に別requestとしてEnd Work要求を受け付けるためのjob管理、thread管理、並行受付機構等は新設しない。
- これはHuman ReviewによるPhase 8A MVPの実装範囲の最小化であり、Human Decision 8A-07の意味を変更するものではない。
- 到達した正式事実を再構成し、安全な再開地点または未解決理由とともに表示する。Human IntentをSQLiteへ保存できるようにする。Activeのままにする／Sleepingにする選択は別のHuman判断とし、End Work自体でFocusを変更しない。
- process異常終了から実行成功を推測しない。再起動時はT5で再検証する。
- 完了条件：操作完了・UI復帰後にEnd Workを選択でき、その後に新しい工程を自動開始しない。既存Use Caseの不可分な境界と正式記録を維持し、到達事実の再構成、Intent保存、別判断によるFocus選択ができる。End WorkをWorkflow Cancellation / Errorとして扱わず、正式Stateを自動変更しない。

### T7. Reminder

- 根拠：R-06、8A-02/09/12。
- Human直接登録、分類、Project必須関連、任意Workflow関連、任意の実行場所、文脈に応じた再提示を実装する。
- 現在Workflowの提示は候補に留め、Humanが確認または解除して保存する。Workflow関連は発見時の由来であり、実装先ではない。
- Human direct / AI proposed then Human savedを混同しない表現を保つ。今回のMVP登録経路はHuman directであり、AI自動生成や未承認候補の正式保存経路を追加しない。
- 完了条件：Projectなし登録拒否、別ProjectのWorkflow関連拒否、任意関連解除、分類・由来保持、保存をpriorityや実装承認と解釈しない。

### T8. Flask / Jinja 8画面とHuman Decision UI

- 根拠：R-07、§8、8A-05/13。
- §5.3の8画面を既存Flask / Jinja基盤に接続する。UI独自のWorkflow State機械や承認処理を作らない。
- Planの承認・修正・中止、Final Approvalの既存5選択肢等を対応する既存契約へ渡す。操作対象のUUID・Artifactを確認し、別Workflowへ判断を流用しない。
- 既存Handoffに選択肢が一意に定義されていない場合、選択肢を捏造せず不足情報を表示する。判断後の画面復帰と工程自動再実行を区別する。
- Constitution変更時の判断も、未定義の正式State遷移やHumanの代わりの判断に変換しない。
- 完了条件：8画面の必要情報、判断理由と材料、新規/再開の区別、誤送信・再送・stale対象の下流実行拒否を検証する。

### T9. Boundary / Regression / MVP Completion audit

- 根拠：R-08/R-09、§14、8A-11/13。
- Git管理対象とlocal管理情報、DB付随ファイル、Evidence除外を確認する。`approvals/`や`state_history/`等は保存先次第で除外が異なるため、名称だけで管理外と断定しない。
- 正常系でProject→Workflow→既存工程→Human判断を通し、未定義差し戻しではHandoffを検証する。STOPしたWorkflowをCompletedとして集計しない。
- T1～T8のテスト、Phase 7 Regression、8画面の手動確認、Overengineering Checkを実施する。
- 完了条件：§12の項目を証拠と照合し、失敗・未実施・不足を隠さずHumanへ報告できる。

## 8. TDD / テスト計画

### 8.1 TDD方針

振る舞いを追加するTargetでは、変更前に対象要求の失敗テストを確認し、最小実装でPASSへ進める。既存Application LayerのTest Execution Record / Evidence / TDD検証方式を変更しない。対象テストとFull Regressionの結果を区別し、実行していない検証をPASSと記載しない。

### 8.2 必須検証領域

| 領域 | 正常系 | 異常系・境界 |
| --- | --- | --- |
| Project / Constitution | 未完成保存、明示的「特になし」、3項目確認後開始 | blank/unknown、変更項目再確認、進行中State自動変更なし |
| Identity | UUID保持、rename、複数Workflow | 所属不一致、参照取り違え、non-unique |
| Focus | 明示切替、Sleeping再開、最近最大3件 | 保存失敗でActive複数化しない、State不変 |
| Resume | 正式情報から再構成、既存checkpoint復元 | missing/mismatch/non-unique、部分保存、stale Approval、上流Output不足 |
| Work continuity | 正式事実表示、Intent保存・再提示 | 過去Intent自動実行なし、記録不能を隠さない |
| End Work | 操作完了・UI復帰後の終了選択、正式事実の再構成、Intent保存、別判断でFocus選択 | 強制終了・不可分境界の分割なし、終了後の新工程自動開始なし、Cancellation / Error化・正式State自動変更なし、Focus自動変更なし。操作中の別request受付は要求・テスト対象にしない |
| Reminder | 分類、場所、Project、任意Workflow | 未承認Candidate非正式化、由来偽装なし、別Project関連拒否 |
| Existing registration | Human明示登録、新UUID、新Workflow | 自動登録・過去Workflow捏造・旧Artifact変更なし |
| Human Decision | 既存選択肢、判断後の同一Workflow表示 | 承認なし進行、再送、対象変更、AI代行を拒否 |
| Final return | 8A-13の返却先・材料表示とHandoff | 独自State遷移・自動再実行・Completed化なし |
| Persistence / Git | SQLiteと正式Artifact分離 | DB失敗、filesystem部分保存、SQLiteからState復元なし、runtime漏出なし |

### 8.3 Regression

- `tests/test_workflow_entry.py`、`test_plan_workflow.py`、`test_implementation_workflow.py`、`test_evidence_workflow.py`、`test_review_workflow.py`。
- `tests/test_final_approval_workflow.py`、`test_workflow_trace.py`、`test_mvp_e2e.py`。
- `test_approval_*.py`、`test_state_transition*.py`、`test_current_state_repository.py`。
- Evidence / Test Execution Record / command trace / Correction / Retry関連の既存テスト。
- `test_git_cli_merge_*.py`、`test_merge_*.py`、`test_phase_six_completion.py`、Core / AI Runner / 依存方向の既存テスト。
- 最後に既存CIと同じ`python -m pytest -q`でFull Regression。Git操作は既存テスト同様に使い捨てRepository内、AIは制御されたtest doubleで検証する。

Flask route検証には既存Flaskのtest clientを利用する計画とし、新browser automation依存を必須化しない。手動確認では8画面、Human判断の分かりやすさ、新規/再開誤認防止、End Work中の表示、Sleeping後の文脈復元を確認する。実AIによる品質検証とofflineの契約検証を混同しない。

## 9. リスク

| リスク | 影響 | 対応 |
| --- | --- | --- |
| 既存Outputの復元不足 | 再起動後に次工程へ安全に進めない | 8A-08の明示STOP。正常復元例も検証し、万能resumeを装わない |
| SQLiteとArtifact保存の部分成功 | indexと実体の不一致 | 再読込・既存検証、失敗表示、成功やrollbackを推測しない |
| 操作完了前のEnd Work受付を期待する誤解 | 強制終了や不要な並行受付機構の追加 | MVPでは操作完了・UI復帰後に選択する。既存Use Caseの不可分境界を維持し、job / thread管理を新設しない。End Work後の新工程自動開始を防ぐ |
| Approval対象の変更・再送 | 古い承認の誤適用 | 実Artifact同一性を再検証し既存契約へ渡す |
| runtimeファイルのGit混入 | clean判定・機密情報・保存境界への影響 | local配置と付随ファイル除外の検証、Evidence除外維持 |
| 未定義差し戻しを実装で埋める | Phase 7契約変更 | 8A-13の正常Handoffで終了 |

## 10. 人間確認事項

8A-13により、前回停止理由であるFinal Approval差し戻し境界はResolvedとなった。本Draftの要求・責務・Target範囲について新たな`HUMAN_DECISION_REQUIRED`は検出していない。ただし本Plan自体のHuman Review / Approvalは未完了である。

実装時に正式Artifactと既存契約から一意に決まらない業務判断・保存authorityの変更・新しい状態遷移が必要になった場合、実装上の都合で補完しない。問題、根拠、選択肢、影響、最小MVP案を提示してHumanへ返す。欠落しているruntime入力に対する正常なSTOPと、本Planに新要件を追加する判断を区別する。

## 11. 変更禁止事項の確認

- Constitution、Principles、承認済みSpecificationを書き換えない。
- 既存Phase 7のState、Approval、Evidence、Review、Final Approval、Merge契約を変更しない。
- SQLiteを正式State / Approval Authorityにしない。
- 同じ正式情報を意図的に二重保存しない。
- Plan工程でsource / test / UIを実装しない。DB作成、migrationを行わない。
- Human Plan Approvalの生成、implementation-ready扱い、commit / push / mergeを行わない。

## 12. 完了判定方法

### 12.1 将来のPhase 8A実装Completion

1. ProjectをConstitution未完成で作成でき、明示確認前にはWorkflow開始を拒否する。
2. Constitution変更を項目別に再確認へ戻し、進行中Workflowを独自判断で変更しない。
3. immutable UUIDでProject / Workflowを区別し、複数WorkflowとFeature非同義を維持する。
4. Active最大1件とSleeping情報保持、最近Sleeping最大3件を満たす。
5. 既存Specificationと実Approvalを起点に既存Application Layerへ接続できる。
6. 正式情報から現在地点を再構成し、明確な正常再開と根拠不足時のSTOPを区別する。
7. 過去Intentを再表示し、自動実行しない。操作完了・UI復帰後にEnd Workを選択でき、以後の新工程を自動開始しない。実行中Use Caseの強制終了・不可分境界の分割・別request受付用のjob管理やthread管理は行わない。End WorkをWorkflow Cancellation / Errorとせず、到達した正式事実の再構成とSQLiteへのHuman Intent保存を行い、Active維持／Sleepingへの変更は別のHuman判断とする。
8. ReminderをHumanが保存・分類・再提示でき、Project必須、Workflow任意、provenanceとHuman保存境界を守る。
9. 既存開発物は明示登録のみで、過去履歴の自動移行を行わない。
10. 8画面で判断材料と不足を提示し、委任済みで一意な処理に不要なNext操作を要求しない。
11. 8A-13の差し戻しを正常なHandoffとして扱う。これはApplication Layerの`completed`への遷移条件を緩和しない。
12. SQLite / Evidence / Git境界とPhase 7契約を保持し、Phase 8Aテスト・既存Regression・手動確認を完了する。

### 12.2 今回の文書作成Completion

Decision 8A-13の追記、根拠とTargetsの対応、文書リンク・差分・空白検証を完了し、本DraftをHuman Reviewへ返す。上記実装Completionやテスト成功を今回達成したとは報告しない。

## 13. Plan結論

- Plan状態：`human_review_required` / Draft / Human Approval Pending。
- Targets：T1～T9の9件。
- 新たなHuman Decision要求：なし（8A-13適用後の本Draft範囲）。
- 実装へ進めるか：不可。HumanによるPlan Approvalを待つ。
- 次の行為：Human Review。本書作成後にSTOPする。

## 14. MVP Overengineering Check

| 確認項目 | 判定 | 根拠 |
| --- | --- | --- |
| Phase 8B機能混入 | なし | Dialogue / Specification生成 / AI Candidate自動生成を対象外化 |
| Phase 7の不用意な変更 | なし | 外側接続のみ。未定義差し戻しは8A-13でHandoff |
| SQLiteの新State Authority化 | なし | UUID・参照・Human管理情報のみ。正式検証は既存Layer |
| 不要なNext連打 | なし | 一意で委任済みの接続は継続し、判断・不足だけHumanへ返す |
| AIによるHuman Decision代行 | なし | 明示判断を既存契約へ渡し、推測による承認を禁止 |
| migration過剰化 | なし | 既存開発物の明示登録以後のみ管理 |
| Reminderのpriority system化 | なし | 分類・由来・場所・関連に限定 |
| frontend / database / APIの複雑化 | 抑制 | Flask / Jinja再利用、SQLite、ORM・API分離なし |
| MVP完成を遅らせる構造 | 抑制 | 9 Targets。End Workは操作完了・UI復帰後に限定し、操作中の別request受付用job管理・thread管理・並行受付機構を新設しない。汎用checkpoint・分散job基盤・完全差し戻し再実行を作らない |

将来の利便性だけを理由に対象を増やさない。安全なSTOPを隠さず、実装範囲の追加が必要になった場合はHuman Decisionへ戻る。
