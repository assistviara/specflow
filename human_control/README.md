# Human Control実行用Web接続

T8内⑥の実行用依存は、`create_app(..., execution_factory=factory)` に明示的に渡す。
環境変数から起動する標準の `app` には実行用factoryを設定していないため、
管理情報の閲覧はできるが、新しいWorkflow開始は安全にSTOPする。
AI service、model、runner、repository、retry authorizationを自動選択しない。

`factory(workflows, registered_workflow) -> ApplicationPorts` は、Workflow登録後に一度だけ呼ばれる。
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
Review Handoffは表示し、Finalへ進める場合も `final.start` の判断待ちまで。
Correction、`decide_final` / `final.resume`、Mergeは呼ばない。
例外・部分保存では実Outputと正式記録を保持してSTOPし、rollbackや再送による再実行を行わない。
