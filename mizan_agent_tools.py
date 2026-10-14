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
import hashlib, http.cookiejar, json, os, secrets, shutil, subprocess, tempfile, time, urllib.request

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
    """Cookie session for the sealed-path mint API. Never stores the password."""
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    @classmethod
    def signup(cls, email, password):
        s = cls(); s.user = _post(f"{STUDIO}/product/signup", {"email": email, "password": password}, s.opener); return s

    @classmethod
    def login(cls, email, password):
        s = cls(); s.user = _post(f"{STUDIO}/product/login", {"email": email, "password": password}, s.opener); return s


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
