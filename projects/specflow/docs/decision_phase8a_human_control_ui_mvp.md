# Decisions

## Phase 8A Human Control UI MVP — Human Decisions

- 記録日：2026-10-01
- 決定者：Human（ユーザー）
- 根拠：Humanから提示された確定済みDecision 8A-03～8A-13
- 根拠Specification：[Specification v0.2.0](specification_phase8a_human_control_ui_mvp_v0.2.0.md)（Human Approved）
- Specification承認commit：`b268773c23ea18516dc2b35fad47629534ebf785`
- Phase 7 Application Layer MVP baseline：`68c827ec14c1e1a190878470a14187dfa0277140`
- 判定：Human Approved / Resolved

### 記録範囲

本書はHumanが確定した8A-03～8A-13を正式Artifactとして記録する。
各Decisionの本文はHuman提示文を保持する。
本書はImplementation Planの承認、実装開始の承認、runtime Approval Recordの生成を意味しない。

### 既存Decisionの参照

- 8A-01：Specification §4 / §15に記録済み（Resolved）。Project作成とWorkflow開始Gateを分離し、3項目の明示的意思確認を要求する。「現時点では特になし」は有効であり、blank / unknownとは区別する。
- 8A-02：Specification §9 / §15に記録済み（Resolved）。AI CandidateはHumanの明示的保存まで正式項目ではない。Human directとAI proposed then Human savedを区別し、保存を重要・優先・実装決定と同一視しない。

8A-01・8A-02の正本はSpecificationとし、既存本文を変更しない。

---

## Human Decision 8A-03 — Local Persistence

- 判定：Human Approved
- 状態：Resolved

Phase 8AではJSON + SQLiteのハイブリッド構成を採用する。

既存Application LayerのState、History、Approval、Evidence、Review、
Final Approval等は既存の保存方式を維持する。

新しいPhase 8A Human Control管理情報にはSQLiteを使用する。

対象例：

- Project管理
- Active / Sleeping
- ProjectとWorkflowの関連
- Project Constitution確認状態
- Humanの「次に考えていたこと」
- Reminder
- その他Human Control上の継続管理情報

SQLiteは既存Application Layer Artifactを置き換えない。

同じ正式情報を意図的に二重保存しない。

原則：

SQLiteは「どれを見るか」を管理する。
Application Layerは「それが正しいか」を検証する。
Humanは「どうするか」を決める。

---

## Human Decision 8A-04 — Work Continuity Responsibility Boundary

- 判定：Human Approved
- 状態：Resolved

「前回ここまで」はHumanが手入力する情報ではない。

既存Application Layerの正式Artifact、State、History、Trace等から、
現在到達している事実として再構成する。

「次に考えていたこと」はHumanの意図であり、SQLiteへ保存する。

再開時にはその過去のHuman Intentを表示するが、
自動実行してはならない。

過去のHuman Intentは現在のHumanの判断を拘束しない。

原則：

Humanは覚えておく必要はない。
SpecFlowが記録し、必要な時にHumanへ戻す。
ただし、記録された過去の意図は現在のHumanの決定を拘束しない。

---

## Human Decision 8A-05 — Constitution Change and Ongoing Workflow

- 判定：Human Approved
- 状態：Resolved

Project Constitutionのいずれかの項目が変更された場合、
その項目はHuman reconfirmation pendingへ戻す。

3項目すべてがHumanにより確認されるまで、
New Workflow Start Gateを閉じる。

進行中Workflowが存在する場合、
Constitution変更だけを理由にApplication Layer Stateを
自動変更・自動停止・自動継続してはならない。

Human Decisionを提示し、

- 変更後Constitution
- 現在のWorkflow
- 必要な判断材料

をHumanへ返す。

Humanが継続・停止・必要な再検討等を判断する。

AIはConstitution変更の重要性を勝手に決定しない。

---

## Human Decision 8A-06 — Project / Workflow Identity and Specification Linkage

- 判定：Human Approved
- 状態：Resolved

ProjectとWorkflowには、
Human-facing nameとは別にimmutable UUIDを持たせる。

名前変更によってidentityは変化しない。

Workflowは必ず一つのProjectに所属する。

SQLiteにはWorkflow起点を特定するため、少なくとも以下の関連情報を持つ。

- Specification reference / path
- Specification content hash
- Approval ID association

ただしSQLiteはApproval Authorityではなくindexである。

Workflow開始・再開時には、
既存Application Layerが実際のSpecification、hash、Approval Record等を検証する。

missing / mismatch / non-unique等により
安全かつ一意に判断できない場合は推測せずSTOPし、
Humanへ戻す。

---

## Human Decision 8A-07 — 「今日はここまで」の意味

- 判定：Human Approved
- 状態：Resolved

［今日はここまで］はHuman work sessionの終了であり、
Workflow cancellationではない。

操作実行中の場合は強制終了しない。

現在実行中の不可分な操作を安全な境界まで完了し、
結果を記録した後、新しい操作を開始しない。

その後End Work画面で、

- 到達地点
- 次回再開地点
- Humanの「次に考えていたこと」

を扱えるようにする。

Humanは、

- 進行中のままにする
- 寝かせる

を選択できる。

［今日はここまで］そのものでは、
正式Application Layer StateやActive/Sleepingを
自動変更しない。

Humanの中断は正常系であり、Errorではない。

---

## Human Decision 8A-08 — Resume

- 判定：Human Approved
- 状態：Resolved

Resumeは「SQLiteに保存されたState値を戻す」処理ではない。

Project UUID / Workflow UUIDで対象を特定し、
必要な正式Application Layer Artifactを再検証して、
現在の安全なResume Pointを再構成する。

SQLiteが保持するのは、

- どのProject / Workflowか
- 正式Artifactをどこで確認するか
- Humanの過去のIntent

等である。

SQLiteを正式State Authorityにしない。

Humanの過去Intentは再表示するだけで、
自動実行しない。

missing / mismatch / non-unique等により
一意で安全なResume Pointを再構成できない場合は、
推測しない。

何が未解決か、
なぜ再開できないか、
Humanに何を判断してもらう必要があるかを提示してSTOPする。

Activeからの短時間再開でもSleepingからの長期間再開でも、
同じ原則を適用する。

---

## Human Decision 8A-09 — Reminder Project / Workflow Association

- 判定：Human Approved
- 状態：Resolved

Reminderは必ず一つのProjectに所属する。

Project UUIDとの関連付けは必須。

Workflow UUIDとの関連付けは任意。

Workflowとの関連は、

「そのReminderに気づいた時の由来・文脈」

を示すだけであり、

- 実装先
- 優先順位
- 重要度
- Workflow再開指示

を意味しない。

現在のWorkflow作業中にReminderを登録する場合、
SpecFlowは現在Workflowを関連候補として提示してよい。

ただし自動確定してはならない。

Humanが関連を確認または解除できること。

---

## Human Decision 8A-10 — Existing Project Registration

- 判定：Human Approved
- 状態：Resolved

Phase 8A導入以前から存在する開発物を、
自動的にPhase 8A Projectへ取り込まない。

Humanが、

「この既存開発物を、これからSpecFlowで管理・発展させる」

と判断した時点で、
明示的に既存Projectとして登録する。

登録時にPhase 8A用Project identityを作成する。

登録以前の開発履歴や過去Workflowを、
Phase 8A形式へ推測・自動移行しない。

過去の履歴は既存Git / Artifactにそのまま保持する。

Phase 8Aへの登録後に開始する新しいWorkflowから、
Phase 8A Human Control管理を適用する。

想定される実利用例：

Phase 8A完成
  ↓
Humanが既存SpecFlowをPhase 8A Projectとして登録
  ↓
Phase 8Bを新しいWorkflowとして開始

---

## Human Decision 8A-11 — SQLite / Evidence / Git Responsibility Boundary

- 判定：Human Approved
- 状態：Resolved

SQLite、Evidence、Gitの責任を明確に分離する。

SQLite：
Human Control上の継続・管理情報。

Evidence：
Application Layerにおいて
「実際に何が起きたか」を検証する正式記録。

Git：
正式な開発成果と変更履歴。

Phase 7でGit管理対象としていないEvidenceを、
Phase 8Aを理由として新たにGit管理対象へ変更しない。

Evidenceが正式であることと、
Gitへcommitすることは同義ではない。

Phase 8AではPhase 7 Evidence保存方式を再設計しない。

---

## Human Decision 8A-12 — AI Reminder Candidate Scope

- 判定：Human Approved
- 状態：Resolved

Phase 8Aでは、

AI CandidateとHuman Approvalの境界

は維持する。

ただし、会話・作業内容等をAIが自動解析し、
Reminder Candidateを自動発見・自動生成する機能は
Phase 8A MVPには含めない。

Phase 8AではHumanが自分で
［思い出しておく］を登録できればよい。

AIによる積極的なCandidate発見・生成は
Phase 8B以降へ送る。

Candidateを扱える設計上の境界は維持するが、
8Aで高度なAI Candidate生成機構を作らない。

目的はサグラダ・ファミリア化を避け、
Phase 8A MVPを完成させることである。

---

## Human Decision 8A-13 — Final Approval差し戻し境界

- 記録日：2026-10-01
- 判定：Human Approved（選択肢A）
- 状態：Resolved

Phase 8Aでは、Final Approvalからの差し戻しについて、
既存Application Layerで定義済みの返却契約までを接続してください。

HumanがPlan Revision等への差し戻しを選択した場合、
Phase 8Aは既存契約で確定している判断・返却先・不足情報を表示し、
Human Handoffしてください。

既存Application Layerで未定義の状態遷移や
差し戻し後の処理を、Phase 8Aが推測して自動実行してはいけません。

この安全なSTOP / Human Handoffを、
Phase 8A MVPの正常なCompletion範囲として認めます。

差し戻し後の完全な再実行経路を実現するために、
Phase 7 Application LayerをPhase 8Aで拡張しないでください。

---

## Human Plan Approval — Phase 8A Implementation Plan v0.1.0-draft

- 記録日：2026-10-01
- 決定者：Human（ユーザー）
- 判定：Human Approved
- 対象：[Implementation Plan v0.1.0-draft](drafts/phase8a_human_control_ui_mvp_implementation_plan_v0.1.0-draft.md)
- 承認対象ファイルのSHA-256：`6f649945ff3601f40ed663b10d4f50e8d557d0dd2bef0b798896095c7fa320d9`

HumanはT6のMVP化修正を含むPlanを承認し、Phase 8A実装の正式基準とした。
End Workは操作完了・UI復帰後の明示選択とし、実行中Use Caseを強制終了せず、job管理・thread管理・並行受付機構を新設しない。
正式事実から到達地点を再構成し、Human IntentをSQLiteへ保存し、Active / Sleepingは別のHuman判断とする。Decision 8A-07は変更しない。

承認対象本文とhashを保持するため、Planファイル内の作成時のDraft / Human Approval Pending表記は変更しない。現在のHuman承認状態は本記録で示す。これはユーザーの明示承認の記録であり、AIが承認を生成したものではない。

今回の実行許可はT1のTDD実装・対象テスト・関連Regression・Completion確認まで。T1完了時点でSTOPし、T2はHuman確認前に開始しない。新たなHuman判断が必要ならHUMAN_DECISION_REQUIREDとして停止する。commit / pushは行わない。
