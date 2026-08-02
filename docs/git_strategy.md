# SpecFlow Git Strategy

Version: 0.1.0

---

# Purpose（目的）

本書は、

SpecFlowにおける
GitおよびGitHubの運用ルールを定義する。

Gitの一般的な操作方法ではなく、

SpecFlowの開発で使用する

- Branch
- Pull Request
- Merge
- Tag

の運用方針を定める。

---

# 1. Branch

## main

正式に承認された状態を保持する。

直接開発は行わない。

Pull Requestによってのみ更新する。

---

## developer

通常の開発作業を行う。

新しい文書、
実装、
修正は、

原則としてdeveloperブランチで行う。

---

# 2. 開発フロー

SpecFlowでは、
次の順序で開発を行う。

```text
developer
    │
    ▼
実装・修正
    │
    ▼
Commit
    │
    ▼
Push (origin/developer)
    │
    ▼
Pull Request
    │
    ▼
Human Review
    │
    ▼
Merge
    │
    ▼
main
    │
    ▼
Pull
    │
    ▼
developerへ反映
```

通常は、

```bash
git push origin developer

git checkout main
git pull origin main

git checkout developer
git merge main

git push origin developer
```

の流れで同期する。

---

# 3. Pull Request

developerからmainへの反映は、

Pull Requestを使用する。

Pull Requestには、

最低限、

以下を記載する。

- 概要
- 完了した文書または機能
- 主な決定事項
- 次に進む内容

人間が内容を確認した後、

mainへMergeする。

---

# 4. Tag

Tagは、

重要なマイルストーンとなる

Commitへ付与する。

TagはBranchではなく、

Commitを識別する。

---

## Tag命名規則

```
<対象>-v<Version>
```

例

```
docs-v1.0

prototype-v0.1

release-v1.0
```

---

## Tagの意味

### docs

中核文書の完成

例

```
docs-v1.0
```

---

### prototype

動作するプロトタイプ

例

```
prototype-v0.1
```

---

### release

正式版

例

```
release-v1.0
```

---

## Tag作成

```bash
git tag -a docs-v1.0 -m "SpecFlow中核文書 v1.0 完成"

git push origin docs-v1.0
```

---

# 5. Release

GitHub Releaseは、

Tagへ

説明

配布物

変更履歴

などを付加して、

正式公開する場合のみ作成する。

開発途中の節目は、

Tagのみで管理する。

---

# 6. 更新方針

本書は、

Gitの操作方法を網羅するものではない。

SpecFlowの開発において

繰り返し利用する

Git運用ルールのみを定義する。

必要に応じて、

Versionを更新する。

---

# 7. 現在のマイルストーン

| Tag | Commit | 内容 |
|------|--------|------|
| docs-v1.0 | 09dd00b | SpecFlow中核文書 Version 1.0 完成 |

---

# Closing Statement

Gitは、

ソースコードを保存するためだけのものではない。

SpecFlowでは、

文書、

設計、

実装、

レビュー、

意思決定

すべてを

開発資産として管理する。

Tagは、

その時点で到達した

設計上のマイルストーンを記録するものである。