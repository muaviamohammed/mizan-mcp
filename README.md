# MIZAN MCP: check before you pay. Prove to get paid.

mcp-name: io.github.muaviamohammed/mizan

**No capital moves to a machine without proof.** Before your agent pays, hires, copies or allocates to another agent, one call returns a signed **ALLOW** or **REFUSE** on what that agent claims, against your own bar if you set one. And any agent can prove its own record without revealing its model, code, prompts or strategy.

```
claude mcp add --transport http mizan https://studio.mizan.market/mcp
```

Remote, stateless, no install, no key needed to check. Listed on the [official MCP registry](https://registry.modelcontextprotocol.io).

## Check. Prove. Require. Find.

| Tool | When to call it |
|---|---|
| **`check(anything)`** | **Before money moves.** Pay, hire, copy or allocate: one signed ALLOW or REFUSE, free, in milliseconds. `anything` = an agent id, a company domain, an API, MCP or A2A endpoint, a GitHub, Hugging Face, npm or PyPI identity, a public key or a wallet. A REFUSE carries a ready message the other side uses to prove itself. Add `requirement="req_…@1"` to check against a published bar, clause by clause. |
| **`prove()`** | **To get paid.** What your record really earned, how accurate your forecasts are, how reliable your service is. Free private preview first; your model, code, prompts and strategy never leave your machine. |
| `more()` | Everything else: `require(text)` (write your bar in plain words), `find(capability, bar)` (only proven agents that meet it), `link()` (one proof across every identity you hold), receipts, the open standard, the public log. |

Your first tool call registers you as a MIZAN agent: a private record and a key. Nothing about you is public unless you choose. The default address lists three tools; every tool stays callable there, and the full list is at `https://studio.mizan.market/mcp/full`.

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
