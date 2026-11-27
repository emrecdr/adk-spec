"""One-time GitHub Copilot login: `adk-spec login`.

Copilot is the arm with no API key. GitHub's OAuth device flow prints a URL and a short code; the person approves it
in a browser; the token is cached on disk, after which adk-spec runs unattended. LiteLLM ships this flow but polls
for only sixty seconds per code, which is shorter than walking to a browser, and refuses to start inside a running
event loop. So this runs the same flow with GitHub's own window (about fifteen minutes), using LiteLLM's endpoints,
client id, headers and token file, so LiteLLM reads the result exactly as if it had written it.

Ported from the owner's adk_review. It uses names private to LiteLLM 1.106.2, which 1.110.0 removed: a test holds
each one, so a LiteLLM bump that moves them fails at once.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import truststore

from ..orchestration.settings import copilot_key, copilot_token, pin_copilot_dir, quiet_litellm


def keep_private(token: Path) -> None:
    """The token, the key LiteLLM caches beside it, and their folder, readable by their owner alone. No other file
    of the folder is touched, and a folder this account does not own keeps the modes its owner set."""
    for path in (token, token.parent / copilot_key().name):
        if path.is_file():
            path.chmod(0o600)
    with contextlib.suppress(OSError):
        token.parent.chmod(0o700)


def unreachable(exc: Exception) -> int:
    """GitHub could not be reached: the reason, and the fix where the reason is a certificate."""
    print(f"[copilot] GitHub could not be reached: {exc}", file=sys.stderr)
    if "CERTIFICATE_VERIFY_FAILED" in str(exc):
        print(
            "[copilot] a proxy on this network re-signs HTTPS: point Python at its root certificate with "
            "SSL_CERT_FILE, a PEM bundle that holds it, then run this again",
            file=sys.stderr,
        )
    return 1


def no_answer(status: int) -> int:
    """GitHub's token address answered a poll with what is no JSON object: an outage's page, or a proxy's."""
    print(f"[copilot] GitHub answered HTTP {status} with no JSON: an outage's page, or a proxy's", file=sys.stderr)
    if os.getenv("GITHUB_COPILOT_ACCESS_TOKEN_URL"):
        print("[copilot] GITHUB_COPILOT_ACCESS_TOKEN_URL names the address that answered. Check it", file=sys.stderr)
    print("[copilot] no token was cached. Run this again", file=sys.stderr)
    return 1


def _polled(client: Any, url: str, headers: Mapping[str, str], body: Mapping[str, str]) -> dict[str, Any] | int:
    """GitHub's answer to one poll, the JSON object it sends, or the exit code where there is none."""
    import httpx

    try:
        reply = client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        return unreachable(exc)
    try:
        data = reply.json()
    except ValueError:  # a page where GitHub's JSON would be
        data = None
    return data if isinstance(data, dict) else no_answer(reply.status_code)


def main(argv: list[str]) -> int:
    # Certificates through the system's store, as the model factory verifies them: first, before LiteLLM is imported,
    # which keeps the context it makes then, and before GitHub is asked anything.
    truststore.inject_into_ssl()
    # Every file this process makes is its owner's alone from its first byte: LiteLLM writes the token with the
    # default umask.
    os.umask(0o077)
    parser = argparse.ArgumentParser(prog="adk-spec login", add_help=False)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    pin_copilot_dir()  # LiteLLM reads the folder as written: one `~` it would read as a folder named so
    token = copilot_token()
    if token.is_file() and token.stat().st_size and not args.force:  # an empty file is no token
        with contextlib.suppress(OSError):
            keep_private(token)
        print(f"[copilot] already authenticated: {token}")
        print("[copilot] re-authenticate with: adk-spec login --force")
        return 0
    import httpx

    quiet_litellm()  # before LiteLLM's first import
    from litellm.llms.github_copilot.authenticator import (
        DEFAULT_GITHUB_ACCESS_TOKEN_URL,
        DEFAULT_GITHUB_CLIENT_ID,
        Authenticator,
    )
    from litellm.llms.github_copilot.common_utils import GetDeviceCodeError

    auth = Authenticator()
    try:
        info = auth._get_device_code()  # LiteLLM's request: its client id, its headers
    except GetDeviceCodeError as exc:
        return unreachable(exc)
    expires_in = _seconds(info, "expires_in", 900)
    interval = _seconds(info, "interval", 5)
    # Flushed: with stdout redirected to a file, a buffered code would sit unseen until the flow ended.
    print(f"[copilot] open {info['verification_uri']} and enter the code {info['user_code']}", flush=True)
    print(
        f"[copilot] the code is valid for about {expires_in // 60} minutes. Waiting for your approval...\n", flush=True
    )

    url = os.getenv("GITHUB_COPILOT_ACCESS_TOKEN_URL", DEFAULT_GITHUB_ACCESS_TOKEN_URL)
    body = {
        "client_id": os.getenv("GITHUB_COPILOT_CLIENT_ID", DEFAULT_GITHUB_CLIENT_ID),
        "device_code": info["device_code"],
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    deadline = time.monotonic() + expires_in
    with httpx.Client(timeout=30) as client:
        while time.monotonic() < deadline:
            time.sleep(interval)
            data = _polled(client, url, auth._get_github_headers(), body)
            if isinstance(data, int):
                return data
            if access_token := data.get("access_token"):
                return _stored(auth, token, access_token)
            error = data.get("error")
            if error == "slow_down":
                interval += 5
            elif error != "authorization_pending":
                print(f"[copilot] GitHub answered {error!r}: {data.get('error_description', '')}", file=sys.stderr)
                return 1
    print("[copilot] the code expired before you approved it. Run this again", file=sys.stderr)
    return 1


def _seconds(info: Mapping[str, object], key: str, default: int) -> int:
    """A count of seconds GitHub's device-code reply names, or `default` where it names none."""
    value = info.get(key)
    return value if type(value) is int else default


def _stored(auth: Any, token: Path, access_token: str) -> int:
    """Keep GitHub's token, and exchange it once now, so a failure shows here and not in a run: exit 0; or 1 where
    Copilot serves the account no key, the token then removed, since readiness would read it as ready."""
    from litellm.llms.github_copilot.common_utils import GetAPIKeyError

    try:
        auth._ensure_token_dir()
        # The key cached for the token before, another account's after `--force`, would answer the exchange in this
        # one's place. It goes first, so a file that cannot be written leaves both as they were.
        Path(auth.api_key_file).unlink(missing_ok=True)
        token.write_text(access_token, encoding="utf-8")
    except OSError as exc:
        return _unwritable(exc, token)
    try:
        auth.get_api_key()
    except KeyboardInterrupt:  # a token no key was had for would read as ready, to the next login too
        token.unlink(missing_ok=True)
        raise
    except GetAPIKeyError as exc:  # GitHub knows the account; Copilot serves it no key
        token.unlink()
        print(f"[copilot] GitHub signed you in, but Copilot gave no key: {exc}", file=sys.stderr)
        print(
            "[copilot] usually that account has no Copilot seat. A proxy that blocks api.github.com reads "
            "the same. Run this again with an account that has one",
            file=sys.stderr,
        )
        return 1
    keep_private(token)
    print(f"[copilot] done: token cached at {token}")
    return 0


def _unwritable(exc: OSError, token: Path) -> int:
    """Exit 1, said, where the token or its key cannot be written, the file named."""
    print(f"[copilot] could not write {exc.filename or token}: {exc.strerror or exc}", file=sys.stderr)
    print(
        "[copilot] make it writable, or set GITHUB_COPILOT_TOKEN_DIR to a folder you own. Then run this again",
        file=sys.stderr,
    )
    return 1
