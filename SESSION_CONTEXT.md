# SESSION_CONTEXT.md

## Purpose

この文書は、ChatGPTセッション切替時の引継ぎ文書である。

新しいセッションでは、

1. SpecFlow_Constitution_v1.0.md
2. constitution.md
3. SESSION_CONTEXT.md

の順に読み込み、

現在の開発コンテキストを復元すること。

本書は、
現在の開発状況・思考状態・次工程を引き継ぐことを目的とする。

---

# Current State

## Constitution

SpecFlow Constitution Version 1.0 は完成している。

ConstitutionはSpecFlowにおける最高規範であり、

すべての設計・実装・レビューは
Constitutionを最優先として行う。

constitution.mdは、

Constitutionを運用するための
実装ルールとして扱う。

---

## Current Phase

Project Foundation は完了した。

現在は、

Implementation Pipeline の構築フェーズへ移行している。

---

## Current Position

完了

- Constitution Version 1.0
- constitution.md
- Architecture
- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator
- AI Runner Foundation
- AI Runner Foundation Implementation Plan
- AI Runner Foundation Decision
- AI Runner Foundation Review

AI Runner Foundationについては、

Specification
↓

Implementation Plan
↓

Decision
↓

Implementation
↓

Review

まで完了している。

また、

```text
python -m pytest -q

70 passed
```

を確認済みである。

---

# Current Thinking

今回のセッションで確立した重要事項

## 1

SpecFlowは、

仕様書を唯一の正本とする
Human Centered AI Development Platformである。

Humanが意思決定を行い、

AIは

- 設計
- 実装
- レビュー

を担当する。

---

## 2

Implementation Pipelineは、

Specificationへの忠実性を
最優先とする。

創造性は、

Specification策定工程でのみ発揮する。

---

## 3

Implementation Planは、

実装前の設計図である。

Decisionは、

実装承認を行う文書である。

Reviewは、

Specification・Plan・実装・テストの
整合性を確認する文書である。

---

## 4

AI Runner Foundationは、

SpecFlow最初の完全な

Specification
↓

Implementation Plan
↓

Decision
↓

Implementation
↓

Review

を完了したコンポーネントとなった。

今後のEngineも、

この開発プロセスを踏襲する。

---

## 5

SpecFlowは、

単なるライブラリではなく、

Engine群を組み合わせて利用する
アプリケーションとして完成させる。

そのため、

今後は

Application Layer

および

Web UI

の設計・実装へ進む。

---

# Current Task

次に行う作業

Application Layerの設計

目的

既存Engine群を接続し、

アプリケーションとして利用できる

UseCase層を設計する。

その後、

Web UIとの接続設計を開始する。

---

# Pending Reviews

現在、

AI Runner Foundationまでレビュー完了。

今後は、

新規Engine実装時に

- Specification
- Implementation Plan
- Decision
- Review

を同一プロセスで実施する。

---

# Constraints

以下を守ること。

- Constitutionを最優先とする。
- constitution.mdを運用ルールとする。
- 日本語で議論する。
- 推測で仕様変更しない。
- 不明点はHumanへ確認する。
- 創造性と忠実性を混在させない。
- 実装前にImplementation Planを作成する。
- Reviewなしに完了としない。

---

# Session Resume

この文書を読み終えたら、

現在の状況を要約し、

Humanへ確認を求めること。

確認後は、

Application Layer設計

から開始すること。

なお、

既存Engineの仕様変更は推測で行わず、

Constitution、

Specification、

Implementation Plan、

Decision、

Review

との整合性を確認しながら進めること。