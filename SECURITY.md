# Aureon Security Hardening

Security review applied per Aureon brain corpus (input validation, least privilege, SSRF prevention, safe errors).

## Production checklist

1. Set **`AUREON_API_KEY`** on Railway — all `POST` training/brain/pipeline endpoints require `X-API-Key` header.
2. Set **`DATABASE_URL`** to PostgreSQL (not SQLite) for multi-worker deployments.
3. Set **`ALERT_WEBHOOK_URL`** only to trusted HTTPS endpoints (internal IPs blocked).
4. Do not expose Railway Postgres publicly.

## Fixes applied

| Issue | Severity | Fix |
|-------|----------|-----|
| Unauthenticated expensive POST endpoints | Critical | API key auth via `AUREON_API_KEY` |
| DoS via unbounded `subdomain_limit` | High | Capped at 20; domain at 29 |
| DoS via concurrent training jobs | High | Exclusive training lock (429) |
| Error messages leak internals | Medium | Generic client errors; server-side logging |
| Webhook SSRF | High | Block localhost/private IPs in `ALERT_WEBHOOK_URL` |
| Path traversal in local inbox | High | `resolve_path_under()` |
| Unbounded JSON/model load | Medium | Size limits + payload validation |
| Labeler doc/label mismatch | Medium | Count check before zip |
| Missing security headers | Medium | CSP, X-Frame-Options, nosniff |
| Inline onclick handlers | Low | Event listeners + CSP-friendly JS |
| PostgreSQL pool exhaustion | Medium | pool_size + recycle |

## Client usage with API key

```bash
curl -X POST "https://your-app.railway.app/api/brain/run" \
  -H "X-API-Key: your-secret-key"
```

In browser (optional): set `window.AUREON_API_KEY` before clicking buttons.
