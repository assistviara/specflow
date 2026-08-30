SpecFlowプロジェクトを再開します。

新しいChatGPT / Codexセッションでは、以下を必ずこの順番で確認してください。

1. `SpecFlow_Constitution_v1.0.md`
2. `constitution/constitution.md`
3. `constitution/principles.md`
4. `constitution/implementation_guidelines.md`
5. `SESSION_CONTEXT.md`
6. `projects/specflow/docs/drafts/application_layer_specification_v0.2.0-draft.md`
7. `projects/specflow/docs/drafts/application_layer_implementation_plan_v0.1.0-draft.md`
8. Gitの現在状態

## 起動手順

### Step 1

`SpecFlow_Constitution_v1.0.md`を最上位文書として理解してください。

Constitutionに反する提案・設計・実装は行わないでください。

### Step 2

`constitution/constitution.md`、`constitution/principles.md`、`constitution/implementation_guidelines.md`をProject Rulesとして理解してください。

Implementation Pipelineでは、ConstitutionおよびProject Rulesの両方に従ってください。

### Step 3

`SESSION_CONTEXT.md`から、以下を復元してください。

- 現在の開発フェーズ
- 完了済み事項
- 現在のTask
- 制約事項
- 次に読む正式Artifact

### Step 4

Application Layer SpecificationおよびApplication Layer Implementation Planを読み、Phase 1 Implementationの開始条件を確認してください。

特に、Phase 1のPurpose、Scope、Implementation Targets、Tests、Completion Conditionsを確認してください。

### Step 5

Gitの現在状態を確認してください。

最低限、以下を確認してください。

```powershell
git status --short --branch
git log --oneline --decorate -n 5
```

Pull Request #32のmerge commitが現在の設計ベースラインであることを確認してください。

### Step 6

上記確認結果を統合し、以下をHumanへ簡潔に報告してください。

- プロジェクト理念
- 開発ルール
- 現在地
- 次工程
- Gitの現在状態

Humanの確認前に、以下は開始しないでください。

- 新しい設計
- Implementation
- Specification変更
- Implementation Plan変更

確認後は、`SESSION_CONTEXT.md`に記載された地点から、Application Layer Phase 1 Implementationを開始してください。

---

## 注意事項

- Constitutionを最優先としてください。
- Specificationを唯一の正本として扱ってください。
- 承認済みImplementation Planに従ってください。
- 推測による仕様変更は禁止です。
- Specificationから一意に決定できない事項はHumanへ確認してください。
- Human ApprovalをAIが生成、推測、補完、代替してはいけません。
- Technical RetryとCorrectionを混同しないでください。
- Review APPROVED、Human Final Approval、Merge成功、completedを混同しないでください。
- 日本語を標準言語として議論してください。
