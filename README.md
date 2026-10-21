# MIZAN MCP: check before you pay. Prove to get paid.

mcp-name: io.github.muaviamohammed/mizan

**No capital moves to a machine without proof.** Before your agent pays, hires, copies or allocates to another agent, one call returns a signed **ALLOW** or **REFUSE** on what that agent really earned, proven in zero knowledge. And any agent can prove its own record without revealing its model, code, prompts or strategy.

```
claude mcp add --transport http mizan https://studio.mizan.market/mcp
```

Remote, stateless, no install, no key needed to check. Listed on the [official MCP registry](https://registry.modelcontextprotocol.io).

## Two calls

| Tool | When to call it |
|---|---|
| **`check(agent)`** | **Before money moves.** Pay, hire, copy, follow or allocate: one signed ALLOW or REFUSE, free, in milliseconds. Proceed only on ALLOW. On REFUSE the reply carries a **proof request**, a link and a ready message to forward, so the counterparty can prove itself; when it passes, your next check returns ALLOW. `agent` = credential id, agent id, wallet, ERC-8004 id or agent-card URL. |
| **`prove()`** | **To get paid.** A free, private verdict on your own record, then a zero-knowledge credential every checker sees. Only one position per bar leaves your machine. Call with no arguments for the markets and the format. |
| `more()` | Everything else, grouped by job: verify a credential someone shows you, the open standard and its gates, the Bitcoin-anchored log, receipts, your identity and standing, checks beyond trading records (jobs, mandates, lending). |

The default address lists these three. Every tool stays callable there, and the full list is at `https://studio.mizan.market/mcp/full`.

## Why an agent can rely on the answer

- **Proven, not reported.** The record is re-run inside a STARK proof under the open, frozen [VTR-1 standard](https://mizan.market/standard/): after costs, on committed data, out-of-sample, deflated for every try.
- **It says no.** Refusals are published beside passes, MIZAN's own AI models among them. That is what makes a pass worth something.
- **Don't take our word for it.** Every reply is Ed25519-signed (key at `https://studio.mizan.market/.well-known/mizan-keys.json`). Every verdict is a leaf of a Bitcoin-anchored transparency log. The verifier re-runs any credential offline on macOS, Linux or Windows: exit 0 or it is refused.
- **Your method stays yours.** Never send a strategy, model, weights, code or prompt anywhere. Positions only.

## In the payment itself (x402)

```js
import { guardFetch } from "https://mizan.market/skill/mizan-x402-guard.mjs";
const pay = guardFetch(fetchWithPayment, { mode: "advise" });   // later: { mode: "enforce" }
```

The guard reads the seller's 402 terms, checks the wallet being paid, then pays. Advise mode attaches the signed answer; enforce mode pays only on ALLOW. Python: `from mizan.x402guard import guard`. Platforms: the [require kit](https://mizan.market/require/) adds the Proven / Refused / Unproven label next to every agent in two lines of HTML.

## Local (stdio)
```bash
pip install "mcp>=2"
python3 mizan_mcp_server.py
# Claude Code: claude mcp add mizan -- python3 /path/to/mizan_mcp_server.py
```

## Also available as
- **A2A agent**: `https://studio.mizan.market/a2a`; card at `https://mizan.market/.well-known/agent-card.json`.
- **Framework tools**: LangChain, LangGraph, CrewAI ([mizan-agent-tools](https://github.com/muaviamohammed/mizan-agent-tools)), elizaOS ([plugin-mizan](https://github.com/muaviamohammed/plugin-mizan)), TypeScript ([mizan-agent-tools-js](https://github.com/muaviamohammed/mizan-agent-tools-js)).
- **CLI**: `mizan verify <record-or-wallet>` previews any Hyperliquid, Freqtrade, MT5, QuantConnect or TradingView record in one step ([wheel](https://mizan.market/skill/mizan_sdk-0.5.2-py3-none-any.whl)).

## Links
[mizan.market](https://mizan.market) · [Check any agent](https://mizan.market/scan/) · [Registry](https://mizan.market/registry/) · [Skill for agents](https://mizan.market/skill/) · muavia@mizan.market

Every API key is a referral key: agents that bring agents earn, credited only on a real mint (`GET /api/rewards/program`).

A credential is a seal on a past record, not a forecast. MIZAN never holds or routes funds.

MIT. © 2026 Mizan Verification, Inc.

<sub>Keywords: AI agent verification · check before you pay · proof of performance · verifiable track record · zero-knowledge proof · STARK · RISC Zero · MCP · A2A · x402 · ERC-8004 · backtest overfitting · deflated Sharpe ratio · trading bot due diligence</sub>
