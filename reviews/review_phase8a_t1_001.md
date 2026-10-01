# Phase 8A T1 実装照合記録

- 記録日：2026-10-01
- 実装前baseline：`developer` / `b268773`
- 根拠：[承認済みPlan T1](../projects/specflow/docs/drafts/phase8a_human_control_ui_mvp_implementation_plan_v0.1.0-draft.md)、[Human Decisions / Plan Approval](../projects/specflow/docs/decision_phase8a_human_control_ui_mvp.md)
- 範囲：T1 Human Control persistence / identityのみ。
- 本記録は実装者による照合であり、独立ReviewやHuman Approvalを代替しない。

## 実装

`human_control/models.py`にimmutableなProject / Workflow UUIDと参照情報、`sqlite_repository.py`にSQLite index保存を追加した。DBパスは呼び出し元指定。新規DB初期化と既存DBの読込を分離し、既存ファイルの上書き・自動migrationをしない。

保存するのはProject名・UUID、Workflow名・UUID・所属Project、Specification path / hash / Approval ID association、State / History path、Artifact参照である。正式State・Approval・Evidenceの内容は保存せず、読み書き・実行も行わない。重複identityを置換せず、外部キーで存在しないProjectへの所属を拒否する。SQLiteの例外を隠さず、失敗transactionをrollbackし接続を閉じる。

T2のProject作成Use Case / Constitution Gate、T3のFocus、T4以降の実行adapter・再開、Reminder、UIは未実装。今回のProject保存APIはT1の低レベル永続化であり、Workflow開始許可ではない。運用DBは作成していない。SQLite DBはpytestの一時領域でのみ検証した。

## TDD / 検証

1. 新規テストを先に追加。
2. Initial FAIL：`python -m pytest -q tests/test_human_control_persistence.py`。未実装の`human_control`による`ModuleNotFoundError`でcollection error 1件。振る舞いassertionでのFAILではない。
3. 最小実装後、通常権限ではpytest一時フォルダへのアクセス拒否（2 passed / 8 setup errors）。これは実装テストの成功とは扱わない。
4. 権限承認後：`python -m pytest -q -p no:cacheprovider tests/test_human_control_persistence.py` → **10 passed**。
5. 関連Regression：下記11ファイルを同じpytestオプションで実行 → **66 passed**。

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

Full RegressionとUI検証は今回未実施。T1で変更した責務に関連するRegressionを実施した。

## T1 Completion Conditions

| 条件 | 判定 | 証拠 |
| --- | --- | --- |
| rename後もidentity保持 | PASS | Project / Workflow rename後、DB再読込とfrozen modelを検証 |
| 複数Workflowの関連分離 | PASS | 2 Project / 3 Workflow、同名、Artifact参照の独立保存を検証 |
| index変更で承認やStateが成立しない | PASS | 実State / Approvalファイル不変、missing Artifact非生成、既存Approval Validationによる未承認拒否 |
| 永続化失敗を検出 | PASS | SQLite lockによる書込失敗の例外と既存値保持を検証 |
| 旧データmigrationなし | PASS | 既存JSON / SQLiteへの初期化拒否、foreign DB読込拒否とbytes不変 |

Phase 7コード・契約の変更なし。Phase 8B creepなし。新たなHUMAN_DECISION_REQUIREDなし。T1でSTOPし、T2はHuman確認待ち。commit / pushなし。
