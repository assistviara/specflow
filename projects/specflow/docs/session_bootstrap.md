SpecFlowプロジェクトを再開します。

添付した以下の3文書を、必ずこの順番で読み込んでください。

1. SpecFlow_Constitution_v1.0.md
2. constitution.md
3. SESSION_CONTEXT.md

## 起動手順

読み込み後は、以下の手順で進めてください。

### Step 1

SpecFlow_Constitution_v1.0.mdを最上位文書として理解してください。

Constitutionに反する提案・設計・実装は行わないでください。

### Step 2

constitution.mdを運用ルールとして理解してください。

Implementation Pipelineでは、
Constitutionとconstitution.mdの両方に従ってください。

### Step 3

SESSION_CONTEXT.mdから、

- 現在の開発フェーズ
- 完了済み事項
- 現在のTask
- 制約事項

を復元してください。

### Step 4

上記3文書を統合し、

以下を簡潔に要約してください。

- プロジェクト理念
- 開発ルール
- 現在地
- 次工程

### Step 5

要約内容についてHumanへ確認を求めてください。

Humanの承認があるまで、

- 新しい設計
- 実装提案
- 仕様変更

は行わないでください。

承認後、

SESSION_CONTEXT.mdに記載されたCurrent Taskから開発を再開してください。

---

## 注意事項

- Constitutionを最優先としてください。
- Specificationを唯一の正本（Single Source of Truth）として扱ってください。
- 推測による仕様変更は禁止です。
- 不明点はHumanへ確認してください。
- 日本語を標準言語として議論してください。
- SpecFlowの開発プロセス（Specification → Implementation Plan → Decision → Implementation → Review）を維持してください。