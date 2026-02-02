# Dify × Playwright MCP Integration Proposal

## 目的
Dify の Tool プラグインから Playwright を **MCP (Model Context Protocol)** 経由で操作できるようにし、
「Dify → MCP → Playwright」連携を安定・拡張性の高い形で実現する。

## ざっくり構成案

```
[Dify App/Agent]
  └─ Tool呼び出し (structured input)
      ↓
[Dify Plugin (Python Tool)]
  └─ MCP Client
      ↓ (JSON-RPC over stdio/WS/HTTP)
[MCP Playwright Server]
  └─ Playwright (browser + contexts + pages)
```

### 1. Dify Plugin を MCP Client にする
- Dify プラグインは「MCP サーバーに対してコマンドを発行するクライアント」になる。
- MCP サーバーは Playwright の操作 API を公開し、Dify からは **型付きパラメータ** で操作できる。

**メリット**
- Dify → MCP の境界を明確化し、スクリプト `exec` に依存しない。
- MCP でツール仕様を定義できるため、入力検証と監査がしやすい。

### 2. Playwright 側は MCP Server で集約
- Playwright を扱う MCP サーバーをコンテナとして独立稼働。
- Dify プラグインは MCP への接続 URI を credentials で指定。

## 実装ステップ案

### Step 1: MCP サーバーの選定/用意
- 既存の MCP Playwright サーバーがあれば採用。
- 無ければ Playwright API を MCP でラップしたサーバーを作る。
  - 最低限のコマンド例: `new_context`, `new_page`, `goto`, `screenshot`, `pdf` など。

### Step 2: Dify Plugin を MCP Client 化
1. `requirements.txt` に MCP クライアントを追加 (例: `mcp` など)。
2. `tools/playwright.py` を **exec ベースから MCP 呼び出しに差し替え**。
3. `tools/playwright.yaml` の parameters を「構造化入力」に変更。

**入力例 (structured)**
```yaml
parameters:
  - name: actions
    type: array
    required: true
    llm_description: |
      Execute a list of actions against Playwright MCP.
    schema:
      items:
        type: object
        properties:
          method: { type: string }
          params: { type: object }
```

**ツール実装イメージ (抜粋)**
```py
client = MCPClient(uri)
for action in actions:
    client.call(action["method"], action.get("params", {}))
```

### Step 3: セッション管理
- MCP 側で browser/context/page を **セッションIDで管理**。
- Dify 側からは `session_id` を維持できるよう、
  - プラグイン側で `session_id` を返却
  - 次のツール呼び出しで再利用

### Step 4: 実行結果の設計
- 文字列/画像/JSON などの成果物を MCP で返す。
- Dify 側は `ToolInvokeMessage` でテキスト/バイナリを返却。

## セキュリティと運用の注意
- **任意 Python 実行 (`exec`) を避ける**ことが最大の目的。
- MCP 側でコマンドの許可リストを管理。
- タイムアウト/リトライ/並列実行は Dify プラグイン側で制御。

## 現在の実装状況
- `tools/playwright.py` に **HTTP ベースの MCP 呼び出し** を追加済み。
- `actions` パラメータが渡され、かつ `mcp_uri` credential が設定されている場合、
  MCP JSON-RPC を順に実行して最後の結果を返す。
- WebSocket MCP には未対応のため、WS エンドポイントのみの場合はエラーになる。

## 最小構成サンプル

- Dify Plugin: MCP client only
- Playwright MCP Server: `--host 0.0.0.0 --port 3000`
- Dify credentials: `mcp_uri=http://host.docker.internal:3000`

## 期待される効果
- LLM から安全に Playwright を操作可能
- MCP 仕様に沿って API を拡張可能
- Dify 側の Tool を増やさずに機能追加できる

## 次に決めること
- MCP サーバーの実装/採用候補
- どのレイヤーでセッションを管理するか
- どの操作を許可リストに入れるか
