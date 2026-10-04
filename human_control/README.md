# Human Control実行用Web接続

T8内⑥の実行用依存は、`create_app(..., execution_factory=factory)` に明示的に渡す。
環境変数から起動する標準の `app` には実行用factoryを設定していないため、
管理情報の閲覧はできるが、新しいWorkflow開始は安全にSTOPする。
AI service、model、runner、repository、retry authorizationを自動選択しない。

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
