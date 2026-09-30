# Phase 8A Human Control UI MVP
## Specification v0.2.0

**Status: Human Approved**

## 1. Purpose

Phase 8Aの目的は、既存のSpecFlow Application Layerを、単一のHumanがブラウザから安全かつ直感的に利用できる **Human Control UI** として提供することである。

HumanはApplication Layer内部の工程、State、Artifact、処理順序を記憶し、逐一操作する作業者であってはならない。

Humanの役割は、**Humanの権限を必要とする事項について意思決定すること**である。

Application LayerまたはAIへ委任済みであり、Specificationその他の正式Artifactから一意に決定可能な処理については、単なる工程進行のための不要なHuman操作を要求してはならない。

一方、承認、選択、曖昧さ、例外、未委譲の判断、重要な変更その他Humanの権限を必要とする事項については、AIが推測、補完、代替せず、Humanへ判断を返さなければならない。

Phase 8Aは、既存Application LayerのSpecification FirstおよびHuman Approval Boundaryを継承する。

## 2. Scope

Phase 8Aは、既存Application Layerの外側に、次の上位構造を追加する。

Project
  ↓
Workflow
  ↓
Existing Application Layer

### 2.1 Project

Project（プロジェクト）は、Humanが継続的に育てていく一つの開発対象である。

例えば、

- 独自アセスメントアプリ
- 飲食店・弱シグナル分析アプリ
- 高齢者行動支援アプリ

等が一つのProjectとなる。

Projectは複数の機能を持つことができる。

例えば「飲食店・弱シグナル分析アプリ」という一つのProjectが、

飲食店・弱シグナル分析アプリ
├─ 線形回帰
├─ 非線形回帰
├─ シナリオ分析
├─ モンテカルロ・シミュレーション
├─ SHAP
└─ 弱シグナル分析

等の複数機能を持つことを妨げない。

### 2.2 Workflow

Workflow（ワークフロー）は、**Projectに対して一回のSpecificationを起点として行う変更・追加・修正等の開発単位**である。

WorkflowとProjectが持つ「機能」は同義ではない。

一つのWorkflowによって、一つの機能だけが追加・変更される場合もあれば、複数機能にまたがる変更が行われる場合もある。

例えば、

Project：飲食店・弱シグナル分析アプリ

Workflow #001
線形回帰機能を追加する

Workflow #002
非線形モデルとの比較機能を追加する

Workflow #003
モンテカルロ分析を追加する

Workflow #004
SHAPによる説明機能を追加する

Workflow #005
弱シグナル検出機能を追加する

Workflow #006
弱シグナルをシナリオ分析へ渡し、
モンテカルロ結果と組み合わせて表示する

といった構造を取ることができる。

したがって、

**Project = 育てていく開発対象全体**
**Feature = Projectが提供する機能**
**Workflow = 今回Projectに加える変更の開発単位**

として区別する。

### 2.3 Existing Application Layer

Phase 8AでいうApplication Layerとは、対象Project側のApplication Layerを意味するものではない。

Phase 7までに完成した**SpecFlow自身のApplication Layer**を意味する。

既存Application Layerは、Specification ApprovalからImplementation Plan、Implementation、TDD、Evidence、Review、Correction、Final Approval、Merge、`completed`までを一連のWorkflowとして制御する。

Phase 8AはこのApplication Layerを再実装しない。

## 3. Project Constitution

各Projectは、次の3項目を基本方針として持つ。

### 3.1 目的

Projectが何のために存在するか。

### 3.2 大切にすること

Projectを育てていく際に継続して尊重する判断原則。

### 3.3 守ること

機能追加や変更が行われても越えてはならない制約。

Project Constitutionと個別WorkflowのSpecificationを混同してはならない。

複数Workflowを通じて継続して守るべき内容はProject Constitutionに属する。

特定の変更・追加・修正について定める内容はWorkflowのSpecificationに属する。

Phase 8Aでは、AIによるProject Constitutionの自動作成を行わない。

Humanが外部の生成AI等と対話しながらProject Constitutionを検討することは妨げない。

SpecFlowは、**Humanが決定したProject Constitutionを保持し、開発中に見失わないようにする**役割を担う。

## 4. Project Creation / Workflow Gate

Project Constitutionが未完成でも、Projectを作成できなければならない。

アイデア段階、検討中、まだ十分に言語化されていないProjectの存在を禁止してはならない。

つまり、

> **プロジェクトの卵を殺さない。**

一方、Projectを実際に育てるためにWorkflowを開始する前には、

- 目的
- 大切にすること
- 守ること

について、Humanの明示的な意思が確認されていなければならない。

「現時点では特になし」等も、Humanが検討した上で明示的に決定した結果であれば有効とする。

空欄等、Humanが検討したかどうか確認できない状態を、AIまたはシステムがHuman Decision済みと推測してはならない。

したがって、

> **Projectは基本方針が未完成でも作成できる。**
>
> **ただしProject ConstitutionについてHumanの意思が確認されるまでWorkflowには進めない。**

これを**Workflow開始Gate**とする。

## 5. Human Control Principles

Phase 8Aは、以下の原則を守らなければならない。

### 5.1 Humanは作業者ではなく意思決定者

HumanにApplication Layer内部の工程を逐一操作させることを目的としない。

### 5.2 「できる」と「決めてよい」を区別する

AIまたはシステムに技術的な実行能力があることを、その事項をAIが決定してよい根拠としてはならない。

### 5.3 Delegated Work

Humanから既に委任され、正式Artifactから一意に処理を決定できる場合、単なる工程進行のための不要なHuman操作を要求してはならない。

### 5.4 Human Decision

Human Decisionが必要な場合には、少なくとも、

- 何が起きているか
- なぜHuman Decisionが必要なのか
- 判断に必要な情報
- Humanが選択可能な内容

を提示しなければならない。

必要な情報が不足している場合、その不足状態そのものをHumanへ提示する。

AIが推測によって不足を埋めてはならない。

## 6. Project Focus

Projectの作業上の位置づけとして、

**進行中（Active）**
**寝かせる（Sleeping）**

を扱う。

同時に進行中にできるProjectは最大1件とする。

別Projectを進行中にする場合、それまで進行中だったProjectは寝かせる。

この切替はHumanが明示的に決定する。

AIは最終更新日時、利用頻度、推測された重要性等から、進行中Projectを自動決定してはならない。

進行中／寝かせるは、Application LayerのWorkflow Stateとは別概念である。

Projectを寝かせても、

- Workflow State
- History
- Specification
- Human Decision
- Approval
- Evidence
- その他正式Artifact

を失ってはならない。

寝かせることは、取消、失敗、削除を意味しない。

## 7. Recognition over Recall

Phase 8Aは、Humanが過去の作業内容を記憶していることを前提としてはならない。

必要な場面で、

- 前回ここまで
- 次に考えていたこと
- 現在Humanの判断が必要なこと
- 現在の文脈に関連する過去のHumanの意図

を再提示できなければならない。

すべての情報を常時表示する必要はない。

**必要な情報を、必要な時にHumanへ戻すこと**を目的とする。

## 8. UI Requirements

Phase 8Aは次の8画面を対象とする。

### 8.1 起動画面

少なくとも、

- あなたの判断が必要
- 現在進行中
- 最近寝かせたプロジェクト
- 思い出しておくこと
- ［＋ 新しいプロジェクト］

を提供する。

Human Decisionが存在する場合は認識しやすい位置に表示する。

最近寝かせたProjectは、Humanが最後に［寝かせる］を実行した日時を基準として、新しいものから最大3件表示する。

また、

**［寝かせているプロジェクトをすべて見る］**

を提供する。

### 8.2 新しいProject作成画面

少なくとも、

- Project名
- 目的
- 大切にすること
- 守ること

を入力できる。

Project Constitutionの3項目が未完成でもProjectを作成できる。

Workflowが存在しない場合、

> まだ作業はありません

等、その状態をHumanが理解できる表示を行い、

**［＋ 最初の作業を始める］**

を提供する。

ただしWorkflow開始Gateを満たしていない場合、その理由および未確認項目をHumanへ提示する。

### 8.3 Project開発画面

少なくとも、

- Project名
- 進行中／寝かせる
- Human Decisionの有無
- 現在のWorkflow
- 前回ここまで
- 次に考えていたこと
- Project Constitution
- Workflow History
- 新しいWorkflowを始める入口

を確認できる。

**［続きから始める］**

と、

**［＋ 新しい作業を始める］**

を明確に区別する。

Humanが既存Workflowの続きを行うつもりだったにもかかわらず、誤って新しいWorkflowを作成しやすいUIとしてはならない。

### 8.4 Workflow作業画面

Humanが［続きから始める］を選択した場合、Human自身にApplication Layer内部の再開地点を記憶または選択させてはならない。

保存された正式情報から現在地点を判断し、Humanに必要な内容を提示する。

状況に応じて、

- Specification確認
- Plan Approval
- Implementation状況
- Review結果
- Human Decision
- Final Approval

等を表示する。

Human Approvalなしに承認工程を通過してはならないという既存Application Layerの境界を維持する。

Humanへ委任確認を繰り返す必要がなく、一意に決定可能な処理については、不必要な［次へ］操作を要求しない。

### 8.5 作業終了画面

Humanが［今日はここまで］を選択した場合、

**今回ここまで進んだ内容**

および、

**次回再開するとき**

を確認できなければならない。

その後、

**［進行中のままにする］**
**［寝かせる］**

をHumanが選択できる。

この選択によってApplication Layerの正式Workflow Stateを変更してはならない。

### 8.6 寝かせたProject一覧画面

寝かせているProjectを一覧表示できる。

HumanはProjectを開き、内容を確認できる。

Humanの明示的操作によって、そのProjectを進行中へ戻すことができる。

その場合、それまで進行中だったProjectは寝かせる。

### 8.7 Human判断画面

Human Decisionが必要な場合の共通UIを提供する。

少なくとも、

- 何が起きたか
- なぜHumanの判断が必要か
- 判断材料
- 選択可能なDecision

を表示する。

AIはHuman Decisionを生成、推測、補完、代替してはならない。

HumanがDecisionを行った後、そのDecisionに対応するWorkflowへ戻る。

### 8.8 思い出しておくこと画面

「思い出しておくこと」を独立した画面で管理する。

各項目はProjectとの関連を持つことができる。

項目の性質として、少なくとも、

- 不具合
- 改善案
- 新機能候補
- 将来構想
- 要検討

等を区別できる設計とする。

必要に応じて、

- 会社で確認
- 自宅で可能

等の実行場所情報を持たせることができる。

現在のProjectと明確な関連を持つ項目が存在する場合、

> 関連する「思い出しておくこと」があります

等の形で適切な文脈に再提示できる。

AIは、これらの項目の戦略的優先順位をHumanに代わって決定してはならない。

## 9. AI Candidate Boundary

AIは作業・対話等から、

**「思い出しておくこと」の候補（Candidate）**

をHumanへ提示してよい。

例えば、

> あとで思い出しておく候補があります。
> 「会社PCで性別欄の不具合を再現確認する」
>
> ［残しておく］［残さない］

のように提示できる。

ただし、AI Candidateは正式な「思い出しておくこと」ではない。

Humanが［残しておく］等の明示的なDecisionを行った場合にのみ正式項目として保存する。

Humanが保存しなかったCandidateを正式項目として蓄積してはならない。

正式項目について、

**Human直接登録**

と、

**AI提案 → Human保存**

の由来を区別できなければならない。

また、

**保存された＝重要**
**保存された＝優先**
**保存された＝実装決定**

と解釈してはならない。

Humanは時間の経過、新しい情報、考え直し等によって、保存済み項目を改めて評価できる。

AIは「昨日重要だと考えた」という事実だけを理由として、その重要性が現在も維持されていると推測してはならない。

## 10. Application Layer Integration

Phase 8Aは、既存Application Layerの正式情報をUI独自の情報へ置き換えてはならない。

特に、

- Current State
- State Transition History
- Human Approval Record
- Implementation Evidence
- Review Result
- Git Operation Result

を混同してはならない。

UIではHumanに理解しやすい日本語へ変換して表示してよい。

ただし、表示上の簡略化によって正式情報そのものの意味を変更してはならない。

## 11. Data / Git Boundary

Gitは、**正式な開発成果およびその履歴を管理するために使用する。**

例えば、

- Source Code
- Specification
- Implementation Plan
- Tests
- 正式Evidence
- その他Git管理対象Artifact

を扱う。

一方、

- Projectの個人用管理情報
- 進行中／寝かせる
- 前回ここまで
- 次に考えていたこと
- 思い出しておくこと
- Local Settings
- Logs
- Temporary Data

等を、PC間同期だけを目的としてGit管理対象へ追加してはならない。

`.gitignore` 等によってGit管理から除外すべきデータを、クラウド同期の代替としてGitへ追加しない。

Phase 8Aでは、

**自宅PCと会社PC間のSpecFlowローカルデータ完全同期**

を実装しない。

Gitに汎用クラウドストレージの役割を負わせない。

会社環境でしか実行できない確認等は、「思い出しておくこと」等によってHumanが認識できるようにすることができる。

必要な正式な開発成果はGit管理へ戻すことができる。

## 12. Stop / Human Handoff

次の場合、AIまたはApplication Layerが独自判断で先へ進んではならない。

Human Approvalが必要な場合、Human Decisionが必要な場合、正式Artifactから一意に処理を決定できない場合、必要情報が欠落している場合、安全な再開地点を確定できない場合、既存Application LayerがHuman HandoffまたはEarly Stopを要求した場合。

Phase 8Aはこの状態を隠してはならない。

Humanが、

**何が起きているか**
**何が分からないのか**
**何を決める必要があるのか**

を理解できる形で提示する。

## 13. Out of Scope

Phase 8Aでは、以下を実装対象としない。

- Multi-user
- Login / Account
- Role / Permission管理
- Concurrent Editing
- Cloud Operation
- PC間のローカルデータ完全同期
- Notification System
- 高度なDashboard / Analytics
- 市場調査機能そのもの
- 弱シグナル分析機能そのもの
- AIによるProject Constitution自動作成
- AIによる高度なConstitution整合性判定
- AIによるProjectの自動切替
- AIによるHuman Decisionの代替
- AIによる「思い出しておくこと」の戦略的優先順位決定
- 自然言語対話からSpecification Draftを作成するPhase 8B機能

これら将来機能の完成を、Phase 8AのCompletion条件としてはならない。

## 14. Completion Conditions

Phase 8A MVPは、少なくとも以下を満たさなければならない。

HumanがブラウザからProjectを作成できる。

Project Constitutionが未完成でもProjectを保存できる。

Project ConstitutionについてHumanの意思が確認されるまでWorkflowを開始できない。

一つのProjectが複数のWorkflowを持つことができる。

WorkflowとProjectのFeatureを同一概念として扱わない。

一つのWorkflowが必要に応じて複数Featureへ変更を加えることを妨げない。

Humanが一つのProjectを進行中として扱い、他のProjectを寝かせることができる。

寝かせたProjectを情報を失わず再開できる。

Project内の複数Workflowを区別できる。

既存Specificationを起点として既存Application Layerへ接続できる。

HumanがApplication Layer内部の工程を記憶しなくても、［続きから始める］から適切な現在地点へ戻れる。

Human Decisionが必要な場合はHumanへ戻る。

委任済みで一意に決定可能な処理では、不要なHuman操作を要求しない。

「思い出しておくこと」を保存、分類、再提示できる。

AI CandidateはHumanの明示的保存Decisionなしに正式項目にならない。

Git管理対象とローカル作業データを分離できる。

既存Application LayerのHuman Approval Boundary、State、History、Approval、Evidence、Review、Merge等の意味を破壊しない。

Phase 8Aに必要なTestsが成功する。

既存Application LayerのRegression Testsが成功する。

## 15. Human Decisions

### Human Decision 8A-01 — Project Constitution / Workflow Gate

**Resolved**

ProjectはProject Constitutionが未完成でも作成可能とする。

ただし、

- 目的
- 大切にすること
- 守ること

についてHumanの明示的意思が確認されるまでWorkflowを開始してはならない。

「現時点では特になし」はHumanが明示的に決定した場合に有効とする。

### Human Decision 8A-02 — AI Candidate

**Resolved**

AIは「思い出しておくこと」のCandidateをHumanへ提示してよい。

AI Candidateは正式項目ではない。

Humanが明示的に保存を決定した場合にのみ正式項目となる。

AIは保存Decisionおよび優先順位DecisionをHumanに代わって行わない。

### Unresolved Human Decisions

**現時点：0件**

## 16. Phase 8B Connection Boundary

Phase 8Aは、基本方針がまだ完成していないProjectの存在を許容する。

この領域は、将来のPhase 8BにおけるSpecification Dialogueの接続点となり得る。

アイデア
   ↓
Projectの卵
   ↓
考える
残す
寝かせる
   ↓
【Phase 8B】
Human ↔ AI Dialogue
   ↓
目的
大切にすること
守ること
   ↓
Human Decision
   ↓
何を作るかを整理
   ↓
Specification Draft
   ↓
Human Approval
   ↓
──────────────
 Workflow開始Gate
──────────────
   ↓
【Phase 8A】
Human Control UI
   ↓
Existing Application Layer
   ↓
Plan
Implementation
Test
Evidence
Review
Final Approval
Merge
Completed

Phase 8Bが将来追加されても、Phase 8Aおよび既存Application LayerのHuman Approval Boundaryを置き換えてはならない。

AIはHumanが考えるための候補、質問、整理材料を提示できる。

しかし、

> **AIが提案したこと**

と、

> **Humanが自分の意思として決定したこと**

を混同してはならない。
