# Phase 8A T2 / T3 実装照合記録

- 実装前baseline：`developer` / `736a8ce`（`origin/developer`一致、working tree clean）
- Specification承認：`b268773`
- Human Decisions / Implementation Plan承認：`a96d27a`
- 根拠：[承認済みPlan T2 / T3](../projects/specflow/docs/drafts/phase8a_human_control_ui_mvp_implementation_plan_v0.1.0-draft.md)、[Human Decisions](../projects/specflow/docs/decision_phase8a_human_control_ui_mvp.md)
- 本記録は実装者の照合結果であり、独立ReviewやHuman Approvalではない。

## T2 — Project / Constitution / Existing registration

根拠はR-01、Specification §3–4、8A-01 / 05 / 10。

`ProjectService`を追加。未完成Projectの作成、3項目の保存・明示確認・Constitution Gate、変更項目だけのreconfirmation、既存開発物の明示登録を実装した。確認対象の現在値を照合し、古い内容や空欄への確認を拒否する。「現時点では特になし」の明示確認は有効。

Constitution変更時は既存Current Stateを読み取り、進行中または状態不明のWorkflowと正式参照、変更後Constitution、Human判断が必要な理由を返す。State変更・停止・継続は実行しない。これはT8用の情報返却であり、今回画面は実装しない。

既存登録はHumanの明示操作と新UUIDに限定し、参照先を探索・変更・移行しない。Project Creation GateとNew Workflow Start Gateは別。Constitution Gateの許可はSpecification Approvalや実行許可ではなく、T4の接続は未実装。

### TDD

1. `tests/test_human_control_projects.py`を先に追加。
2. Initial FAIL：`human_control.projects`未実装による`ModuleNotFoundError`、collection error 1件。assertionでのFAILではない。
3. 最小実装後、対象10件＋T1 10件：**20 passed**。
4. Phase 7関連Regression：**66 passed**。

### Completion

| 条件 | 判定 | 確認 |
| --- | --- | --- |
| 未完成Project保存と開始Gate分離 | PASS | 3項目未確認ではGate不許可、全項目明示確認で許可 |
| blank / unknownと明示的「特になし」の区別 | PASS | None / 空文字 / 空白の確認拒否、明示内容確認を検証 |
| 変更項目だけreconfirmation | PASS | 再読込後も他項目の確認を保持 |
| 進行中WorkflowのHuman返却 | PASS | Workflow参照と変更後内容を返し、正式State bytes不変 |
| 明示登録・migrationなし | PASS | 非明示操作拒否、新UUID、過去Workflowなし、旧Artifact不変 |
| 保存失敗 | PASS | 書込lock例外、既存確認済み内容を保持 |

T2完了後、ユーザーの許可どおりT3へ進んだ。

## T3 — Active / Sleeping

根拠はR-03、Specification §6 / §8.1 / §8.6。

Humanの明示操作に限定したActive切替・Sleeping操作、全Sleeping一覧、最近Sleeping最大3件を実装した。新規作成・閲覧はActive化しない。Activeを持たないProjectはSleeping一覧に含めるが、明示的なSleep日時がなければ最近Sleepingには含めない。

Active切替は一つのtransactionで旧Activeを解除し対象をActiveにする。DBのpartial unique indexでもActive最大1件を保護する。変更途中に失敗してもrollbackし、旧Activeを失わない。

最近SleepingはHumanの明示的な［寝かせる］操作の最終日時をUTCで保存して降順最大3件とする。名称・Constitution更新や別ProjectのActive化によって、［寝かせる］日時を新しく捏造しない。現在ActiveのProjectは最近Sleepingから除く。同時刻の並びはUUIDで安定化し、重要度・優先順位と解釈しない。

### TDD

1. `tests/test_human_control_focus.py`を先に追加。
2. Initial FAIL：未実装のFocus APIによる**10 failed**（AttributeError）。
3. 最小実装後、対象10件＋T1/T2 20件：**30 passed**。
4. Phase 7関連Regressionを再実行：**66 passed**。

### Completion

| 条件 | 判定 | 確認 |
| --- | --- | --- |
| Human明示切替・Active最大1件 | PASS | 未確認操作拒否、切替、DB一意制約 |
| 保存失敗・再読込 | PASS | 切替途中のDB trigger失敗で旧Active保持、別接続で再読込 |
| 最近Sleeping最大3件 | PASS | 5件から降順3件、編集日時非使用、Active除外、再Sleep日時更新 |
| 正式情報保持 | PASS | State / History / Approval / Evidence bytes不変、Workflow identity・参照保持 |
| FocusとWorkflow Stateの分離 | PASS | Sleepingと再Active化でWorkflowを実行・取消しない |

## 検証コマンドと範囲

対象テストは次のコマンドで実行した。

```text
python -m pytest -q -p no:cacheprovider tests/test_human_control_projects.py tests/test_human_control_persistence.py
python -m pytest -q -p no:cacheprovider tests/test_human_control_focus.py tests/test_human_control_projects.py tests/test_human_control_persistence.py
```

Phase 7関連Regressionは同じpytestオプションで次の11ファイルを実行した。

```text
tests/test_current_state_repository.py
tests/test_state_transition.py
tests/test_state_transition_history.py
tests/test_approval_record.py
tests/test_approval_record_service.py
tests/test_approval_validation.py
tests/test_json_approval_record_repository.py
tests/test_json_implementation_evidence_repository.py
tests/test_json_test_execution_record_repository.py
tests/test_workflow_entry.py
tests/test_core_dependency_direction.py
```

Full Regression・UIテストは今回未実施。実DBはpytest一時領域のみ。運用DBや旧データのmigrationは実行していない。

## 保存形式と境界

新規SQLite schemaにConstitution、既存登録参照、Focusの管理表を追加した。最終schema versionは3。既存schema version 1 / 2を自動更新せず、不一致として明示的に拒否する。旧DBの内容を消去・移行・置換する処理は追加していない。

Phase 7コード・契約、Specification / Decisions / Planは変更していない。SQLiteは正式State / Approval Authorityではない。Phase 8B creep、新たなHUMAN_DECISION_REQUIRED、job / thread / 並行受付機構追加はない。

T3でSTOP。T4未着手。commit / pushなし。
