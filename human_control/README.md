# Human Control実行用Web接続

T8内⑥の実行用依存は、`create_app(..., execution_factory=factory)` に明示的に渡す。
標準の `python app.py` は `create_environment_app()` で以下の設定を読み、
固定構成のproduction factoryを接続する。設定不足でも管理UIは利用できるが、
Workflow開始画面・実行POST・Final判断POSTは理由を表示してSTOPする。
既存Workflowのread-only表示は維持する。modelや保存先のfallbackはない。

## 標準起動の明示設定

管理UIだけを使う場合は、`SPECFLOW_HUMAN_CONTROL_DB` に明示初期化済みDBを指定する。
新規DBの場合に限り `python -m flask --app app:app init-human-control-db --path <明示パス>`
で初期化する。通常起動・再起動でDBを初期化・置換しない。

実Workflowには次の設定も必要。directoryはHumanが事前に用意した絶対パスを指定する。

| 環境変数 | 内容 |
| --- | --- |
| `SPECFLOW_OPENAI_MODEL` | Humanが明示するOpenAI model。Plan・Prompt・Reviewで同じ指定を利用 |
| `OPENAI_API_KEY` | 実行processのOpenAI認証情報。UIや報告へ貼り付けない |
| `SPECFLOW_EXECUTION_REPOSITORY` | 実装・Git・Final Mergeの対象Repository |
| `SPECFLOW_APPROVALS_DIR` | 正式Approval保存先。Webの参照先と共通 |
| `SPECFLOW_EVIDENCE_DIR` | 正式Evidence保存先。Webの参照先と共通 |
| `SPECFLOW_EXECUTION_RECORDS_DIR` | Test RecordとCommand Traceの共通保存directory |

設定後、同じPowerShellから `python app.py` を起動し、`http://127.0.0.1:5000` を開く。
設定値はprocess起動時の構成として固定する。変更時はサーバー再起動が必要。
起動・factory構築はAI実行、Workflow開始、Approval作成、Git変更を行わない。
設定の存在確認は認証・model利用権限やGit正常性の実証ではない。実行時の失敗はSTOPする。

Codex CLIとGitがこのprocessから利用可能であることが必要。
既存コマンド `codex exec --json --ephemeral -` は変更せず、model・権限はHuman管理の
CLI設定を利用する。Webが権限を拡大したり、別runnerへ切り替えたりしない。
起動失敗・非ゼロ終了はSTOPし、stderrをJSONLや画面へ流さない。
JSONLの妥当性は既存parserが検証する。非ゼロ終了の部分stdoutを成功Evidenceに変換しない。

Review Retryには、安全根拠未確認として不許可を返すcallbackだけを接続する。
正常系では呼ばれず、障害時も追加のAI試行を行わない。既存の他工程のRetry契約は変更しない。
Merge Retry保存先は新設定にせず、既存Final契約のsnapshot親directory配下
`retry_history` を利用する。

## 実行影響とT9隔離環境

明示POSTによるWorkflow実行では、正式入力を外部AIへ送信し、費用が発生し得る。
Plan承認後の委任処理は対象RepositoryでCLI・テスト・Git操作を実行する。
Final承認では既存Use Caseが対象の `developer` branchへMergeする場合がある。
委任時のRepository入力と起動設定が不一致なら、Plan承認・委任前にSTOPする。
Final POSTでも対応を再確認する。実行対象に関する他の検証は既存Phase 7に委ねる。

T9実AI E2EにはSpecFlow開発Repositoryを使わず、Humanが別途承認した使い捨てRepositoryを使う。
例（production既定値ではなく、手動準備する配置案）：

```text
<Human指定のT9ルート>/run-001/
  target-repo/                 # 独立した.git、初期commit、developer branch、remoteなし
  runtime/
    human-control.sqlite3
    approvals/
    evidence/
    execution-records/        # Trace / Test Recordは同じdirectory
    workflows/<識別領域>/     # 正式入力、State、History、Plan、Prompt、Review、Final
```

Finalの `retry_history` は上記Final保存先配下に既存処理が保存する。
この配置だけではOSアクセス隔離にはならない。CLI権限と送信対象はHumanが確認する。
検証Repositoryのcwdから既存 `python -m infrastructure.specflow_test_wrapper` を利用できる
Python環境・module検索pathも必要（SpecFlowコードを変更対象としてコピーしない）。
正式Specification、保存済みApproval、既存State等はUIの入力契約どおり明示し、
AIや起動コードが補完・承認しない。実AI E2EとFinal Mergeは別途Humanの承認後に行う。

## 既存UI接続契約

`factory(workflows, registered_workflow) -> ApplicationPorts` は、⑥ではWorkflow登録後に一度だけ呼ばれる。
既存の `WorkflowEntryUseCase`、`PlanWorkflowUseCase`、`ImplementationWorkflowUseCase`、
`EvidenceWorkflowUseCase`、`ReviewWorkflowUseCase`、`FinalApprovalWorkflowUseCase` を構成して返す。
productionでは、それぞれの既存constructorに実際のAI service / runner、保存repository、
Git・test-state provider等を明示的に与える。test mockへのfallbackはない。
Approval / Evidence repositoryはWebの `approvals_dir` / `evidence_dir` と同じ正式保存先を使い、
Git接続はHumanが指定する対象Repositoryと一致させる。factoryの失敗・必要portの欠落では
登録済みWorkflowを残してSTOPする。

開始入力には、既存Stateと正式文書、保存済みSpecification Approval ID、生成metadata、
新しいPlan保存先が必要。基本方針の確認項目から正式文書を生成しない。
入力確認後の開始POSTでtokenを消費し、登録、Entry、Plan生成・保存を同期実行する。
次のHuman Plan判断まで自動で進む。登録の成功はApplication Layerの成功ではない。

Plan承認時は、委任用入力をすべて検査した後、同じadapterの `decide_plan` に渡す。
source / test pathとscopeは文字列のJSON配列。空配列もHumanが明示する。
TDD適用、不要理由、Review方式、branch、Prompt規則等を推測・補完しない。
Plan / Promptのhashとidentityは実際のOutputと正式記録から結び付ける。
既存Approval IDの上書きを避けるため、Plan判断の保存先IDは未使用のものを指定する。
Approvalの意味と妥当性の検証は既存Phase 7に委ねる。

実adapterは `human_execution.runs` にWorkflow UUID単位で保持する。
`observation()` を既存 `human_control.outputs` にコピーするが、両者とも同一process内のmemoryのみ。
単一processで実行し、複数worker間の共有・永続checkpoint・自動再接続は行わない。
restart後は実adapterを再生成せずSTOPし、既存Workflow画面のT5による正式Artifact再構成へ戻す。

Revisionは明示された新しいPlan保存先へ出力し、改めてHuman判断を待つ。
承認後は既存adapterの同期接続に従ってPrompt、Implementation、Evidence、Reviewを進める。
⑥の開始・Plan判断接続ではReview Handoffを表示し、Finalへ進める場合も `final.start` の判断待ちまで。
この接続からCorrection、`decide_final` / `final.resume`、Mergeは呼ばない。
例外・部分保存では実Outputと正式記録を保持してSTOPし、rollbackや再送による再実行を行わない。

## T8内⑦の共通Human判断とFinal専用checkpoint

Project・Workflow・実行結果画面から、同じWorkflowの `/decisions` へ移動できる。
画面には判断理由、正式State / History、判断材料、既存の返却内容、不足情報を表示する。
基本方針の現在値と確認状態も提示し、項目の再確認と進行中Workflowへの影響判断を区別する。
基本方針から正式Stateへの自動変換や、独自の継続・停止操作は追加しない。
Plan判断は⑥の既存画面へ接続する。Review Handoffでは未定義の判断・Correction操作を作らない。

Final判断画面のGETはT5のread-only検証と既存checkpoint loaderだけを使用し、
`final.resume` は呼ばない（このmethodは診断Artifactも保存するため）。
明示POSTでのみ既存5選択肢・理由・参照情報・必要なApproval ID / 時刻を渡す。
最終承認では、既存Final Use CaseがMerge前提を検証し、Merge・Completedまで進む場合がある。
差し戻しは既存routing結果の表示・Handoffまで。独自のMerge、差し戻し先実行、Retryは追加しない。

同じprocessの実adapterがある場合は `decide_final` を使う。restart後は新しいadapterや
上流Outputを合成せず、検証済みの既存Final checkpointに対して `ports.final.resume` を使う。
この場合、明示POST時にfactoryから実行用依存を取得し、取得後も正式対象・基本方針を再確認する。
factoryはconstructorの構成だけを行い、正式記録や管理情報を変更しないこと。
依存やArtifactが不足すればSTOPする。汎用checkpointやSQLite schemaは追加しない。

POST試行と返された実Final Outputはprocess memory内にだけ保持する。
Final結果・Merge checkpointの参照は既存indexに記録し、実Outputは既存Output holderに渡す。
同一processの再送拒否に加え、restart後は既存の `.decision.json` receipt等を検証する。
既に判断済み・部分保存・Merge失敗等では自動でやり直さず、実記録を提示してHandoffする。
判断後は同じWorkflow画面に戻り、実結果と保存失敗を表示する。
