# SpecFlow Architecture

Version: 1.0

---

# 1. Purpose（目的）

本書は、SpecFlow全体のアーキテクチャを定義する。

Constitutionは、

「何を守るべきか」

を定義する。

AI Developer Oathは、

AI開発者としての誓約を定義する。

Principlesは、

AI開発者の行動規範を定義する。

Implementation Guidelinesは、

実装時に従う設計規約を定義する。

Architectureは、

SpecFlow全体の構造として、

- AI組織
- システム構造
- Engine
- Layer
- Dependency
- Data Flow

を定義する。

Architectureは、

Constitution、

AI Developer Oath、

Principles

と整合していなければならない。

本書は、

SpecFlowの進化に合わせて継続的に更新される。

---

# 2. Overall Architecture

SpecFlowは、

次の二つのArchitectureによって構成される。

```text
SpecFlow Architecture
│
├── AI Organization Architecture
│
└── System Architecture
```

AI Organization Architectureは、

AI開発者同士の責務、

協調、

成果物の受け渡し、

Humanとの関係を定義する。

System Architectureは、

Engine、

Layer、

Dependency、

Data Flow

を定義する。

両Architectureは独立しているが、

常に整合していなければならない。

---

# 3. AI Organization Architecture

## 3.1 Purpose

AI Organization Architectureは、

SpecFlowへ参加するAI開発者の責務と、

Humanとの関係を定義する。

SpecFlowでは、

AIは一つの巨大なAIとして動作するのではない。

それぞれ責務を持つ複数のAIが、

一つの開発チームとして協調する。

---

## 3.2 Organization Structure

```text
                        Human
                           │
                  Decision / Approval
                           │
                           ▼
                     Requirement
                           │
                           ▼
                     Specification
                           │
────────────────────────────────────────────

                 Specification AI
                         │
                         ▼
                  Architecture AI
                         │
                         ▼
                Implementation AI
                         │
                         ▼
                     Review AI
                         │
                         ▼
                      Test AI

────────────────────────────────────────────
                         │
                         ▼
                  Approved Result
```

---

## 3.3 Governance

すべてのAI開発者は、

Constitution

↓

AI Developer Oath

↓

Principles

に従って行動する。

Architectureは、

これらの統治文書に反する設計を行ってはならない。

---

## 3.4 Responsibility

各AIは、

担当工程だけを担当する。

担当工程以外の責務を

代行してはならない。

担当外の判断が必要になった場合は、

担当工程またはHumanへ返却する。

---

## 3.5 Collaboration

AI同士は、

成果物を受け渡すことで協調する。

担当外の成果物を、

独断で変更してはならない。

改善提案を発見した場合は、

Implementationへ反映せず、

Specification策定工程へ返却する。

---

## 3.6 Human-Centered Development

SpecFlowでは、

Humanだけが

意思決定を行う。

AIは、

分析

提案

設計

実装

レビュー

テスト

を担当する。

AIは、

最終判断を行わない。

正式成果物は、

Humanによる承認を経て確定する。

AIが生成する成果物は、

すべてDraftとして扱われる。

---

# 4. System Architecture

System Architectureは、

SpecFlowを構成するEngine、

Layer、

データフロー、

依存関係を定義する。

System Architectureは、

AI Organization Architectureが定義する責務を、

実際のソフトウェアとして実現する。

Engineは、

単一責務を持つ小さな部品として設計される。

必要に応じて、

複数のEngineを組み合わせることで、

一つのユースケースを構成する。

---

# 4.1 Overall Flow

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

SpecFlowでは、

各Engineが成果物を段階的に生成し、

次のEngineへ受け渡す。

すべての成果物は、

Humanが承認するまでDraftとして扱われる。

---

# 5. Engine Architecture

SpecFlowは、

役割ごとに分割されたEngineによって構成される。

Engineは、

以下の二種類に分類される。

- Core Engine
- Orchestration Engine

将来的には、

Execution EngineおよびSupport Engineが追加される予定である。

---

# 5.1 Core Engine

Core Engineは、

一つの責務だけを持つ。

他Engineから利用されることを前提とし、

単独でもテスト可能である。

Core Engine同士は、

可能な限り独立して設計する。

---

## Document Loader

### Responsibility

正式文書を読み込み、

Python Objectとして提供する。

### Input

- Constitution
- AI Developer Oath
- Principles
- Architecture
- Specification
- Decisions
- PROJECT
- Prompt Template

### Output

Document Object

---

## Template Engine

### Responsibility

Templateへ値を埋め込み、

Prompt Templateを展開する。

Templateそのものは変更しない。

Templateを唯一の正本とする。

### Output

Rendered Prompt

---

## Prompt Builder

### Responsibility

Template Engineを利用し、

Promptを構築する。

ContextとTemplateを統合し、

PromptResultを生成する。

### Output

PromptResult

---

# 5.2 Orchestration Engine

Orchestration Engineは、

複数のCore Engineを組み合わせ、

一つのユースケースを実現する。

Core Engineに業務知識を持たせてはならない。

ユースケース固有の制御は、

Orchestration Engineが担当する。

---

## Plan Prompt Generator

### Responsibility

Implementation Plan作成用Promptを生成する。

### Flow

1. Document Loaderから正式文書を取得する。
2. Contextを構築する。
3. Prompt Builderへ渡す。
4. PromptResultを取得する。
5. 呼び出し元へ返却する。

Plan Prompt Generatorは、

SpecFlowにおける最初のOrchestration Engineである。

---

# 5.3 Planned Engine

以下のEngineは、

Version 1.0では未実装であり、

将来追加予定である。

---

## AI Runner

### Responsibility

AIへPromptを渡し、

生成結果を取得する。

### Supported AI

- Codex
- ChatGPT
- Claude
- Gemini
- Local LLM

AI Runnerは、

AI固有の差異を吸収するAdapterとして動作する。

---

## Review Engine

### Responsibility

以下を比較し、

レビュー結果を生成する。

- Specification
- Implementation Plan
- Source Code
- Test Result

Review Engineは、

Draftの品質確認を担当する。

最終判断はHumanが行う。

---

## Test Engine

### Responsibility

テストコードの生成、

実行、

結果収集を担当する。

将来的には、

自動回帰テストにも対応する。

---

## State Manager

### Responsibility

現在の開発状態を管理する。

### Example

- requirement_editing
- specification_editing
- architecture_editing
- planning
- implementing
- reviewing
- testing
- completed

State Managerは、

各Engineの現在位置を管理する。

---

# 5.4 Engine Relationship

```text
Document Loader
        │
        ▼
Prompt Builder
        │
        ▼
Template Engine
        │
        ▼
Plan Prompt Generator
        │
        ▼
AI Runner
        │
        ▼
Review Engine
        │
        ▼
Test Engine
```

各Engineは、

単一責務を維持しながら、

一方向に成果物を受け渡す。

Engine間で循環依存を作ってはならない。

---

# 6. Data Flow

SpecFlowでは、

各Engineが入力データを段階的に変換しながら処理を進める。

```text
Markdown Documents
        │
        ▼
Document Loader
        │
        ▼
Document Objects
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
Draft
        │
        ▼
Review Engine
        │
        ▼
Reviewed Draft
        │
        ▼
Human Review
        │
        ▼
Approved Document
```

各Engineは、

入力を受け取り、

次工程で利用できる成果物へ変換する責務のみを持つ。

正式文書は、

Humanが承認するまで変更されない。

AIが生成する成果物は、

すべてDraftとして扱われる。

---

# 7. Layer Architecture

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

正式文書を扱う。

### Engine

- Document Loader

---

## Prompt Construction Layer

Promptを構築する。

### Engine

- Template Engine
- Prompt Builder

---

## Orchestration Layer

複数Engineを組み合わせ、

ユースケースを実現する。

### Engine

- Plan Prompt Generator

---

## Execution Layer

AIを実行する。

### Engine

- AI Runner

---

## Review Layer

生成物をレビューする。

### Engine

- Review Engine
- Test Engine

---

## EngineとLayerの対応

| Layer | Core Engine | Orchestration Engine |
|--------|-------------|----------------------|
| Input | Document Loader | - |
| Prompt Construction | Template Engine<br>Prompt Builder | - |
| Orchestration | - | Plan Prompt Generator |
| Execution | AI Runner | - |
| Review | Review Engine<br>Test Engine | - |

各Engineは、

責務に応じたLayerへ配置される。

Core Engineは、

再利用可能な部品として設計される。

Orchestration Engineは、

Core Engineを組み合わせ、

ユースケースを実現する。

---

# 8. Dependency Rules

SpecFlowでは、

依存関係を単純に保つことを重視する。

## One-way Dependency

依存は、

上位Layerから下位Layerへのみ許可する。

逆方向依存は禁止する。

---

## No Circular Dependency

循環依存は禁止する。

Engine同士は、

互いに独立していることを原則とする。

---

## Single Responsibility

各Engineは、

一つの責務だけを持つ。

責務が増えた場合は、

新しいEngineとして分離する。

---

## Reusability

Core Engineは、

再利用可能な部品として設計する。

ユースケース固有の処理は、

Orchestration Engineが担当する。

---

# 9. Design Principles

SpecFlowの実装は、

以下の設計原則に従う。

- Human-centered
- Single Responsibility
- One-way Dependency
- Reusability
- Draft First
- Traceability
- Separation of Concerns

Architectureは、

Constitution、

AI Developer Oath、

Principles

と整合していなければならない。

---

# 10. Future Extensions

Version 1.x以降では、

以下の機能追加を予定している。

## AI Runner

- Claude Runner
- ChatGPT Runner
- Gemini Runner
- Codex Runner
- Local LLM Runner

---

## Development Support

- Workflow Engine
- Git Manager
- Plugin System
- Template Repository

---

## AI Collaboration

- Multi AI Scheduling
- Distributed Execution
- Review Automation
- Knowledge Base
- AI Marketplace

---

# 11. Architecture Policy

SpecFlowは、

AIを中心に設計しない。

Humanを中心に設計する。

AIは、

意思決定を行わない。

AIは、

分析、

設計、

実装、

レビュー、

テスト

を担当する。

最終的な責任は、

常にHumanが担う。

Architectureは、

AIがHumanを置き換えるためではなく、

HumanがAIを最大限活用するために存在する。

---

# Closing

SpecFlowは、

単なるAI開発ツールではない。

SpecFlowは、

Humanを中心に、

複数のAIが、

それぞれの責務を果たしながら協調して開発を進めるための、

AI協調開発アーキテクチャである。

Constitutionは、

守るべき価値を定義する。

AI Developer Oathは、

AI開発者としての誓約を定義する。

Principlesは、

AIの行動規範を定義する。

Architectureは、

それらを実現するための構造を定義する。

SpecFlowは、

Human、

AI、

Software Architecture

の調和によって、

継続的かつ高品質なソフトウェア開発を実現する。