# Brawl Stars API endpoint checker

This repository includes a local script to test whether Brawl Stars API endpoints are reachable with your token.

## 1) Run the endpoint checker

```bash
python3 check_brawlstars_api.py \
  --token "$BRAWL_TOKEN" \
  --player-tag "#UUUVR2V" \
  --club-tag "#2Q0GCLJG" \
  --output brawlstars-endpoint-report.json
```

Notes:
- `--club-tag` is optional.
- By default it checks both known public endpoints and a few "suspected" endpoints that sometimes appear in model schemas.
- Add `--no-suspected` if you only want core public endpoints.

## 2) How to allowlist your device IP

Supercell API tokens require **public IPv4 addresses** in CIDR form. They do **not** accept private LAN addresses like:
- `192.168.x.x`
- `10.x.x.x`
- `172.16.x.x` to `172.31.x.x`
- `127.0.0.1`

### Steps

1. Find your current public IP from the same machine that will run scripts:

```bash
curl -4 ifconfig.me
```

or

```bash
curl -4 https://api.ipify.org
```

2. In the Supercell developer portal (your API key settings), set allowed IP(s) using CIDR notation:
- Single IP: `X.X.X.X/32` (recommended for one device)
- Full range (not recommended unless needed): broader CIDR blocks

3. Save key settings, then wait ~1 minute and test again.

4. If your internet IP changes frequently (home ISP/mobile hotspot), either:
- update allowlist each time your public IP changes, or
- use a stable egress IP (cloud VM/VPS/Tailscale exit node) and allowlist that one.

## 3) Troubleshooting quick map

- `403 Forbidden` + message about credentials/IP: token invalid, expired, wrong scope, or IP not allowlisted.
- `404 Not Found`: endpoint may not exist (or tag/resource invalid).
- `429`: token rate limit exceeded.
- network/proxy connection errors: your environment cannot reach `api.brawlstars.com` directly.
