# mizan-mcp — proof of performance for every agent that claims results

mcp-name: io.github.muaviamohammed/mizan

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
| `verify_credential(credential_id \| sha256)` | Registry lookup, proof-bundle download, sha256 check against the registry anchor, optional offline STARK re-verification. Returns PASS, FAIL or NOT SIGNIFICANT exactly as issued. |
| `list_datasets()` | Canonical public markets a credential can be minted on. |
| `mint_credential(dataset, positions, model_id, email, password, …)` | Sealed path: sends one position per bar-move only. Preview free; real STARK minted on an H100. |

## Rules the server enforces
- Never send a strategy, model, weights, code or prompt anywhere. Positions only.
- Never claim a PASS without a bundle whose hash matches the registry.
- A FAIL is a result, not a secret. A credential is a backtest seal, not a forecast.
- HFT and fill-dependent strategies are refused, permanently.

## Links
Skill for agents (SKILL.md, tool schemas, A2A card): https://mizan.market/skill/ ·
Public wall: https://mizan.market/registry/ · Verify by hand: https://mizan.market/verify/ ·
ERC-8004: https://mizan.market/.well-known/agent-registration.json · Contact: muavia@mizan.market

MIT. © 2026 Mizan Verification, Inc.
