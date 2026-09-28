# Phase 7 Target 8 実装照合記録

- 対象: End-to-End MVP Validation and Completion
- Baseline: developer / 33b8986
- 状態: 検証中。Humanによる最終監査・Application Layer MVP COMPLETE宣言は未実施。
- 範囲: 不足するE2E testsと既存検証の照合。Production Codeの変更なし。
- 本記録は実装担当による照合資料であり、独立レビューやHuman Approvalを代替しない。

## 正式根拠

- [Specification §14](../projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md): MVP Completion Conditions
- [Implementation Plan](../projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md): Phase 7 Target 8、対応するTestsおよびCompletion Conditions
- 既存Phase 1〜6とTarget 1〜7の責務、State、UseCase、Approval境界は変更しない。

## Test識別子

新規testsはすべて [test_mvp_e2e.py](../tests/test_mvp_e2e.py) に置く。

| 略称 | test名（test_mvp_に続く部分） |
|---|---|
| MAIN | e2e_correction_to_verified_completion_preserves_approval_and_evidence_lineage |
| ENTRY | entry_failure_stops_plan_and_preserves_saved_approval |
| PLAN | plan_human_return_preserves_history_and_requires_new_approval |
| PROMPT | prompt_gate_failure_cannot_start_implementation |
| IMPLEMENTATION | implementation_stop_keeps_state_and_human_boundary |
| BASIS | missing_review_basis_stops_before_review_and_final_approval |
| HUMAN | human_review_stops_final_approval_without_losing_artifacts |
| EARLY | early_stop_does_not_execute_correction_or_invent_human_decision |
| LIMIT | correction_limit_handoff_cannot_enter_final_approval |
| FINAL | final_gate_failures_never_become_successful_completion |
| ROUTE | final_human_route_retains_target_without_automatic_destination_execution |
| RETRY | human_authorized_retry_preserves_approval_evidence_and_correction_count |

## Specification §14との対応

| # | MVP条件 | 新規横断証拠 | 既存の詳細検証 |
|---|---|---|---|
| 1 | 呼び出し元からSpecification指定 | MAIN / ENTRY | workflow_entry |
| 2 | 有効なSpecification Approval確認 | MAIN / ENTRY | workflow_entry / approval_validation |
| 3 | Plan Draft生成 | MAIN / PLAN | plan_workflow / generate_implementation_plan |
| 4 | Human Plan承認・差し戻し | MAIN / PLAN | plan_workflow / request_plan_approval |
| 5 | Approved PlanからPrompt生成 | MAIN / PROMPT | plan_workflow / generate_codex_prompt |
| 6 | 承認範囲内のImplementation・Test | MAIN / IMPLEMENTATION | implementation_workflow / execute_implementation |
| 7 | 原則TDD | MAIN（Initial FAIL、Target/Full PASS） | implementation_workflow / execute_to_test_state_e2e |
| 8 | Evidence JSON構築・保存 | MAIN / BASIS | evidence_workflow / collect_implementation_evidence |
| 9 | Source Code・Git Diff取得 | MAIN（使い捨て実Git） | evidence_workflow / git_repository_state_provider |
| 10 | 必須8種類のReview Input提供 | MAIN / BASIS | prepare_review_input / review_workflow |
| 11 | Review Report生成 | MAIN / HUMAN | review_implementation / classify_review_result |
| 12 | 範囲内Correction・Re-Review | MAIN（新旧Evidence・Review lineage） | correction_cycle / review_workflow |
| 13 | Early Stop・上限でHumanへ返却 | EARLY / LIMIT | correction_continuation / review_workflow |
| 14 | Human Final Approval・差し戻し | MAIN / FINAL / ROUTE | final_approval_workflow / final_approval_routing |
| 15 | 承認BranchをdeveloperへMerge | MAIN（実Gitと承認commitの対応） | merge_preconditions / merge_execution / git_cli_merge_* |
| 16 | Merge正常完了後のみcompleted | MAIN / FINAL / RETRY（content verification含む） | phase_six_completion / final_approval_workflow |
| 17 | 有効な承認なしの工程通過禁止 | ENTRY / PROMPT / HUMAN / FINAL | approval_validation / workflow_entry / final_approval_workflow |
| 18 | State・History・Approval・Evidence追跡 | 全ケースをTarget 7 traceへ接続 | workflow_trace / state_transition_history |

既存検証名はtests/test_<名前>.pyを指す。Phase 1〜6の完成判定を本作業で作り直さず、既存契約と回帰検証を再利用する。

## 主要分岐の検証分担

- Approval不足・対象変更: ENTRY / PROMPT / FINALで次工程とtraceまで確認。hash、identity、不正Recordの詳細組合せは既存tests。
- Plan Revision / Cancellation: PLANで保存Artifactの保持、旧Approval不継承、新しいHuman承認、Promptへの接続を確認。
- Prompt生成失敗・実行不能: PROMPTでImplementationを実行しないことを確認。
- Technical Error / Critical Change: IMPLEMENTATIONで停止理由、actual State、Human待ちを確認。Retry可能性の全分類は既存tests。
- Evidence / Review Input不足: BASISでReviewおよびFinal Approvalを開始しないことを確認。
- Reviewの3結果: MAINはREVISION_REQUIREDからCorrectionを経てAPPROVED、HUMANはHUMAN_REVIEW_REQUIREDからHuman返却を確認。
- Correction: MAINで1回の実Correction、Re-Test、新Evidence、Re-Review、Final Approval、実Git Merge、traceまで検証。
- Early Stop: EARLYは既存Review由来の明示的Assessmentを供給。全EarlyStopCondition、根拠不明時の扱いは既存correction_continuation tests。
- Correction Limit: LIMITは既存Routing境界のcount=3 fixtureから、Handoff→Final Approval拒否→traceを検証。実際に3回Correctionしたと主張しない。回数の増加、履歴整合性、偽造countの拒否は既存correction_cycle / correction_continuation / review_workflow testsで検証する。
- Final Approval: FINAL / ROUTEで無判断、承認対象変更、4つの明示的Human差し戻し経路を確認。Human判断をReviewのAPPROVEDで代替しない。
- Merge: FINALでReadiness時と実行直前の不整合、実行失敗、content verification失敗を確認。MAINでは使い捨てRepositoryに対する実Merge結果を確認。
- Retry: RETRYで無承認の拒否、明示的Human authorization、Merge RetryとVerification-only Retryを確認。Approval / Evidence / Correction Countを維持。
- partial save: FINALでactual State=completedでもHistory保存失敗ならWorkflowとtraceは失敗、completed=Falseであることを確認。

## 責務・検証範囲の照合

- Production Code、Specification、Implementation Plan、UI、Flask、deployment、CI/CDは変更しない。
- 新しいState、UseCase、Approval Rule、generic orchestratorは追加しない。
- Human入力は明示的fixture。Review / Re-Reviewは既存の独立したReview処理とAI portを通し、Codexの自己申告で代替しない。
- live external AIは使用しない。AI/Codex出力とTest実行イベントは既存ports/fakesを使用するため、本番AIの品質評価や実接続試験ではない。
- MAINのGit操作はpytestが作成した一時Repositoryだけで実行する。作業Repositoryをcommit / merge / pushしない。
- Stop情報の不明値を推測で埋めない。既存Output、正式Artifact参照、actual Stateを保持する。Human操作・再開先が不明な場合、自動再開の許可を意味しない。
- Target 7のunknown保持と、MVP全体でHumanが停止状況を確認できることは別の監査項目。各経路のOutputと参照先も最終監査の対象とする。
- UI完成、deployment完成、production ready、製品全体完成の宣言は行わない。

## 実行結果

- 最初のMAIN: GREEN、1 passed。人工的なREDやProduction Code変更なし。
- 追加Retry testのRED: Verification-only Retry用fakeがMerge後のGit factsを反映していなかったtest setup不足。既存契約に合わせてtestのみ修正し、Merge / Verification Retryの2ケースがGREEN。
- Target 8全体、段階的回帰、最後のfull suite: 検証完了後に記録する。
- 3回連続Correctionの補助シナリオは長時間化のため中断し、最小の境界testと既存詳細検証の組合せへ変更した。3回連続実行の完走結果は主張しない。
- Humanの最終監査およびApplication Layer MVP COMPLETE宣言は、この実装結果確認後の別工程に残す。
