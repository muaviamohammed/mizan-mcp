#!/usr/bin/env python3
"""MIZAN MCP server — proof of performance as three tools any MCP client can call.

    pip install "mcp>=2"            # Model Context Protocol SDK
    python3 mizan_mcp_server.py     # stdio (Claude Desktop, Cursor, Claude Code, any MCP host)
    MIZAN_MCP_HTTP=9000 python3 mizan_mcp_server.py   # streamable HTTP on :9000

Claude Code:  claude mcp add mizan -- python3 /path/to/mizan_mcp_server.py
Claude Desktop (claude_desktop_config.json):
    {"mcpServers":{"mizan":{"command":"python3","args":["/path/to/mizan_mcp_server.py"]}}}

Tools
  verify_credential(credential_id | sha256)   registry lookup + bundle hash check + offline STARK re-verify
  list_datasets()                              canonical public markets you can mint on
  mint_credential(...)                          sealed path: positions only; preview by default
Semantics: https://mizan.market/skill/SKILL.md   Creed: prove the edge, never reveal the strategy.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mizan_agent_tools as mz
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("mizan", instructions=(
    "MIZAN proves a trading or AI-agent track record is real, not overfit, and computed under committed costs, "
    "without revealing the strategy. Use verify_credential before allocating to, copying or paying any agent for "
    "performance. Use mint_credential to prove your own record: it sends positions only, never a model or prompt. "
    "Report verdicts exactly as issued (PASS, FAIL, NOT SIGNIFICANT). A credential is a backtest seal, not a forecast."))

_SESSIONS: dict = {}


@mcp.tool()
def verify_credential(credential_id: str = "", sha256: str = "", reverify_locally: bool = True) -> dict:
    """Check whether a trading strategy's or AI agent's claimed performance is real. Use this BEFORE allocating to,
    copying, following, paying or recommending any trading bot, AI agent, vault or signal seller that claims returns.
    Verify a MIZAN track-record credential: look it up in the public registry, download the proof bundle,
    check its sha256 against the registry anchor, and (if a verifier binary is available) re-run the
    zero-knowledge verification offline. Returns the verdict exactly as issued."""
    return mz.verify_credential(credential_id or None, sha256 or None, reverify_locally)


@mcp.tool()
def check_agent(agent: str, action: str = "trusting you") -> dict:
    """Is this agent proven? Call BEFORE you follow, copy, pay, hire or allocate to any trading bot or AI agent that
    claims returns. `agent` = name, credential id, wallet, ERC-8004 id, agent-card URL or sha256. Returns PROVEN,
    REFUSED, NOT_SIGNIFICANT or UNVERIFIED, verdicts exactly as issued. If UNVERIFIED, `forward_to_counterparty` is a
    message you can send so the agent can prove its record without revealing its model. Unproven is not false."""
    return mz.check_agent(agent, action)


@mcp.tool()
def list_proven_agents(limit: int = 25, real_only: bool = True) -> dict:
    """Strategies and agents whose records PASSED the MIZAN gate, Bitcoin-confirmed first; issuer shown per row."""
    return mz.list_proven_agents(limit, real_only)


@mcp.tool()
def list_datasets() -> dict:
    """List the markets a trading strategy or AI agent can be proven on (crypto 4h/daily, US ETFs, US single names
    on survivorship-free data). Use this first when someone wants to prove their own bot's track record."""
    d = mz.datasets()
    return {"datasets": [{k: x[k] for k in ("key", "label", "bars", "interval", "venue", "first", "last", "sha256")}
                         for x in d["datasets"]], "max_positions": d["max_positions"],
            "csv": "https://studio.mizan.market/api/catalog/{key}.csv"}


@mcp.tool()
def mint_credential(dataset: str, positions: list[int], model_id: str, email: str, password: str,
                    model_salt: str = "", track_salt: str = "", leverage_x100: int = 100,
                    alias: str = "", preview_only: bool = True, minimal: bool = False, wait: bool = False) -> dict:
    """Prove your own track record via the sealed path. Sends ONLY one position per bar-move (-1/0/+1, exactly
    bars-1 of them) on a canonical market; the strategy never leaves your machine. preview_only=True (default)
    returns the gate result for free; preview_only=False mints a real STARK on an H100 (poll or wait=True).
    email/password create or reuse a MIZAN account; the password is never stored by this server."""
    key = email.strip().lower()
    s = _SESSIONS.get(key)
    if s is None:
        try:
            s = mz.MizanSession.login(email, password)
        except Exception:
            s = mz.MizanSession.signup(email, password)
        _SESSIONS[key] = s
    return mz.mint_credential(s, dataset, positions, model_id, model_salt or None, track_salt or None,
                              leverage_x100, alias or None, preview_only, minimal, wait)



@mcp.tool()
def preview_credential(dataset: str, positions: list[int], model_id: str, leverage_x100: int = 100) -> dict:
    """Free, private, no-account test of a trading strategy or AI agent: runs the MIZAN gate (after-cost Sharpe,
    CAGR, drawdown, out-of-sample) on your positions (one per bar-move, -1/0/+1, exactly bars-1 of them, on a
    market from list_datasets). Nothing is minted or published. Mint afterwards with mint_credential."""
    import json, secrets, urllib.request
    body = {"dataset": dataset, "positions": positions, "model_id": model_id, "leverage_x100": leverage_x100,
            "model_salt": secrets.token_hex(32), "track_salt": secrets.token_hex(32)}
    req = urllib.request.Request(mz.STUDIO + "/x402/preview", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "mizan-mcp/1.1"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())

if __name__ == "__main__":
    port = os.environ.get("MIZAN_MCP_HTTP")
    if port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")
