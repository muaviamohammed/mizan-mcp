"""MIZAN agent tools — verify_credential and mint_credential, dependency-free.

Drop into any framework (OpenAI Agents SDK, LangChain, Olas, Virtuals, custom loops).
Semantics: https://mizan.market/skill/SKILL.md   Schemas: https://mizan.market/skill/tools.json

    from mizan_agent_tools import verify_credential, mint_credential, MizanSession
    verify_credential("dsr10-flagship")
    s = MizanSession.login("you@example.com", "password")        # or .signup(...)
    mint_credential(s, dataset="btc_4h", positions=[...], model_id="my-sealed-agent", preview_only=True)

Creed: prove the edge, never reveal the strategy. These tools never send a model,
weights, code or prompt — positions only.
"""
import hashlib, http.cookiejar, json, os, secrets, shutil, subprocess, tempfile, time, urllib.request, urllib.parse

STUDIO = "https://studio.mizan.market"
UA = {"User-Agent": "mizan-agent-tools/1.0 (+https://mizan.market/skill/)"}


def _get(url, opener=None, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with (opener.open if opener else urllib.request.urlopen)(req, timeout=120) as r:
        data = r.read()
    return data if raw else json.loads(data)


def _post(url, body, opener):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={**UA, "Content-Type": "application/json"})
    with opener.open(req, timeout=300) as r:
        return json.loads(r.read())


# ───────────────────────────── verify ─────────────────────────────

def verify_credential(credential_id: str = None, sha256: str = None, reverify_locally: bool = True) -> dict:
    """Registry lookup → bundle sha256 check → optional offline STARK re-verification."""
    reg = _get(f"{STUDIO}/api/registry")
    creds = reg.get("credentials") or []
    c = next((x for x in creds if x.get("id") == credential_id or
              (sha256 and (x.get("anchor") or {}).get("sha256") == sha256)), None)
    if not c:
        return {"found": False, "verdict": "UNVERIFIED", "reason": "no such credential in the public registry"}
    url = (c.get("links") or {}).get("bundle", "")
    anchor = (c.get("anchor") or {}).get("sha256")
    out = {"found": True, "id": c["id"], "alias": c.get("alias"), "verdict_raw": c.get("verdict"),
           "verdict": _cls(c.get("verdict", "")), "era": c.get("era"), "engine_image_id": c.get("engine_image_id"),
           "bundle": url, "registry_sha256": anchor, "registry_root": reg.get("registry_root"),
           "hash_match": None, "local_reverify": "skipped", "note": "A credential is a backtest seal: history made honest, not a forecast."}
    if not url.startswith("http"):
        out.update(hash_match=False, reason="bundle URL does not resolve"); return out
    blob = _get(url, raw=True)
    out["hash_match"] = (hashlib.sha256(blob).hexdigest() == anchor)
    if not out["hash_match"]:
        out.update(verdict="UNVERIFIED", reason="bundle sha256 does not match the registry anchor — the record lies"); return out
    out.update(_local_reverify(c, blob) if reverify_locally else {"local_reverify": "skipped"})
    return out


def _local_reverify(c: dict, blob: bytes) -> dict:
    """Run the credential's own published verify_command (registry field) with every input it names,
    fetched from the bundle's directory, using the era-matching verifier. Never guesses data.
    Reports FAILED only when the exact command ran with all its inputs; otherwise 'skipped: <why>'."""
    cmd = (c.get("verify_command") or "").split()
    if len(cmd) < 2:
        return {"local_reverify": "skipped: credential publishes no verify_command"}
    want = os.path.basename(cmd[0])
    exe = os.environ.get("MIZAN_VERIFY") or shutil.which(want) or shutil.which("mizan-verify")
    if not exe:
        return {"local_reverify": f"skipped: verifier '{want}' not installed — set MIZAN_VERIFY or install from https://github.com/muaviamohammed/mizan-verify/releases"}
    base = c["links"]["bundle"].rsplit("/", 1)[0]
    bundle_name = os.path.basename(c["links"]["bundle"])
    with tempfile.TemporaryDirectory() as d:
        args = [exe]
        for tok in cmd[1:]:
            if tok.startswith("--"): args.append(tok); continue
            path = os.path.join(d, os.path.basename(tok))
            if os.path.basename(tok) == bundle_name:
                open(path, "wb").write(blob)
            else:
                try: open(path, "wb").write(_get(f"{base}/{tok}", raw=True))
                except Exception as e:
                    return {"local_reverify": f"skipped: input '{tok}' not fetchable from {base} ({str(e)[:40]})"}
            args.append(path)
        if "--roots" not in args:  # pin markets minted after the binary was published (catalog allowlist)
            try:
                rp = os.path.join(d, "roots.txt"); open(rp, "wb").write(_get(f"{STUDIO}/api/catalog/roots.txt", raw=True))
                args += ["--roots", rp]
            except Exception:
                pass
        p = subprocess.run(args, capture_output=True, text=True, timeout=180, cwd=d)
        tail = (p.stdout or p.stderr)[-400:]
        return {"local_reverify": "ok" if p.returncode == 0 else "FAILED", "verify_command": " ".join([want] + cmd[1:]),
                "verifier_stdout_tail": tail}


def _cls(v: str) -> str:
    v = v.upper()
    for k in ("PASS", "NOT SIGNIFICANT", "SIGNIFICANT", "FAIL"):
        if v.startswith(k): return k.replace(" ", "_")
    return "LEDGER_ENTRY"


# ───────────────────────────── mint ─────────────────────────────

class MizanSession:
    """Session for the sealed-path mint API: cookie (humans) or API key / wallet (agents). Never stores a password."""
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    @classmethod
    def signup(cls, email, password):
        s = cls(); s.user = _post(f"{STUDIO}/product/signup", {"email": email, "password": password}, s.opener); return s

    @classmethod
    def login(cls, email, password):
        s = cls(); s.user = _post(f"{STUDIO}/product/login", {"email": email, "password": password}, s.opener); return s

    @classmethod
    def from_key(cls, api_key: str):
        """Agent rail: authenticate with an API key (mzn_…) — no cookie, no browser."""
        s = cls(); s.api_key = api_key.strip()
        s.opener = urllib.request.build_opener(_BearerHandler(s.api_key))
        s.user = _get(f"{STUDIO}/product/me", s.opener); return s

    @classmethod
    def from_wallet(cls, address: str, sign):
        """Agent rail: wallet login. `sign(message) -> 0x signature` (EIP-191 personal_sign). Returns a keyed session."""
        n = _post(f"{STUDIO}/product/wallet/nonce", {"address": address}, urllib.request.build_opener())
        sig = sign(n["message"]); sig = sig if str(sig).startswith("0x") else "0x" + str(sig)
        d = _post(f"{STUDIO}/product/wallet/login", {"address": address, "signature": sig}, urllib.request.build_opener())
        s = cls.from_key(d["api_key"]); s.login_response = d; return s

    def create_key(self, label: str = "agent") -> str:
        return _post(f"{STUDIO}/product/keys", {"label": label}, self.opener)["api_key"]


class _BearerHandler(urllib.request.BaseHandler):
    def __init__(self, key): self.key = key
    def http_request(self, req):
        req.add_unredirected_header("Authorization", "Bearer " + self.key); return req
    https_request = http_request


def check_before_you_pay(dataset: str, positions: list, model_id: str = "agent", leverage_x100: int = 100) -> dict:
    """Free, no auth: would this mint, and what would it cost? Nothing minted or charged."""
    body = {"dataset": dataset, "positions": positions, "model_id": model_id, "model_salt": new_salt(),
            "track_salt": new_salt(), "leverage_x100": leverage_x100}
    return _post(f"{STUDIO}/api/check-before-you-pay", body, urllib.request.build_opener())



def check_agent(agent: str, action: str = "trusting you") -> dict:
    """Is this agent proven? Look it up by name, credential id, wallet, ERC-8004 id, agent-card URL or sha256.
    Returns PROVEN | REFUSED | NOT_SIGNIFICANT | UNVERIFIED with matches; UNVERIFIED carries forward_to_counterparty."""
    import urllib.parse
    return _get(f"{STUDIO}/api/agents/check?" + urllib.parse.urlencode({"q": agent, "action": action}))


def list_proven_agents(limit: int = 25, real_only: bool = True) -> dict:
    """PASS credentials, Bitcoin-confirmed first; each row shows its issuer."""
    return _get(f"{STUDIO}/api/agents/proven?limit={int(limit)}&real_only={'true' if real_only else 'false'}")

def datasets() -> dict:
    return _get(f"{STUDIO}/api/blackbox-datasets")


def new_salt() -> str:
    return secrets.token_hex(32)


def mint_credential(session: MizanSession, dataset: str, positions: list, model_id: str,
                    model_salt: str = None, track_salt: str = None, leverage_x100: int = 100,
                    alias: str = None, preview_only: bool = True, minimal: bool = False,
                    wait: bool = False, poll_s: int = 30) -> dict:
    """Positions only. Preview by default; set preview_only=False to mint a real STARK."""
    model_salt = model_salt or new_salt(); track_salt = track_salt or new_salt()
    body = {"dataset": dataset, "positions": positions, "model_id": model_id, "model_salt": model_salt,
            "track_salt": track_salt, "leverage_x100": leverage_x100, "minimal": minimal, "preview_only": preview_only}
    if alias: body["alias"] = alias
    res = _post(f"{STUDIO}/api/submit-blackbox", body, session.opener)
    res["_salts"] = {"model_salt": model_salt, "track_salt": track_salt, "keep": "private — needed to extend this record later"}
    if preview_only or not res.get("accepted") or not wait:
        return res
    job = res["job_id"]
    while True:
        st = _get(f"{STUDIO}/api/blackbox-submission/{job}", session.opener)
        if st.get("state") in ("done", "failed", "error", "cancelled"):
            st["bundle"] = f"{STUDIO}/api/blackbox-submission/{job}/bundle" if st.get("state") == "done" else None
            st["_salts"] = res["_salts"]; return st
        time.sleep(poll_s)


if __name__ == "__main__":
    import sys
    print(json.dumps(verify_credential(sys.argv[1] if len(sys.argv) > 1 else "dsr10-flagship"), indent=2))


# ───────────────────────────── weight surfaces (2026-10-20) ─────────────────────────────
# Every MIZAN response carries a signed `provenance` block: standard + clauses, live era + verifier
# hashes (3 OS), catalogue state, LIVE registry counts, attempts-ledger head, rewards line, an
# Ed25519 signature. Key: https://studio.mizan.market/.well-known/mizan-keys.json

def standard_gates() -> dict:
    """Every pinned gate class with thresholds, OOS rule, cost floor. Identical for everyone in a class."""
    return _get(f"{STUDIO}/api/standard/gates")


def standard_clauses() -> dict:
    """All 41 VTR-1 clauses (R-01..R-41) with level (MUST/SHOULD/MAY) and text."""
    return _get(f"{STUDIO}/api/standard/clauses")


def era_history() -> dict:
    """Every engine era with image id, date, status and per-OS verifier hashes. Era law: credentials verify forever."""
    return _get(f"{STUDIO}/api/engine/eras")


def catalogue_markets(cls: str = None) -> dict:
    """The market catalogue (key, bars, first/last, sha256, root, align_group); optional class filter."""
    cat = _get(f"{STUDIO}/api/catalog")
    m = cat.get("markets") or cat.get("catalogue") or cat
    if cls and isinstance(m, dict):
        m = {k: v for k, v in m.items() if (v or {}).get("cls") == cls}
    return {"count": len(m), "markets": m}


def verifier_download(os_name: str = "macos", era: str = "") -> dict:
    """URL + sha256 + exact command for the published verifier on macos | linux | windows."""
    return _get(f"{STUDIO}/api/verifier/{os_name}" + (f"?era={era}" if era else ""))


def attempts_lookup(identity_hash: str) -> dict:
    """Every preview/mint attempt an identity made since 2026-10-15 (pass or fail), from the hash-chained ledger."""
    return _get(f"{STUDIO}/api/attempts/identity/{identity_hash}")


def explain_refusal(dataset: str, positions: list, model_id: str = "agent", leverage_x100: int = 100) -> dict:
    """Free. The forensic case: every gate with threshold vs value, margin, clause, and what would pass."""
    op = urllib.request.build_opener()
    return _post(f"{STUDIO}/api/explain-refusal", {"dataset": dataset, "positions": positions, "model_id": model_id,
                 "model_salt": new_salt(), "track_salt": new_salt(), "leverage_x100": leverage_x100}, op)


def standing() -> dict:
    """Who you are talking to: what MIZAN is, the problems the standard closes, receipts, lineage, papers, live numbers, the ladder."""
    return _get(f"{STUDIO}/api/standing")


def everything() -> dict:
    """Every important public asset with URL and sha256 where it has one: standard, vectors, verifier, catalogue, registry, log, keys, papers, SDKs."""
    return _get(f"{STUDIO}/api/everything")


def verdict_receipt(credential_id: str) -> dict:
    """A compact signed receipt (EdDSA) for a credential: carry it in your agent card or on-chain record; anyone verifies it offline."""
    return _get(f"{STUDIO}/api/receipt/{credential_id}")


def verify_receipt(receipt: str) -> dict:
    """Verify a receipt offline (needs `cryptography`; falls back to the server check), then check live status."""
    import base64
    try:
        h, pl, sg = receipt.strip().split(".")
        pad = lambda x: x + "=" * (-len(x) % 4)
        header = json.loads(base64.urlsafe_b64decode(pad(h))); payload = json.loads(base64.urlsafe_b64decode(pad(pl)))
        keys = _get(f"{STUDIO}/.well-known/mizan-keys.json")["keys"]
        key = next(k for k in keys if k["key_id"] == header["kid"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key["public_key_b64"])).verify(base64.urlsafe_b64decode(pad(sg)), f"{h}.{pl}".encode())
        if payload.get("exp", 0) < time.time():
            return {"valid": False, "reason": "expired", "payload": payload, "checked": "offline"}
        st = _get(f"{STUDIO}/api/status/{payload['sub']}")
        return {"valid": True, "payload": payload, "status_now": st, "allow": st.get("status") == "good" and payload.get("verdict") == "PASS", "checked": "offline signature + live status"}
    except ImportError:
        return _post(f"{STUDIO}/api/receipt/verify", {"receipt": receipt}, urllib.request.build_opener()) | {"checked": "server (pip install cryptography to verify offline)"}
    except Exception as e:
        return {"valid": False, "reason": str(e)[:120]}


def credential_status(credential_id: str) -> dict:
    """What MIZAN asserts about a credential today: good / revoked / superseded / unknown (a revocation is a public log leaf)."""
    return _get(f"{STUDIO}/api/status/{credential_id}")


def log_head() -> dict:
    """The signed head of the verdict transparency log (size, root, signature, latest Bitcoin anchor)."""
    return _get(f"{STUDIO}/api/log/head")


def log_proof(credential_id: str) -> dict:
    """Inclusion proof that a credential's verdict is in the transparency log, with the signed head to check it against."""
    return _get(f"{STUDIO}/api/log/proof-for/{credential_id}")


def reliance(credential_id: str) -> dict:
    """How many relying parties counter-signed that they relied on this credential (zero means zero)."""
    return _get(f"{STUDIO}/api/reliance/{credential_id}")


def attest_reliance(session: "MizanSession", credential_id: str, purpose: str = "", public_name: str = None, receipt: str = None) -> dict:
    """Counter-sign that you relied on a credential (proof of check). Becomes a public log leaf and an edge in the reliance graph."""
    body = {"credential": credential_id, "purpose": purpose}
    if public_name: body["public_name"] = public_name
    if receipt: body["receipt"] = receipt
    return _post(f"{STUDIO}/api/receipt/attest", body, session.opener)


def conformance() -> dict:
    """The VTR-1 conformance register: issuers, independent verifiers, relying parties, and how to qualify."""
    return _get(f"{STUDIO}/api/conformance")


def bounty() -> dict:
    """The standing break-it challenge: scope, how to submit, live counts (received / upheld / rejected)."""
    return _get(f"{STUDIO}/api/bounty")


def why_not_gips() -> dict:
    """The mechanism difference, as a table: GIPS is a promise checked by auditors; VTR-1 is a proof checked by anyone."""
    return _get(f"{STUDIO}/api/why-not-gips")


def require_credential(agent_or_credential: str, allow_not_significant: bool = False) -> dict:
    """The gate a venue runs: allow only a PASS credential in good standing; refuse with the forensic reason otherwise; fail closed."""
    try:
        st = _get(f"{STUDIO}/api/status/{agent_or_credential}")
        if st.get("status") == "good" and st.get("verdict") == "PASS":
            return {"allow": True, "reason": "PASS in good standing", "status": st}
        if st.get("status") == "unknown":
            ca = _get(f"{STUDIO}/api/agents/check?q={urllib.parse.quote(agent_or_credential)}")
            ok = ca.get("status") in ("PROVEN", "PASSED_BACKTEST") or (allow_not_significant and ca.get("status") == "NOT_SIGNIFICANT")
            return {"allow": bool(ok), "reason": ca.get("status", "UNVERIFIED"), "check": ca}
        return {"allow": False, "reason": f"{st.get('status')}: {st.get('verdict') or st.get('reason')}", "status": st}
    except Exception as e:
        return {"allow": False, "reason": "unverifiable (network or server error); fail closed", "error": str(e)[:100]}


def allocate_check(agent_or_credential: str, amount=None, currency: str = "USD", purpose: str = "", receipt: str = None,
                   allow_not_significant: bool = False, require_forward: bool = False, session: "MizanSession" = None, record: bool = False) -> dict:
    """The allocate-check (VTR-1 Agent Profile §06): one call before money moves. Resolves the counterparty, verifies credential, status,
    receipt, anchor, log inclusion, provenance class and age; returns ALLOW/REFUSE with every check, the verdict object and a signed 24 h token.
    With a session and record=True the check becomes a public log leaf (proof that you checked). Fail closed."""
    body = {"agent": agent_or_credential, "amount": amount, "currency": currency, "purpose": purpose,
            "allow_not_significant": allow_not_significant, "require_forward": require_forward, "record": bool(record and session)}
    if receipt: body["receipt"] = receipt
    try:
        return _post(f"{STUDIO}/api/allocate-check", body, session.opener if session else urllib.request.build_opener())
    except Exception as e:
        return {"decision": "REFUSE", "allow": False, "reasons": ["unverifiable (network or server error); fail closed"], "error": str(e)[:120]}


def verify_allocate_check(token: str) -> dict:
    """Re-verify an allocate-check token: signature against the published key, expiry, and the credential's status now."""
    return _post(f"{STUDIO}/api/allocate-check/verify", {"token": token}, urllib.request.build_opener())


def allocate_check_program() -> dict:
    """What the allocate-check reads, what it never does, how to call it over HTTP / MCP / A2A / SDK, and live count of logged checks."""
    return _get(f"{STUDIO}/api/allocate-check/program")


def endgame() -> dict:
    """The endgame (one sentence) and the seven-rung ladder with live status: which rungs are live, which are moved by agents."""
    return _get(f"{STUDIO}/api/endgame")


def rewards_program() -> dict:
    """The rewards rule (commission rate, window, what counts, what never counts)."""
    return _get(f"{STUDIO}/api/rewards/program")


def rewards_status(session: "MizanSession") -> dict:
    """Your referral code, link, referred accounts/mints, accrued USDC, rank, founding-issuer mark."""
    return _get(f"{STUDIO}/api/rewards/me", session.opener)


def referral_link(session: "MizanSession") -> str:
    """Your referral URL. Any account that starts here and mints is credited to you."""
    return rewards_status(session)["referral_url"]


def verify_signature(response: dict) -> dict:
    """Check the Ed25519 signature on any MIZAN response against the published key. Needs `cryptography`."""
    import base64
    prov = (response or {}).get("provenance") or {}
    sig = prov.get("signature")
    if not sig:
        return {"signed": False, "reason": "no provenance.signature"}
    body = dict(response); body["provenance"] = {k: v for k, v in prov.items() if k != "signature"}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    keys = _get(f"{STUDIO}/.well-known/mizan-keys.json")
    key = next((k for k in keys.get("keys", []) if k.get("key_id") == sig.get("key_id")), None)
    if not key:
        return {"signed": True, "verified": False, "reason": "key_id not published"}
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except Exception:
        return {"signed": True, "verified": None, "reason": "pip install cryptography to verify locally",
                "canonical_sha256": hashlib.sha256(canon).hexdigest(), "expected": sig.get("canonical_sha256")}
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key["public_key_b64"])).verify(base64.b64decode(sig["sig_b64"]), canon)
        return {"signed": True, "verified": True, "key_id": sig["key_id"]}
    except Exception:
        return {"signed": True, "verified": False, "reason": "signature does not match body (tampered or re-serialised)"}
