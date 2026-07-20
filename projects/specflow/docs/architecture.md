# SpecFlow Architecture

Version: 0.2.0

---

# 1. 目的

本書は、SpecFlow全体の構造を定義する。

Constitutionが「行動原則」、

Principlesが「思想」、

Implementation Guidelinesが「設計規約」

を定義するのに対し、

Architectureは、

- システム全体の構造
- Engine間の責務と依存関係
- データの流れ
- レイヤ構造
- 実装済み機能と将来構想

を示す。

本書は、SpecFlowの実装状況に合わせて更新される。

Version 0.2.0では、

- Document Loader
- Template Engine
- Prompt Builder
- Plan Prompt Generator

の実装結果を反映し、

Core EngineとOrchestration Engineの区分を導入する。
---

# 2. 全体構成

```text
                         Human
                           │
                           ▼
                     Requirement
                           │
                           ▼
                    Specification
                           │
                           ▼
               Plan Prompt Generator
                  │               │
                  ▼               ▼
          Document Loader   Prompt Builder
                                   │
                                   ▼
                            Template Engine
                                   │
                                   ▼
                             Plan Prompt
                                   │
                                   ▼
                              AI Runner
                           (Codex CLI)
                                   │
                                   ▼
                  Implementation Plan (Draft)
                                   │
                                   ▼
                            Human Review
                                   │
                                   ▼
                 Approved Implementation Plan
```

---

# 3. Engine構成

SpecFlowは、単一責務のEngineを組み合わせて構成される。

Engineは役割に応じて、以下の2種類に分類する。

- Core Engine
- Orchestration Engine

---

# 3.1 Core Engine

Core Engineは、一つの責務だけを持つ基本部品である。

他のEngineから利用されることを前提とし、
単独でもテスト可能である。

---

## Document Loader

### 責務

正式文書を読み込み、
Pythonオブジェクトとして提供する。

### 対象

- Constitution
- Principles
- Specification
- Decisions
- Project Metadata
- Prompt Template

---

## Template Engine

### 責務

Templateへ値を埋め込み、
テンプレートを展開する。

Documentは変更しない。

Templateを正本とする。

---

## Prompt Builder

### 責務

Template Engineを利用し、

Promptを構築する。

PromptResultを生成し、
呼び出し元へ返す。

---

# 3.2 Orchestration Engine

Orchestration Engineは、
複数のCore Engineを組み合わせ、
一つのユースケースを実現する。

---

## Plan Prompt Generator

### 責務

Plan作成用Promptを生成する。

Document Loaderから正式文書を取得し、

Contextを構築し、

Prompt Builderへ渡す。

PromptResultを取得し、
呼び出し元へ返す。

本Engineは、
複数のCore Engineを組み合わせる
オーケストレーションEngineである。

---

# 3.3 Planned Engine

以下のEngineは、
Version 0.2では未実装であり、
将来追加予定である。

---

## AI Runner

### 責務

AIへPromptを渡し、

生成結果を取得する。

実装例

- Codex CLI
- Claude
- ChatGPT
- Gemini
- Local LLM

---

## Review Engine

### 責務

Specification

Implementation Plan

Implementation

を比較し、

レビュー結果を生成する。

---

## State Manager

### 責務

現在の状態を管理する。

例

- requirement_editing
- specification_editing
- planning
- implementing
- reviewing
- completed

---

# 4. データの流れ

SpecFlowでは、
各Engineがデータを段階的に変換しながら処理を進める。

```text
Markdown Documents
        │
        ▼
Document Loader
        │
        ▼
Python Objects
        │
        ▼
Plan Prompt Generator
        │
        ▼
Context
        │
        ▼
Prompt Builder
        │
        ▼
Template Engine
        │
        ▼
PromptResult
        │
        ▼
Plan Prompt
        │
        ▼
AI Runner
        │
        ▼
Implementation Plan (Draft)
        │
        ▼
Human Review
        │
        ▼
Approved Implementation Plan
```
各Engineは、
入力データを次の形式へ変換する責務のみを持つ。

正式文書は人間が承認するまで変更されない。

AIが生成する成果物は、
すべてDraftとして扱う。
---

# 5. レイヤ構造
SpecFlowは、
責務ごとに5つのLayerへ分割する。

```text
Input Layer
        │
        ▼
Prompt Construction Layer
        │
        ▼
Orchestration Layer
        │
        ▼
Execution Layer
        │
        ▼
Review Layer
```
---

## Input Layer

入力となる正式文書を扱う。

### 構成

- Document Loader

## Prompt Construction Layer

Promptを構築する。

### 構成

- Template Engine
- Prompt Builder

## Orchestration Layer

複数のCore Engineを組み合わせ、
ユースケースを実現する。

### 構成

- Plan Prompt Generator

## Execution Layer

AIを実行する。

### 構成

- AI Runner（Planned）

## Review Layer

成果物をレビューする。

### 構成

- Review Engine（Planned）

---

## EngineとLayerの対応

| Layer | Core Engine | Orchestration Engine |
|-------|-------------|----------------------|
| Input | Document Loader | - |
| Prompt Construction | Template Engine<br>Prompt Builder | - |
| Orchestration | - | Plan Prompt Generator |
| Execution | AI Runner（Planned） | - |
| Review | Review Engine（Planned） | - |

各Engineは責務に応じたLayerへ配置される。

Core Engineは単一責務を持つ再利用可能な部品であり、
Orchestration Engineは複数のCore Engineを組み合わせてユースケースを実現する。
---

# 6. 設計原則

SpecFlowは、以下の設計原則に従う。

## 単一責務

各Engineは、一つの責務だけを持つ。

責務が増えた場合は、新しいEngineとして分離する。

---

## 一方向依存

Engine同士は一方向のみ依存する。

逆方向の依存は禁止する。

依存関係は上位Layerから下位Layerへのみ許可する。

---

## 再利用性

Core Engineは再利用可能な部品として設計する。

Orchestration Engineは、
Core Engineを組み合わせてユースケースを実現する。

---

## 人間中心

AIが生成する成果物は、すべてDraftとして扱う。

正式な成果物は、人間によるレビューおよび承認を経て確定する。

---

# 7. 将来の拡張

以下はVersion 1.0以降で追加を予定している。

## AI Runner

- Claude Runner
- ChatGPT Runner
- Gemini Runner
- Local LLM Runner

## Development Support

- Git Manager
- Plugin System
- Workflow Engine

---

# 8. Architecture方針

SpecFlowは、
AIを中心に設計しない。

人間を中心に設計する。

AIは意思決定を行わない。

AIは、人間の意思決定を支援するための実行エンジンである。

最終的な責任と承認は、
常に人間が担う。

---

# Closing

SpecFlowは、
AI開発ツールではない。

SpecFlowは、
人間がAIを活用し、
より良いソフトウェアを開発するための
開発オーケストレーターである。

AIはコードを生成する。

人間は価値を決定する。

SpecFlowは、その協調を支える。