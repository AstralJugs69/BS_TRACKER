#!/usr/bin/env python3
"""Check availability of Brawl Stars API endpoints.

Usage examples:
  python check_brawlstars_api.py --token "$BRAWL_TOKEN" --player-tag "#UUUVR2V"
  python check_brawlstars_api.py --token "$BRAWL_TOKEN" --player-tag "#UUUVR2V" --club-tag "#2Q0GCLJG" --output results.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import List, Optional


BASE_URL = "https://api.brawlstars.com/v1"
TIMEOUT_SECONDS = 20


@dataclass
class EndpointResult:
    method: str
    path: str
    url: str
    status: Optional[int]
    ok: bool
    reason: str
    error: Optional[str]
    elapsed_ms: int


def encode_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag:
        return tag
    if not tag.startswith("#"):
        tag = "#" + tag
    return urllib.parse.quote(tag, safe="")


def build_paths(player_tag: str, club_tag: Optional[str], country_code: str, brawler_id: str, include_suspected: bool) -> List[str]:
    ptag = encode_tag(player_tag)
    ctag = encode_tag(club_tag) if club_tag else None

    paths = [
        f"/players/{ptag}",
        f"/players/{ptag}/battlelog",
        "/brawlers",
        f"/brawlers/{brawler_id}",
        "/gamemodes",
        "/events/rotation",
        f"/rankings/{country_code}/players",
        f"/rankings/{country_code}/clubs",
        f"/rankings/{country_code}/brawlers/{brawler_id}",
    ]

    if ctag:
        paths.extend([
            f"/clubs/{ctag}",
            f"/clubs/{ctag}/members",
        ])

    if include_suspected:
        paths.extend([
            "/version",
            "/regions",
            "/locations",
            "/matches",
            "/esports",
        ])

    return paths


def classify_status(status: Optional[int]) -> str:
    if status is None:
        return "network_or_runtime_error"
    if status == 200:
        return "available"
    if status == 400:
        return "bad_request_check_inputs"
    if status == 403:
        return "forbidden_token_or_ip"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "server_error"
    return "other"


def request_json(url: str, token: str) -> tuple[Optional[int], Optional[dict], Optional[str], int]:
    start = time.time()
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.getcode()
            elapsed_ms = int((time.time() - start) * 1000)
            try:
                data = json.loads(body) if body else None
            except json.JSONDecodeError:
                data = None
            return status, data, None, elapsed_ms
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.time() - start) * 1000)
        try:
            data = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            data = None
        return e.code, data, None, elapsed_ms
    except Exception as e:  # noqa: BLE001
        elapsed_ms = int((time.time() - start) * 1000)
        return None, None, str(e), elapsed_ms


def run_checks(paths: List[str], token: str) -> List[EndpointResult]:
    results: List[EndpointResult] = []

    for path in paths:
        url = f"{BASE_URL}{path}"
        status, data, error, elapsed_ms = request_json(url, token)
        reason = classify_status(status)

        if isinstance(data, dict):
            reason = data.get("reason") or data.get("message") or reason

        ok = status == 200
        results.append(
            EndpointResult(
                method="GET",
                path=path,
                url=url,
                status=status,
                ok=ok,
                reason=str(reason),
                error=error,
                elapsed_ms=elapsed_ms,
            )
        )

    return results


def print_table(results: List[EndpointResult]) -> None:
    print("\nBrawl Stars API endpoint availability\n")
    print(f"{'STATUS':>6}  {'OK':>2}  {'ELAPSED':>7}  PATH")
    print("-" * 90)
    for r in results:
        status_text = str(r.status) if r.status is not None else "ERR"
        ok_text = "Y" if r.ok else "N"
        print(f"{status_text:>6}  {ok_text:>2}  {r.elapsed_ms:>6}ms  {r.path}")
        if r.reason and (not r.ok):
            print(f"{'':>20}reason: {r.reason}")
        if r.error:
            print(f"{'':>20}error:  {r.error}")

    total = len(results)
    available = sum(1 for r in results if r.ok)
    print("-" * 90)
    print(f"Available: {available}/{total}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Brawl Stars API endpoint availability with your token.")
    parser.add_argument("--token", required=True, help="Brawl Stars API token.")
    parser.add_argument("--player-tag", required=True, help="Player tag (e.g. #UUUVR2V).")
    parser.add_argument("--club-tag", help="Optional club tag for club endpoints (e.g. #2Q0GCLJG).")
    parser.add_argument("--country-code", default="global", help="Country code or 'global' for ranking endpoints.")
    parser.add_argument("--brawler-id", default="16000000", help="Brawler ID for brawler ranking/details checks.")
    parser.add_argument("--no-suspected", action="store_true", help="Skip suspected/maybe-missing endpoints.")
    parser.add_argument("--output", help="Optional file path to save JSON results.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    include_suspected = not args.no_suspected
    paths = build_paths(
        player_tag=args.player_tag,
        club_tag=args.club_tag,
        country_code=args.country_code,
        brawler_id=args.brawler_id,
        include_suspected=include_suspected,
    )

    results = run_checks(paths, args.token)
    print_table(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        print(f"\nSaved JSON report to: {args.output}")

    # Non-zero exit when no endpoint succeeded can be useful for CI checks.
    if not any(r.ok for r in results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
