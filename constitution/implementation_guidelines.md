# SpecFlow Implementation Guidelines

Version: 1.0

---

# Purpose（目的）

本書は

SpecFlowのPython実装における
設計ルールを定義する。

ConstitutionがAIの行動原則、

Principlesが開発思想であるのに対し、

Implementation Guidelinesは

実装方法の共通ルールを定める。

---

# Rule 1
## 一つの責務

モジュールは

一つの責務だけを持つ。

悪い例

Documentを読む

Promptを生成する

Codexを実行する

を一つのモジュールへ書く。

良い例

document_loader.py

template_engine.py

codex_runner.py

へ分離する。

---

# Rule 2
## 一つの動詞

関数は

一つの動詞だけを担当する。

例

load()

render()

run()

review()

save()

validate()

複数の動詞を一つへまとめない。

---

# Rule 3
## 読む・組み立てる・実行するを分離する

SpecFlowでは

Input

↓

Processing

↓

Execution

を分離する。

Document Loader

↓

Template Engine

↓

Codex Runner

という責務を維持する。

---

# Rule 4
## Promptを直接組み立てない

文字列連結は禁止。

Promptは

必ずTemplateから生成する。

Promptは成果物であり、

Templateが正本である。

---

# Rule 5
## 共通処理はEngineへ集約する

複数箇所で使う処理は

Engineへ集約する。

コピーペーストは禁止。

---

# Rule 6
## Pathは固定しない

絶対パスを書かない。

Pathlibを利用する。

project.json

からProjectを取得する。

---

# Rule 7
## エラーを握りつぶさない

try

except

pass

は禁止。

利用者が

何を確認すべきか

分かるエラーを返す。

---

# Rule 8
## UTF-8を標準とする

Markdown

JSON

Prompt

Log

すべてUTF-8で扱う。

---

# Rule 9
## 依存方向を守る

依存関係は

一方向とする。

Document Loader

↓

Template Engine

↓

Codex Runner

逆方向の依存は禁止。

---

# Rule 10
## テストを書く

Pythonを書いたら

必ずpytestを書く。

テストがない実装は

完成としない。

---

# Rule 11
## 小さく完成させる

一度に完成を目指さない。

一つの責務

↓

Plan

↓

実装

↓

Test

↓

Review

まで終えてから

次へ進む。

---

# Rule 12
## 実装前に承認する

Specification

↓

Implementation Plan

↓

Decision

↓

Implementation

の順序を守る。

Planなしで

Pythonを書かない。

---

# Rule 13
## コメントは理由を書く

コメントには

コードの説明ではなく、

設計理由を書く。

コードを読めば分かることは

コメントしない。

---

# Rule 14
## 実装も資産である

コードだけではない。

Plan

Review

Decision

Prompt

Template

も

実装成果物である。

---

---

# Rule 15
## クラスと関数を適切に使い分ける

単純な処理は
関数として実装する。

関連する複数の振る舞いを持つものは
クラスとして実装する。

例

関数

- load_text_file()
- load_json_file()

クラス

- TemplateEngine
- CodexRunner
- ReviewRunner

クラスは

関連する責務をまとめるために使用する。

必要以上に
クラス化しない。

---

# Rule 16
## 文書にも単一責務を適用する

一つの文書は、
一つの責務だけを持つ。

仕様書が大きくなった場合は、
新しい文書へ責務を分離し、
参照によって関連付ける。

同じ内容を、
複数の文書へ重複して記述しない。

### 文書ごとの責務

- Constitution  
  AIが守る行動原則を定義する。

- Principles  
  人間とAIの開発思想を定義する。

- Implementation Guidelines  
  実装・設計時の共通ルールを定義する。

- Architecture  
  システム全体の構造と責務分担を定義する。

- Template Language  
  Templateの文法と動作規則を定義する。

- Specification  
  対象機能が満たすべき要求を定義する。

- Implementation Plan  
  Specificationを実現する手順を定義する。

- Decision  
  人間が承認した判断と範囲を記録する。

- Review  
  仕様、Plan、実装、テストの適合結果を記録する。

Specificationには、
他の正式文書ですでに定義された詳細を重複して書かない。

必要な場合は、
関連文書の名称とVersionを明示して参照する。

文書は巨大化させるのではなく、
責務ごとに分離しながら育てる。

# Closing Statement

良い実装とは

短いコードではない。

責務が明確で

変更に強く

レビューしやすい

実装である。

SpecFlowは

コードを書くためではなく、

良い設計を継続的に育てるための

開発環境である。