# Aureon Security Hardening

Security review applied per Aureon brain corpus, with patterns adapted from [nomad_cyber_algorithm](https://github.com/ZorakCorp/nomad_cyber_algorithm).

## Production checklist

1. Set **`AUREON_API_KEY`** on Railway — all `POST` training/brain/pipeline endpoints require `X-API-Key`.
2. Set **`AUREON_AUDIT_CHAIN_KEY`** (64 hex chars) — durable HMAC key for tamper-evident audit log.
3. Set **`DATABASE_URL`** to PostgreSQL (not SQLite) for multi-worker deployments.
4. Set **`ALERT_WEBHOOK_URL`** only to trusted HTTPS endpoints (internal IPs blocked).
5. Do not expose Railway Postgres publicly.
6. Monitor **`GET /organism/vitals`** — organism lockdown blocks mutating operations when any organ is critical.

## Nomad-inspired layers (adapted for Aureon-LLM)

| Nomad concept | Aureon implementation |
|---------------|----------------------|
| Organism vitals | `GET /organism/vitals` — auth, audit chain, rate limits, DB |
| Audit immune chain | HMAC-chained JSONL log in `data/audit/` |
| Rate limit nerves | Per-IP sliding window on mutating routes (default 30/min) |
| Replay guard | `X-Timestamp` + `X-Nonce` + `X-Correlation-ID` when API key set |
| Gateway lockdown | 503 `ORGANISM_LOCKDOWN` when critical organ fails |
| Correlation IDs | `X-Correlation-ID` echoed on every response |
| Body size cap | 413 when `Content-Length` exceeds limit |

**Not ported** (TypeScript/PQC-specific): Kyber1024, Dilithium5, imperial cipher stack, WebAuthn console, HSM/TPM attestation, Redis distributed limits.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AUREON_API_KEY` | Required in production for mutating endpoints |
| `AUREON_AUDIT_CHAIN_KEY` | 32-byte hex HMAC key for audit chain |
| `AUREON_AUDIT_LOG_DIR` | Audit log directory (default `data/audit`) |
| `AUREON_RATE_LIMIT_PER_MINUTE` | Mutating requests per IP per minute (default 30) |
| `AUREON_REPLAY_GUARD` | Set `0` to disable replay headers (dev only) |
| `AUREON_AUTO_LEARN` | `1` on Railway by default — background grade learning |
| `AUREON_AUTO_LEARN_INTERVAL_SEC` | Seconds between auto-learn cycles (default 3600) |

## Automated learning (Railway)

When `RAILWAY_ENVIRONMENT` is detected, background learning starts without manual API calls. It rotates through micro-subdomains and advances one grade level per cycle. Disable with `AUREON_AUTO_LEARN=0`. Monitor at `GET /api/brain/auto-learn`.

## Fixes applied

| Issue | Severity | Fix |
|-------|----------|-----|
| Unauthenticated expensive POST endpoints | Critical | API key auth via `AUREON_API_KEY` |
| DoS via unbounded `subdomain_limit` | High | Capped at 20; domain at 29 |
| DoS via concurrent training jobs | High | Exclusive training lock (429) |
| DoS via request floods | High | IP rate limiting on mutating routes |
| Replay of signed requests | Medium | Timestamp + nonce guard |
| Audit tampering undetected | Medium | HMAC-chained audit log + organism pulse |
| Error messages leak internals | Medium | Generic client errors; server-side logging |
| Webhook SSRF | High | Block localhost/private IPs in `ALERT_WEBHOOK_URL` |
| Path traversal in local inbox | High | `resolve_path_under()` |
| Unbounded JSON/model load | Medium | Size limits + payload validation |
| Missing security headers | Medium | CSP, X-Frame-Options, nosniff |
| PostgreSQL pool exhaustion | Medium | pool_size + recycle |

## Client usage with API key

```bash
TS=$(python -c "import time; print(int(time.time()*1000))")
NONCE=$(python -c "import secrets; print(secrets.token_hex(16))")
CID="curl-$(date +%s)"

curl -X POST "https://your-app.railway.app/api/brain/run" \
  -H "X-API-Key: your-secret-key" \
  -H "X-Timestamp: $TS" \
  -H "X-Nonce: $NONCE" \
  -H "X-Correlation-ID: $CID"
```

In browser (optional): set `window.AUREON_API_KEY` before clicking buttons — replay headers are added automatically.

## Organism vitals

```bash
curl https://your-app.railway.app/organism/vitals
```

Returns `vital`, `lockdown_reason`, per-organ state, and `organism_fingerprint`.
