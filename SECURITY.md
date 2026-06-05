# Aureon Security Hardening

Security review applied per Aureon brain corpus, with patterns adapted from [nomad_cyber_algorithm](https://github.com/ZorakCorp/nomad_cyber_algorithm).

## Sovereign organism (11 organs)

Aureon implements the **nomad sovereign organism** model — interlocking security organs with dependency ordering. Partial compromise triggers lockdown on mutating HTTP routes.

| Nomad organ | Aureon organ | Implementation |
|-------------|--------------|----------------|
| Supply Spleen | `supply_spleen` | `requirements.txt` SHA-256 at startup |
| Audit Immune | `audit_immune` | HMAC-chained JSONL audit log |
| Bootstrap Heart | `bootstrap_heart` | Railway secret/database auto-bootstrap |
| Auth Gateway | `auth_gateway` | `AUREON_API_KEY` on mutating routes |
| Replay Cortex | `replay_guard` | `X-Timestamp` + `X-Nonce` + correlation ID |
| Rate Nerves | `rate_limit_nerves` | Per-IP sliding window (default 30/min) |
| Database Marrow | `database_marrow` | PostgreSQL / SQLite connectivity |
| Training Spleen | `training_lock` | Exclusive training lock (429 when busy) |
| Gateway Skin | `gateway_skin` | Security middleware + headers |
| Vault Marrow | `vault_marrow` | Secrets file bound to organism fingerprint |
| Activity Lungs | `activity_lungs` | Structured AI activity logs (Railway) |

**Not ported** (TypeScript/PQC-specific): Kyber1024, Dilithium5, imperial cipher stack, WebAuthn console, HSM/TPM attestation, Redis distributed limits.

## Security API

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /security/doctrine` | Public | Nomad doctrine + organ roles |
| `GET /security/status` | Public | Full organism vitals + stack metadata |
| `GET /security/audit` | API key | Tamper-evident audit log tail |
| `POST /security/pulse` | API key + replay | Force organism pulse |
| `GET /organism/vitals` | Public | Legacy vitals (same organism) |

## Production checklist

1. Deploy on Railway — `app/railway_env.py` auto-provisions `AUREON_API_KEY`, `AUREON_AUDIT_CHAIN_KEY`, and SQLite if Postgres is not linked.
2. Attach **Railway Postgres** and set `DATABASE_URL=${{Postgres.DATABASE_URL}}` for durable multi-replica brain state.
3. Mount a **volume** at `/data` (or set `AUREON_DATA_DIR=/data`) so secrets and SQLite survive redeploys.
4. Optional: pin dependencies with `AUREON_REQUIREMENTS_SHA256=<sha256 of requirements.txt>`.
5. Optional: restrict clients with `AUREON_CLIENT_ALLOWLIST=<sha256(api_key)>,...`.
6. Monitor `GET /security/status` — organism lockdown blocks mutating operations when critical organs fail.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AUREON_API_KEY` | Mutating endpoint auth (auto-generated on Railway if unset) |
| `AUREON_AUDIT_CHAIN_KEY` | 32-byte hex HMAC audit chain key |
| `AUREON_AUDIT_LOG_DIR` | Audit log directory |
| `AUREON_RATE_LIMIT_PER_MINUTE` | Mutating requests per IP per minute (default 30) |
| `AUREON_REPLAY_GUARD` | Set `0` to disable replay headers (dev only) |
| `AUREON_CLIENT_ALLOWLIST` | Comma-separated API key hashes or raw keys |
| `AUREON_CHAOS_VEIL` | Timing jitter on mutating routes (default ON) |
| `AUREON_CHAOS_JITTER_MS` | Max jitter ms (default 40) |
| `AUREON_ORGANISM_PULSE_MS` | Background pulse interval (default 30000) |
| `AUREON_VAULT_BIND_FINGERPRINT` | Bind secrets vault to organism fingerprint (default ON) |
| `AUREON_REQUIREMENTS_SHA256` | Pin requirements.txt hash |
| `AUREON_AUTO_LEARN` | Background grade learning on Railway |

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

## Organism vitals

```bash
curl https://your-app.railway.app/security/status
curl https://your-app.railway.app/organism/vitals
```

Returns `vital`, `learning_allowed`, `lockdown_reason`, all 11 organs, and `organism_fingerprint`.
