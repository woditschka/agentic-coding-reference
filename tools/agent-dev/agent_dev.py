#!/usr/bin/env python3
"""Run one agent-dev verb: read the policy file and the tool's profile, write one document to stdout.

The launcher calls this for everything that reads or decides.
"""

import argparse
import sys
from pathlib import Path

from agent_dev_config import (
    MODES,
    Config,
    ConfigError,
    ProxyPolicy,
    emit_squid_conf,
    load,
    open_weight_policy,
    project_shadow_key,
    shell_settings,
    validate_domain,
)
from agent_dev_profiles import Profile, name_rank, profile_for, shell_profile


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tool", required=True)
    verbs = parser.add_subparsers(dest="verb", required=True)
    verbs.add_parser("profile", help="the tool's profile as KEY=VALUE lines")
    key = verbs.add_parser("project-key", help="the shadow key of one project path")
    key.add_argument("path")
    settings = verbs.add_parser("settings", help="KEY=VALUE lines for the launcher")
    settings.add_argument("config")
    conf = verbs.add_parser("squid-conf", help="the proxy policy for one launch")
    conf.add_argument("config")
    conf.add_argument("--subnet", required=True)
    conf.add_argument("--mode", choices=MODES)
    conf.add_argument("--allow", action="append", default=[])
    conf.add_argument("--ide-gateway")
    conf.add_argument("--ide-port", type=int)
    # --ow opens the reverse port to the [open-weight] peer; --host-gateway is what
    # a peer of "host" resolves to (the engine's name for the host machine).
    conf.add_argument("--ow", dest="open_weight", action="store_true")
    conf.add_argument("--host-gateway")
    conf.add_argument("--label")
    allowlist = verbs.add_parser(
        "allowlist", help="the effective allow-list, one per line"
    )
    allowlist.add_argument("config")
    allowlist.add_argument("--allow", action="append", default=[])
    session = verbs.add_parser(
        "session-settings", help="the settings document the session receives"
    )
    session.add_argument("config")
    session.add_argument("--ow", dest="open_weight", action="store_true")
    return parser.parse_args(argv)


def _render(args: argparse.Namespace, profile: Profile, config: Config) -> str:
    """Render the document one verb asks for."""
    if args.verb == "settings":
        return shell_settings(config, name_rank)
    if args.verb == "session-settings":
        return profile.session_settings(config, open_weight=args.open_weight)
    # Per-run --allow entries apply to this launch only; the file is never
    # rewritten.
    extra = tuple(validate_domain(entry, "--allow") for entry in args.allow)
    if args.verb == "allowlist":
        return "".join(f"{domain}\n" for domain in config.allow + extra)
    return emit_squid_conf(
        ProxyPolicy(
            subnet=args.subnet,
            mode=args.mode or config.mode,
            allow=config.allow + extra,
            tool=profile.command,
            label=args.label or profile.command,
            mandatory_host=profile.mandatory_host,
            ide_gateway=args.ide_gateway,
            ide_port=args.ide_port,
            open_weight=(
                open_weight_policy(
                    config, args.host_gateway, profile.inference_path_regex
                )
                if args.open_weight
                else None
            ),
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Run one verb and write its document to stdout."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    prefix = "agent-dev"
    try:
        profile = profile_for(args.tool)
        prefix = profile.command
        if args.verb == "profile":
            sys.stdout.write(shell_profile(profile))
        elif args.verb == "project-key":
            sys.stdout.write(project_shadow_key(args.path) + "\n")
        else:
            config = load(
                Path(args.config),
                str(Path.home()),
                reads_telemetry=bool(profile.telemetry_off),
            )
            sys.stdout.write(_render(args, profile, config))
    except (ConfigError, ValueError) as exc:
        print(f"{prefix}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
