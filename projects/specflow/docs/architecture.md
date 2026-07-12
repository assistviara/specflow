# SpecFlow Architecture

Version: 0.1.0

---

# 1. 目的

本書は

SpecFlow全体の構造を定義する。

Constitutionが「行動原則」

Principlesが「思想」

Implementation Guidelinesが「設計規約」

であるのに対し、

Architectureは

システム全体の構造を示す。

---

# 2. 全体構成

```text
                    Human
                      │
                      ▼
             Specification
                      │
                      ▼
           Implementation Plan
                      │
                      ▼
                Decision
                      │
                      ▼
              SpecFlow Engine
                      │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
Document Loader  Template Engine  Codex Runner
      │              │              │
      └──────────────┼──────────────┘
                     ▼
               Generated Prompt
                     │
                     ▼
                  Codex CLI
                     │
                     ▼
          Implementation Plan
                     │
                     ▼
             Review Engine
                     │
                     ▼
               Human Review
```

---

# 3. Engine構成

## Document Loader

責務

正式文書を読み込む。

対象

- Constitution
- Principles
- Specification
- Decision
- Project Metadata
- Prompt Template

---

## Template Engine

責務

Templateへ値を埋め込み、

完成したPromptを生成する。

Documentは変更しない。

Templateを正本とする。

---

## Codex Runner

責務

Codex CLIを起動する。

Promptを渡す。

生成結果を取得する。

---

## Review Engine

責務

Specification

Plan

Implementation

を比較し、

レビュー結果を生成する。

---

## State Manager

責務

現在の状態を管理する。

例

- specification_editing
- plan_ready
- implementing
- reviewing
- completed

---

# 4. データの流れ

```text
Markdown

↓

Document Loader

↓

Python Object

↓

Template Engine

↓

Prompt

↓

Codex

↓

Markdown

↓

Review
```

---

# 5. レイヤ構造

Input Layer

↓

Processing Layer

↓

Execution Layer

↓

Review Layer

---

## Input Layer

Document Loader

---

## Processing Layer

Template Engine

State Manager

---

## Execution Layer

Codex Runner

---

## Review Layer

Review Runner

---

# 6. 設計原則

各Engineは

一つの責務だけ持つ。

Engine同士は

一方向のみ依存する。

逆方向の依存は禁止。

---

# 7. 将来追加予定

以下はVersion1.0以降で追加予定。

- Claude Runner
- ChatGPT Runner
- Gemini Runner
- Local LLM Runner
- Git Manager
- Plugin System
- Workflow Engine

---

# 8. Architecture方針

SpecFlowは

AIを中心に設計しない。

人間を中心に設計する。

Engineは

人間の意思決定を支援するために存在する。

---

# Closing

SpecFlowは

AI開発ツールではない。

AIと人間が

協調して開発するための

開発オーケストレーターである。