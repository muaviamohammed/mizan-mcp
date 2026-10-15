# mizan-mcp — verify any AI trading agent's track record (zero-knowledge proof of performance)

mcp-name: io.github.muaviamohammed/mizan

**Use it before you allocate to, copy, or pay any trading bot or AI agent that claims returns.**

An MCP server that lets any agent **verify** a trading or AI-agent track-record credential,
or **mint** one for its own record, without ever revealing the strategy.

MIZAN credentials are zero-knowledge (STARK) proofs under the open [VTR-1 standard](https://mizan.market/standard-spec):
the record is recomputed inside the proof with the trial count, cost schedule and out-of-sample split
bound in-circuit. Anyone verifies a credential offline in ~81 ms. FAIL verdicts are published alongside passes.

> Prove the edge. Never reveal the strategy.

## Remote (no install)
```
https://studio.mizan.market/mcp        # streamable HTTP, stateless
```
Claude Code: `claude mcp add --transport http mizan https://studio.mizan.market/mcp`

## Local (stdio)
```bash
pip install "mcp>=2"
python3 mizan_mcp_server.py
# Claude Code: claude mcp add mizan -- python3 /path/to/mizan_mcp_server.py
```

## Tools
| Tool | What it does |
|---|---|
| `check_agent(agent)` | **Start here.** Is this agent proven? Look up by name, wallet, ERC-8004 id, agent-card URL, credential id or sha256. PROVEN, REFUSED, NOT SIGNIFICANT or UNVERIFIED; unverified answers carry a message to forward to the counterparty. |
| `list_proven_agents(limit)` | PASS credentials, Bitcoin-confirmed first; issuer shown per row. |
| `verify_credential(credential_id \| sha256)` | Registry lookup, proof-bundle download, sha256 check against the registry anchor, optional offline STARK re-verification. Returns PASS, FAIL or NOT SIGNIFICANT exactly as issued. |
| `list_datasets()` | Canonical public markets a credential can be minted on. |
| `preview_credential(dataset, positions, model_id)` | Free, private, no-account gate test of your own bot or agent. Nothing is published. |
| `mint_credential(dataset, positions, model_id, email, password, …)` | Sealed path: sends one position per bar-move only. Preview free; real STARK minted on an H100. |

## Rules the server enforces
- Never send a strategy, model, weights, code or prompt anywhere. Positions only.
- Never claim a PASS without a bundle whose hash matches the registry.
- A FAIL is a result, not a secret. A credential is a backtest seal, not a forecast.
- HFT and fill-dependent strategies are refused, permanently.

## Also available as
- **AgentKit action provider** (`mizan`): `verify_credential` + `list_datasets` — PR to coinbase/agentkit.
- **A2A agent**: `https://studio.mizan.market/a2a` (JSON-RPC `message/send` → "verify <id>"); card at `https://mizan.market/.well-known/agent-card.json`.
- **ERC-8004 validator** on Base: registration file at `https://mizan.market/.well-known/agent-registration.json`.

## Links
Skill for agents (SKILL.md, tool schemas, A2A card): https://mizan.market/skill/ ·
Public wall: https://mizan.market/registry/ · Verify by hand: https://mizan.market/verify/ ·
ERC-8004: https://mizan.market/.well-known/agent-registration.json · Contact: muavia@mizan.market

MIT. © 2026 Mizan Verification, Inc.


## Keywords
AI trading agent verification · backtest overfitting · deflated Sharpe ratio · proof of performance · verifiable track record · zero-knowledge proof · zkVM · RISC Zero · STARK · ERC-8004 · A2A · x402 · Hyperliquid vault due diligence · trading bot audit
