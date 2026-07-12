# Plan Prompt Review

Review No: 001

対象:
plan_prompt_template.md

Version:
1.0

レビュー日:
2026-07-12

レビュアー:
たけしゃん
ChatGPT

---

# 1. レビュー目的

Plan Prompt Template Version1.0が

・Constitution

・Principles

・Specification

に従っているかを確認する。

また、

Codexが安全かつ再現可能に
Implementation Planを生成できる内容であるかを確認する。

---

# 2. 総合評価

★★★★★

Version1.0として十分に利用可能。

重大な問題は認められない。

改善事項はVersion1.1で反映する。

---

# 3. 良かった点

## 3.1 AIの役割が明確

Plan工程では

「調査」

「Plan作成」

のみを担当し、

コード変更は禁止されている。

Constitutionと一致している。

---

## 3.2 優先順位が明確

Constitution

↓

Principles

↓

Specification

↓

Decision

↓

既存コード

↓

一般的ベストプラクティス

という優先順位が整理されている。

AIが既存コードを理由に
Specificationを変更しない設計になっている。

---

## 3.3 安全性が高い

曖昧な仕様

DB変更

認証変更

PKL互換性

ライブラリ変更

などでは

人間確認を必須としている。

---

## 3.4 Traceability

PRE

REQ

をPlanまで追跡する設計となっている。

---

## 3.5 出力形式が統一されている

Implementation Planの出力形式が固定されており、

再現性が高い。

---

# 4. 改善提案

## IMP-001

UNKNOWNという状態を追加する。

調査できなかった項目は

推測せず

UNKNOWN

として出力する。

---

## IMP-002

Project Metadataを入力情報へ追加する。

project.json

の内容をPromptへ渡す。

---

## IMP-003

Decisionとの対応を追加する。

Decision ID

↓

Plan

の追跡ができるようにする。

---

## IMP-004

Planの最後に

Confidence

High

Medium

Low

を出力する。

---

# 5. Constitutionとの整合性

|項目|結果|
|---|---|
|仕様書優先|PASS|
|Plan優先|PASS|
|説明責任|PASS|
|レビュー必須|PASS|
|安全第一|PASS|

---

# 6. Principlesとの整合性

|項目|結果|
|---|---|
|人間主体|PASS|
|AIは部下|PASS|
|小さく完成|PASS|
|履歴は資産|PASS|
|実践を通して学ぶ|PASS|

---

# 7. 判定

Status

APPROVED

Version1.0として採用する。

改善事項は

Version1.1で対応する。

---

# 8. 次回レビュー予定

実際にCodexでPlan生成を行った後、

Version1.1レビューを実施する。