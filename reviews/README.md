# SpecFlow Reviews

Version: 0.1.0

Status: Ready

---

# 1. 目的

レビューは、
実装が正式文書に適合していることを確認し、
品質を保証するために実施する。

レビューでは次を確認する。

- Specification
- Implementation Plan
- Decision
- Implementation Guidelines

pytestによる動作確認だけでなく、

- 責務
- 依存関係
- 設計判断
- 実装範囲
- テスト内容

も確認する。

---

# 2. レビュー対象

レビューでは、
次の工程の整合性を確認する。

```text
Specification
      ↓
Implementation Plan
      ↓
Decision
      ↓
Implementation
      ↓
Tests
```

レビューは、
実装だけではなく、
設計から実装までを確認する工程である。

---

# 3. 判定区分

## PASS

仕様・設計・承認内容に適合している。

---

## WARNING

実装は承認できるが、

- 将来の改善候補
- 軽微な注意事項
- Versionアップ時の検討事項

が存在する。

---

## FAIL

次のいずれかに該当する。

- 仕様違反
- Decision違反
- 承認範囲外の変更
- テスト不足
- 重大な品質問題

---

# 4. 総合判定

## APPROVED

現在の実装を正式に承認できる。

---

## CHANGES REQUESTED

修正後に
再レビューを実施する。

---

# 5. 命名規則

レビュー文書は次の命名規則とする。

```text
review_<対象機能>_<連番3桁>.md
```

例

```text
review_document_loader_001.md
review_template_engine_001.md
review_prompt_builder_001.md
```

---

# 6. 完了条件

レビュー工程は、
次のすべてを満たした場合に完了とする。

- 正式文書との適合性を確認した
- 実装範囲を確認した
- 責務分離を確認した
- テスト結果を確認した
- 総合判定を記録した
- 人間がレビュー結果を確認した

---

# 7. 文書構成

レビュー関連文書は、
次の役割で管理する。

```text
reviews/
    README.md
        ↓
レビュー制度の共通ルール

document_templates/
    review_template.md
        ↓
レビュー文書の雛形

reviews/
    review_<feature>_001.md
        ↓
各機能のレビュー結果
```

---

# 8. レビュー方針

SpecFlowでは、

レビューは
バグ探しだけを目的としない。

レビューでは、

- 仕様への適合性
- 設計の一貫性
- 責務分離
- テスト品質
- 保守性

を確認し、

改善提案がある場合は
将来Versionへの提案として記録する。

Version 0.1では、
レビューは人間が最終確認を行う。

将来は、
Review Engineによる
レビュー支援を追加する予定である。

---

# Closing

レビューは、
SpecFlowの品質保証工程である。

レビュー結果は、

- 実装の承認
- 将来への改善提案
- 開発履歴

として蓄積し、

継続的に品質を向上させることを目的とする。