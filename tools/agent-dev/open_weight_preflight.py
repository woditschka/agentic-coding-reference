#!/usr/bin/env python3
"""Ask the [open-weight] peer which models it serves and hold the model map to the answer.

Runs on the host before a --ow launch, so a stale map is named before the
session starts instead of failing one dispatch at a time. Exit codes, the
interface claude-dev branches on: 0 every mapped tag is listed; 1 at least
one unlisted tag is a local one, which fails every dispatch that names it;
2 the peer did not answer; 3 every unlisted tag is a cloud tag, served on
demand and so possibly absent from the listing.
"""

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.request

# The listing endpoint Ollama, LM Studio and llama-server answer alike.
TAGS_PATH = "/api/tags"
# A tag with no suffix means this one, as `ollama pull` would read it.
DEFAULT_TAG = "latest"
# A tag the daemon fetches from its cloud registry on first use.
CLOUD_SUFFIX = ":cloud"
# Per socket operation; the deadline bounds the whole fetch.
DEFAULT_TIMEOUT_S = 3.0
DEADLINE_S = 10.0
# A listing is kilobytes; a peer sending more is not answering the question.
MAX_LISTING_BYTES = 1 << 20
READ_CHUNK_BYTES = 1 << 16
# Peer-controlled strings reach the operator's terminal: this many, this long.
MAX_NAMES_SHOWN = 20
MAX_NAME_LENGTH = 80

EXIT_LISTED = 0
EXIT_LOCAL_MISSING = 1
EXIT_NO_ANSWER = 2
EXIT_CLOUD_MISSING = 3


class PeerError(Exception):
    """The peer did not answer the question."""


def canonical(tag: str) -> str:
    """Spell a tag the way the listing spells it."""
    # The registry path may carry a port but never a suffix, so the suffix is
    # a colon after the last slash.
    name = tag.rsplit("/", 1)[-1]
    return tag if ":" in name else f"{tag}:{DEFAULT_TAG}"


def sanitize(text: str) -> str:
    """Keep a peer-sent string printable: ASCII only, no control bytes, capped."""
    kept = "".join(c if " " <= c <= "~" else "?" for c in text)
    return kept[:MAX_NAME_LENGTH] + ("..." if len(kept) > MAX_NAME_LENGTH else "")


def served_tags(listing: object) -> set[str]:
    """Read the tag names out of a listing document."""
    if not isinstance(listing, dict) or not isinstance(listing.get("models"), list):
        raise PeerError("the listing carries no models array")
    names: set[str] = set()
    for entry in listing["models"]:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            names.add(entry["name"])
    return names


def missing(mapped: list[str], served: set[str]) -> list[str]:
    """Name the mapped tags the peer does not list, in map order."""
    return [tag for tag in mapped if canonical(tag) not in served]


def verdict(absent: list[str]) -> int:
    """Grade the unlisted tags: a local one fails, cloud-only tags warn."""
    if not absent:
        return EXIT_LISTED
    if all(tag.endswith(CLOUD_SUFFIX) for tag in absent):
        return EXIT_CLOUD_MISSING
    return EXIT_LOCAL_MISSING


def _build_opener() -> urllib.request.OpenerDirector:
    """Build an opener that speaks plain HTTP only and never follows a redirect."""
    # No file: or ftp: handler and no redirect handler, as in ide_preflight.
    # The peer is operator policy, the listing it returns is not, and a 3xx
    # must not walk the probe to another host.
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(urllib.request.UnknownHandler())
    return opener


_OPENER = _build_opener()


def fetch_listing(peer: str, port: int, timeout: float) -> object:
    """Fetch the peer's listing within the size cap and the deadline."""
    url = f"http://{peer}:{port}{TAGS_PATH}"
    deadline = time.monotonic() + DEADLINE_S
    body = bytearray()
    with _OPENER.open(url, timeout=timeout) as response:
        while True:
            chunk = response.read(READ_CHUNK_BYTES)
            if not chunk:
                break
            body += chunk
            if len(body) > MAX_LISTING_BYTES:
                raise PeerError(f"listing larger than {MAX_LISTING_BYTES} bytes")
            if time.monotonic() > deadline:
                raise PeerError(f"listing not complete after {DEADLINE_S:g} s")
    return json.loads(body.decode("utf-8"))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--peer", required=True, help="host name or address")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--tag", action="append", default=[], help="a mapped tag")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the check and print its verdict for the launcher to relay."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    where = f"{args.peer}:{args.port}"
    try:
        served = served_tags(fetch_listing(args.peer, args.port, args.timeout))
    except (
        OSError,
        urllib.error.URLError,
        http.client.HTTPException,
        PeerError,
        ValueError,
    ) as exc:
        # An HTTPError's reason phrase is the peer's own bytes.
        print(f"open-weight-preflight: {where} did not answer: {sanitize(str(exc))}")
        return EXIT_NO_ANSWER
    absent = missing(args.tag, served)
    code = verdict(absent)
    if code == EXIT_LISTED:
        print(f"open-weight-preflight: {where} lists every mapped tag")
        return code
    shown = sorted(sanitize(name) for name in served)[:MAX_NAMES_SHOWN]
    more = f", +{len(served) - len(shown)} more" if len(served) > len(shown) else ""
    kind = "cloud tags" if code == EXIT_CLOUD_MISSING else "tags"
    print(
        f"open-weight-preflight: {where} does not list the {kind} {', '.join(absent)} "
        f"(served: {', '.join(shown) or 'nothing'}{more})"
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
