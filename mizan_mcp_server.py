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


def _session():
    k = os.environ.get("MIZAN_API_KEY", "")
    if not k:
        raise RuntimeError("set MIZAN_API_KEY (mzn_…)")
    return mz.MizanSession.from_key(k)
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
def mint_credential(dataset: str, positions: list[int], model_id: str, email: str = "", password: str = "",
                    model_salt: str = "", track_salt: str = "", leverage_x100: int = 100,
                    alias: str = "", preview_only: bool = True, minimal: bool = False, wait: bool = False, api_key: str = "") -> dict:
    """Prove your own track record via the sealed path. Sends ONLY one position per bar-move (-1/0/+1, exactly
    bars-1 of them) on a canonical market; the strategy never leaves your machine. preview_only=True (default)
    returns the gate result for free; preview_only=False mints a real STARK on an H100 (poll or wait=True).
    email/password create or reuse a MIZAN account; the password is never stored by this server."""
    if api_key:
        s = mz.MizanSession.from_key(api_key)
        return mz.mint_credential(s, dataset, positions, model_id, model_salt or None, track_salt or None,
                                  leverage_x100, alias or None, preview_only, minimal, wait)
    if not email or not password:
        return {"error": "pass api_key (POST /product/keys or /product/wallet/login) or email + password"}
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
def check_before_you_pay(dataset: str, positions: list[int], model_id: str = "agent", leverage_x100: int = 100) -> dict:
    """Free, no account. Runs the MIZAN gate on your positions and returns would_mint plus price: the exact cost of a
    real credential right now ($0 during the founding cohort; USDC on Base via x402 once paid minting opens).
    Nothing is minted, stored or charged. Call before mint_credential."""
    return mz.check_before_you_pay(dataset, positions, model_id, leverage_x100)


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


# ───────────── weight surfaces (2026-10-20) — same tools as the remote server ─────────────
@mcp.tool()
def standard_gates() -> dict:
    """The pinned gate classes (DIRECTIONAL-V2, MARKET-NEUTRAL-V2): every threshold, the OOS rule, the cost floor. Identical for everyone in a class (VTR-1 R-37)."""
    return mz.standard_gates()


@mcp.tool()
def standard_clauses() -> dict:
    """All 41 VTR-1 clauses (R-01..R-41): id, MUST/SHOULD/MAY, group, text."""
    return mz.standard_clauses()


@mcp.tool()
def era_history() -> dict:
    """Every engine era (image id, date, status, verifier hashes per OS). Era law: a credential verifies forever under the era that minted it."""
    return mz.era_history()


@mcp.tool()
def catalogue_markets(cls: str = "") -> dict:
    """The canonical market catalogue (key, bars, first/last bar, sha256, Merkle root, align group). Optional class filter."""
    return mz.catalogue_markets(cls or None)


@mcp.tool()
def verifier_download(os_name: str = "macos", era: str = "") -> dict:
    """URL, sha256 and the exact command for the published verifier on macos | linux | windows. Exit 0 = verified, exit 1 = refused."""
    return mz.verifier_download(os_name, era)


@mcp.tool()
def attempts_lookup(identity_hash: str) -> dict:
    """Every preview and mint attempt an identity made (pass or fail) since 2026-10-15, from the public hash-chained attempts ledger."""
    return mz.attempts_lookup(identity_hash)


@mcp.tool()
def explain_refusal(dataset: str, positions: list[int], model_id: str = "agent", leverage_x100: int = 100) -> dict:
    """Free, nothing charged. The forensic case: every pinned gate with threshold vs value, margin, the VTR-1 clause, and what would pass. A short record is accepted: it is placed at the end of the catalogue window with earlier bars flat (disclosed in `padding`)."""
    return mz.explain_refusal(dataset, positions, model_id, leverage_x100)


@mcp.tool()
def standing() -> dict:
    """Who you are talking to: what MIZAN is, the nine problems the standard closes, receipts, lineage, papers, live counts, the ladder."""
    return mz.standing()


@mcp.tool()
def everything() -> dict:
    """Every important public asset with URL and sha256 where it has one."""
    return mz.everything()


@mcp.tool()
def verdict_receipt(credential_id: str) -> dict:
    """Signed verdict receipt (EdDSA) to carry in an agent card or on-chain record; verified offline with the published key."""
    return mz.verdict_receipt(credential_id)


@mcp.tool()
def verify_receipt(receipt: str) -> dict:
    """Verify a receipt (signature, expiry, live status). allow=true only for PASS in good standing."""
    return mz.verify_receipt(receipt)


@mcp.tool()
def credential_status(credential_id: str) -> dict:
    """good / revoked (reason, log index) / superseded / unknown. Revocations are public log leaves."""
    return mz.credential_status(credential_id)


@mcp.tool()
def log_head() -> dict:
    """Signed head of the verdict transparency log; heads anchored to Bitcoin."""
    return mz.log_head()


@mcp.tool()
def log_proof(credential_id: str) -> dict:
    """RFC 6962 inclusion proof for a credential's verdict."""
    return mz.log_proof(credential_id)


@mcp.tool()
def reliance(credential_id: str) -> dict:
    """How many relying parties counter-signed reliance on this credential (zero means zero)."""
    return mz.reliance(credential_id)


@mcp.tool()
def attest_reliance(credential_id: str, purpose: str = "", public_name: str = "", receipt: str = "") -> dict:
    """Proof of check: counter-sign that you relied on a credential. Public log leaf + reliance-graph edge. Uses MIZAN_API_KEY."""
    return mz.attest_reliance(_session(), credential_id, purpose, public_name or None, receipt or None)


@mcp.tool()
def require_credential(agent_or_credential: str, allow_not_significant: bool = False) -> dict:
    """The gate a venue runs: allow only PASS in good standing; fail closed."""
    return mz.require_credential(agent_or_credential, allow_not_significant)


@mcp.tool()
def allocate_check(agent_or_credential: str, amount: float | None = None, currency: str = "USD", purpose: str = "", receipt: str = "",
                   allow_not_significant: bool = False, require_forward: bool = False, record: bool = False) -> dict:
    """The allocate-check (VTR-1 Agent Profile §06): one call before money moves. ALLOW/REFUSE with every check, the verdict object and a signed 24 h token. Fail closed. record=true logs the check as a public leaf (uses MIZAN_API_KEY)."""
    sess = None
    if record:
        try: sess = _session()
        except Exception: sess = None
    return mz.allocate_check(agent_or_credential, amount, currency, purpose, receipt or None, allow_not_significant, require_forward, sess, record)


@mcp.tool()
def verify_allocate_check(token: str) -> dict:
    """Re-verify an allocate-check token: signature, expiry, status now (still_allow)."""
    return mz.verify_allocate_check(token)


@mcp.tool()
def conformance() -> dict:
    """The VTR-1 conformance register and how a second issuer qualifies."""
    return mz.conformance()


@mcp.tool()
def bounty() -> dict:
    """The standing break-it challenge; every submission is a public log leaf; live counts."""
    return mz.bounty()


@mcp.tool()
def why_not_gips() -> dict:
    """GIPS is a promise checked by auditors; VTR-1 is a proof checked by anyone (the table)."""
    return mz.why_not_gips()


@mcp.tool()
def endgame() -> dict:
    """The endgame in one sentence and the seven-rung ladder with live status per rung: what is live, what is open, what an agent does to move it."""
    return mz.endgame()


@mcp.tool()
def rewards_program() -> dict:
    """MIZAN Agent Rewards: bring an agent that mints, earn a commission on what it pays (USDC on Base), plus free mints, a Founding Issuer mark and a public rank."""
    return mz.rewards_program()


@mcp.tool()
def rewards_status(api_key: str) -> dict:
    """Your referral code and link, referred accounts and mints, accrued USDC, rank and Founding Issuer mark. Needs your API key (mzn_…)."""
    return mz.rewards_status(mz.MizanSession.from_key(api_key))


@mcp.tool()
def verify_signature(response: dict) -> dict:
    """Verify the Ed25519 signature on any MIZAN response against the published key."""
    return mz.verify_signature(response)


if __name__ == "__main__":
    port = os.environ.get("MIZAN_MCP_HTTP")
    if port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")
